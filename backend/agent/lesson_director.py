"""
Lesson Director — two-phase agent that composes animated lessons from visual tools.

Phase 1 (narrative_plan):  One LLM call → NarrativePlan {title, arc, 2-4 scenes}
Phase 2 (build_scene):     One LLM call per scene → list of tool calls

The resulting StepPlan objects feed directly into submit_lesson() via the
existing rendering pipeline (no new infrastructure required).
"""
from __future__ import annotations

import concurrent.futures
import json
import os
from typing import List

from pydantic import BaseModel, ValidationError

from agent.llm_client import build_llm, call_model, extract_json
from schemas.types import LessonPlan, StepPlan
from schemas.tools import VISUAL_TOOLS, VALID_TOOL_NAMES, tool_catalog_prompt


# ─────────────────────────────────────────────────────────────────────────────
# Data models
# ─────────────────────────────────────────────────────────────────────────────

class ScenePlan(BaseModel):
    title: str
    objective: str          # one sentence: what the viewer should understand
    is_aha_moment: bool = False  # true for the scene with the key insight


class NarrativePlan(BaseModel):
    lesson_title: str
    core_insight: str       # the single most important thing — stated upfront
    narrative_arc: str      # e.g. "hook→setup→insight→resolution"
    scenes: List[ScenePlan] # 2-4 scenes


class ToolCall(BaseModel):
    tool: str
    args: dict = {}


# _call_model, extract_json imported from agent.llm_client
# Tests mock agent.lesson_director._call_model — keep this thin alias
def _call_model(system: str, user: str) -> str:
    return call_model(system, user)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Narrative plan
# ─────────────────────────────────────────────────────────────────────────────

_NARRATIVE_SYSTEM = """\
You are a master educator designing a short animated lesson (30-90 seconds total).

Your task: given a question or topic, produce a lesson plan with a clear narrative arc.

Rules:
- State the CORE INSIGHT first — the single most important thing the viewer will learn.
  If you cannot state it in one sentence, you don't understand the topic well enough.
- Plan 2-4 scenes. Each scene has one job: one idea, one visual, one conclusion.
- Mark exactly one scene as the "aha moment" (is_aha_moment: true).
- narrative_arc should describe the emotional/conceptual journey, e.g.:
    "hook: why naive O(n²) fails → insight: the sliding window invariant → resolution: O(n) solution"
- lesson_title should be concise (≤8 words).
- scene objective must be one sentence that tells the viewer what they'll understand.

Return ONLY valid JSON matching this schema:
{
  "lesson_title": "...",
  "core_insight": "...",
  "narrative_arc": "...",
  "scenes": [
    {"title": "...", "objective": "...", "is_aha_moment": false},
    {"title": "...", "objective": "...", "is_aha_moment": true},
    ...
  ]
}

EXAMPLES of strong lesson plans:

Example 1 — DSA (two-pointer palindrome):
{
  "lesson_title": "Two Pointers for Palindrome",
  "core_insight": "Opposite-end pointers check each character pair exactly once, replacing the inner loop.",
  "narrative_arc": "hook: nested loops do redundant comparisons → insight: opposite-end convergence checks each pair once → resolution: O(n) palindrome check on 'racecar'",
  "scenes": [
    {"title": "Why Nested Loops Waste Work", "objective": "See that a naive palindrome check compares the same characters multiple times.", "is_aha_moment": false},
    {"title": "The Convergence Insight", "objective": "Watch two pointers from opposite ends collapse the inner loop to a single sweep.", "is_aha_moment": true},
    {"title": "The Algorithm in Action", "objective": "Verify 'racecar' is a palindrome in a single pass.", "is_aha_moment": false}
  ]
}

Example 2 — Math (Riemann sums):
{
  "lesson_title": "Riemann Sums as Area",
  "core_insight": "The definite integral is the limit of rectangle widths shrinking toward zero.",
  "narrative_arc": "hook: how do we measure area under a curve? → insight: rectangles approximate, the limit is exact → resolution: ∫ x² from 0 to 4 = 64/3",
  "scenes": [
    {"title": "The Area Question", "objective": "Frame the problem: what is the area under y = x² between 0 and 4?", "is_aha_moment": false},
    {"title": "Rectangles Get Tighter", "objective": "See how the approximation converges as n grows from 4 to 16 to 64.", "is_aha_moment": true},
    {"title": "The Exact Answer", "objective": "Apply the power rule to confirm ∫ x² dx from 0 to 4 = 64/3.", "is_aha_moment": false}
  ]
}

Example 3 — DSA (Kadane's):
{
  "lesson_title": "Kadane's Algorithm",
  "core_insight": "At each index, the best subarray ending here either extends the previous one or restarts at this element — whichever is larger.",
  "narrative_arc": "hook: brute force is O(n²) → insight: only running sum and best-so-far matter → resolution: single pass O(n)",
  "scenes": [
    {"title": "The Brute Force Cost", "objective": "Understand why checking every subarray is O(n²).", "is_aha_moment": false},
    {"title": "The Reset Decision", "objective": "Discover that we only need two numbers — keep extending, or start fresh?", "is_aha_moment": true},
    {"title": "One Pass Through the Array", "objective": "Walk [-2,1,-3,4,-1,2,1,-5,4] computing max_sum.", "is_aha_moment": false}
  ]
}

Notice the patterns:
- core_insight names the SINGLE moment that matters
- narrative_arc traces emotion: confusion → realization → confidence
- aha_moment scene always sits in the middle, never first or last
- objectives describe what the viewer will UNDERSTAND, not what will appear on screen
"""


# Narrative style presets — prepended to the system prompt to shape the agent's
# voice without changing its core constraints. Pick one in direct_lesson / via
# the /api/direct-lesson "style" param.
NARRATIVE_STYLES: dict[str, str] = {
    "intuition_first": (
        "STYLE: Intuition-first. Lead with geometric or visual intuition. Build "
        "feeling before formality. Save precise definitions for after the viewer "
        "has the gut sense."
    ),
    "rigor_first": (
        "STYLE: Rigor-first. State precise definitions and constraints in the "
        "first scene. Build subsequent scenes on a foundation of formal notation."
    ),
    "socratic": (
        "STYLE: Socratic. Frame each scene as a question the viewer should be "
        "able to answer by its end. Each objective should read as a question, "
        "not a statement."
    ),
    "speedrun": (
        "STYLE: Speedrun. Minimum viable lesson. EXACTLY 2 scenes — hook and "
        "resolution. No setup scenes, no callbacks. Hit only the essential insight."
    ),
}
VALID_STYLES: frozenset[str] = frozenset(NARRATIVE_STYLES.keys())


def narrative_plan(question: str, max_retries: int = 2,
                    style: str | None = None) -> NarrativePlan:
    if not question.strip():
        raise ValueError("question is required")
    system = _NARRATIVE_SYSTEM
    if style:
        style_hint = NARRATIVE_STYLES.get(style)
        if style_hint:
            system = f"{style_hint}\n\n{system}"
    last_error: Exception = ValueError("no attempts")
    for _ in range(max_retries):
        try:
            raw = _call_model(system, f"Topic or question:\n{question.strip()}")
            data = extract_json(raw)
            plan = NarrativePlan(**data)
            if not 2 <= len(plan.scenes) <= 4:
                raise ValueError(f"expected 2-4 scenes, got {len(plan.scenes)}")
            titles = [s.title for s in plan.scenes]
            if len(set(titles)) != len(titles):
                raise ValueError(f"duplicate scene titles: {titles}")
            return plan
        except (json.JSONDecodeError, ValueError, ValidationError) as exc:
            last_error = exc
    raise ValueError(f"narrative_plan failed after {max_retries} attempts: {last_error}")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Scene building (tool call sequence per scene)
# ─────────────────────────────────────────────────────────────────────────────

_SCENE_SYSTEM_TEMPLATE = """\
You are a visual animator building one scene of an educational lesson.
You have access to the following visual tools:

{tool_catalog}

QUALITY RULES (follow these strictly):
1. Maximum 3 visual elements on screen at once (show_array, show_hashmap, etc.)
2. Use set_caption() for WHY this step matters — not what's happening visually.
   The animation shows the WHAT. The caption explains the WHY.
3. Call emphasize() exactly once — at the moment that IS the insight.
   For the AHA-MOMENT scene, use emphasize(pace="slow") — longer flash + built-in beat.
4. Call pause(beats=2) immediately after emphasize() to let the insight land.
5. Never have a stretch longer than 3 seconds without a tool call.
6. End every scene with show_result() OR fade_out_element() before the next idea.
7. Keep element_ids consistent: if you create "array_0", reference it as "array_0" later.
8. Move pointers BEFORE highlighting — the pointer shows WHERE, the highlight shows WHAT.
9. Rhythm matters: slow down at insights (pace="slow", pause(beats=2)), speed
   through mechanical steps. Variable pacing turns a recap into a lesson.

Return ONLY a valid JSON array of tool calls:
[
  {{"tool": "tool_name", "args": {{...}}}},
  {{"tool": "tool_name", "args": {{...}}}},
  ...
]

No explanation. No markdown fences. Just the JSON array.

EXAMPLE — a complete aha-moment scene for two-pointer palindrome on 'racecar'.
Note the structure: caption sets the WHY → array + 2 pointers (3 elements max) →
highlight the active pair → emphasize at the convergence → pause(2) lets it
land → show_result for closure. Eight tool calls is plenty for a 30-second scene.

[
  {{"tool": "show_array", "args": {{"values": ["r","a","c","e","c","a","r"], "label": "s", "element_id": "arr"}}}},
  {{"tool": "set_caption", "args": {{"text": "Two pointers converge from opposite ends — every check is exactly one comparison"}}}},
  {{"tool": "add_pointer", "args": {{"name": "L", "element_id": "arr", "index": 0, "color": "GREEN"}}}},
  {{"tool": "add_pointer", "args": {{"name": "R", "element_id": "arr", "index": 6, "color": "RED"}}}},
  {{"tool": "highlight_cells", "args": {{"element_id": "arr", "indices": [0, 6], "color": "YELLOW"}}}},
  {{"tool": "emphasize", "args": {{"element_id": "arr", "index": -1, "pace": "slow"}}}},
  {{"tool": "pause", "args": {{"beats": 2}}}},
  {{"tool": "move_pointer", "args": {{"name": "L", "element_id": "arr", "to_index": 3}}}},
  {{"tool": "move_pointer", "args": {{"name": "R", "element_id": "arr", "to_index": 3}}}},
  {{"tool": "show_result", "args": {{"value": "True", "label": "is_palindrome"}}}}
]
"""


def build_scene(
    question: str,
    scene_plan: ScenePlan,
    core_insight: str,
    previous_scene_context: str = "",
    max_retries: int = 2,
    previous_error: str | None = None,
) -> list[ToolCall]:
    catalog = tool_catalog_prompt()
    system = _SCENE_SYSTEM_TEMPLATE.format(tool_catalog=catalog)

    context_block = ""
    if previous_scene_context:
        context_block = f"\nPrevious scene left the viewer with: {previous_scene_context}\n"

    aha_note = ""
    if scene_plan.is_aha_moment:
        aha_note = (
            "\n⭐ THIS IS THE AHA MOMENT SCENE. "
            "Make the insight visually unmissable. "
            "Use emphasize() + pause(2) at the exact beat where it clicks.\n"
        )

    error_note = ""
    if previous_error:
        # Truncate noisy stderr — only the last few lines tend to matter
        snippet = previous_error.strip().split("\n")
        snippet = "\n".join(snippet[-8:])[:600]
        error_note = (
            "\n⚠️ Your previous attempt produced a render that FAILED with this error:\n"
            f"```\n{snippet}\n```\n"
            "Common causes: invalid index, referencing an element_id that was never "
            "created, malformed args, conflicting tool sequence. Generate a NEW "
            "tool-call sequence that avoids this failure. Be conservative — use "
            "fewer elements, simpler indices, only well-formed args.\n"
        )

    user = (
        f"Overall lesson question: {question}\n"
        f"Core insight of the lesson: {core_insight}\n"
        f"{context_block}"
        f"{aha_note}"
        f"{error_note}"
        f"Build scene: \"{scene_plan.title}\"\n"
        f"Scene objective: {scene_plan.objective}\n"
        f"\nOutput a JSON array of tool calls for this scene."
    )

    last_error: Exception = ValueError("no attempts")
    for _ in range(max_retries):
        try:
            raw = _call_model(system, user)
            data = extract_json(raw)
            if not isinstance(data, list):
                raise ValueError("expected JSON array of tool calls")
            tool_calls = []
            for item in data:
                if not isinstance(item, dict) or "tool" not in item:
                    continue
                tool_name = item["tool"]
                if tool_name not in VALID_TOOL_NAMES:
                    print(f"[lesson_director] unknown tool '{tool_name}' — skipping")
                    continue
                tool_calls.append(ToolCall(
                    tool=tool_name,
                    args=item.get("args", {}),
                ))
            if not tool_calls:
                raise ValueError("no valid tool calls parsed")
            return tool_calls
        except (json.JSONDecodeError, ValueError, ValidationError) as exc:
            last_error = exc
    raise ValueError(f"build_scene failed for '{scene_plan.title}': {last_error}")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2.5 — self-critique pass
# ─────────────────────────────────────────────────────────────────────────────

_CRITIQUE_SYSTEM = """\
You are a strict reviewer of educational animation scenes. You are given a
sequence of visual tool calls produced by a planner. Your job is to spot common
weaknesses and REVISE the calls so the scene is genuinely good.

CHECKLIST (revise the scene if ANY of these fail):
1. Exactly ONE emphasize() at the insight moment — not zero, not three.
2. A pause(beats=2 or more) IMMEDIATELY after that emphasize().
3. At most 3 visual elements created (show_array, show_hashmap, show_stack,
   show_grid, show_code, show_text, show_equation). Pointers, captions, and
   highlights do NOT count toward this limit.
4. The scene starts with a set_caption() explaining WHY (not what).
5. The scene ends with show_result() OR fade_out_element() — not a hanging frame.
6. No long stretches without movement: ≤4 consecutive tool calls without any
   animation (move_pointer, highlight_cells, emphasize, push_stack, etc.).
7. Every element_id referenced by a later tool call must have been created
   earlier by a show_* tool. No forward references, no typos.

If the scene is already strong, return it unchanged.
If it needs fixing, return the REVISED list with all fixes applied.

Return ONLY a valid JSON array of tool calls. No prose, no markdown fences.
"""


def critique_scene(
    tool_calls: list[ToolCall],
    scene_plan: ScenePlan,
    core_insight: str,
) -> list[ToolCall]:
    """Run one LLM pass over the generated tool calls to fix common weaknesses.

    Falls back to the original tool_calls if the LLM produces something invalid.
    Adds ~3 seconds per scene but materially improves output quality.
    """
    if not tool_calls:
        return tool_calls

    serialized = [{"tool": tc.tool, "args": tc.args} for tc in tool_calls]
    user = (
        f"Scene title: {scene_plan.title}\n"
        f"Scene objective: {scene_plan.objective}\n"
        f"Is aha-moment scene: {scene_plan.is_aha_moment}\n"
        f"Lesson core insight: {core_insight}\n\n"
        f"Current tool calls:\n{json.dumps(serialized, indent=2)}\n\n"
        f"Review against the checklist. Return the revised JSON array."
    )

    try:
        raw = _call_model(_CRITIQUE_SYSTEM, user)
        data = extract_json(raw)
        if not isinstance(data, list):
            return tool_calls
        revised: list[ToolCall] = []
        for item in data:
            if not isinstance(item, dict) or "tool" not in item:
                continue
            tool_name = item["tool"]
            if tool_name not in VALID_TOOL_NAMES:
                continue
            revised.append(ToolCall(tool=tool_name, args=item.get("args", {})))
        if len(revised) >= max(3, len(tool_calls) // 2):
            return revised
        # Critique returned too few calls — likely a parse failure. Keep original.
        return tool_calls
    except Exception as exc:
        print(f"[lesson_director] critique_scene failed for '{scene_plan.title}': {exc}")
        return tool_calls


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator — direct_lesson
# ─────────────────────────────────────────────────────────────────────────────

def _build_scene_safe(
    question: str,
    scene_plan: ScenePlan,
    core_insight: str,
    prev_context: str,
    max_retries: int,
    previous_error: str | None = None,
) -> list[ToolCall]:
    """Wrapper that returns a minimal fallback instead of raising.

    Runs the optional self-critique pass after a successful build_scene so the
    output is checked for the common weaknesses (missing emphasize, too many
    elements, no result_box). Then statically lints the calls — if any
    element_id references are broken, one repair pass is attempted before
    giving up.

    ``previous_error`` is forwarded into build_scene so the LLM knows to avoid
    whatever caused the prior render to fail.
    """
    from agent.tool_linter import lint_tool_calls

    try:
        tool_calls = build_scene(
            question=question,
            scene_plan=scene_plan,
            core_insight=core_insight,
            previous_scene_context=prev_context,
            max_retries=max_retries,
            previous_error=previous_error,
        )
    except Exception as exc:
        # Catch broadly — ConnectionError, TimeoutError, anything from the LLM
        # SDK. Without this, the worker thread dies and the whole lesson errors
        # opaquely instead of returning a minimal fallback scene.
        print(f"[lesson_director] build_scene failed for '{scene_plan.title}': "
              f"{type(exc).__name__}: {exc}")
        return [
            ToolCall(tool="set_caption", args={"text": scene_plan.objective}),
            ToolCall(tool="show_text",
                     args={"content": scene_plan.title, "position": "CENTER"}),
            ToolCall(tool="pause", args={"beats": 2}),
        ]

    # Self-critique pass — falls back to original tool_calls if the LLM fails.
    tool_calls = critique_scene(tool_calls, scene_plan, core_insight)

    # Static lint — if broken references, one repair pass with the issues fed back.
    issues = lint_tool_calls(tool_calls)
    if issues:
        print(f"[lesson_director] static lint flagged {len(issues)} issue(s) in "
              f"'{scene_plan.title}'; attempting repair pass")
        try:
            repaired = build_scene(
                question=question,
                scene_plan=scene_plan,
                core_insight=core_insight,
                previous_scene_context=prev_context,
                max_retries=1,
                previous_error="Static validation found these issues:\n- " +
                               "\n- ".join(issues),
            )
            # Only accept the repair if it removed all issues; otherwise keep
            # the (still imperfect) original — the executor silently skips bad
            # calls so the scene still renders something.
            if not lint_tool_calls(repaired):
                tool_calls = repaired
        except Exception as exc:
            print(f"[lesson_director] repair pass failed: {exc}")

    return tool_calls


def direct_lesson(question: str, max_retries: int = 2,
                   style: str | None = None) -> LessonPlan:
    """
    Full pipeline: narrative plan → build each scene in parallel → LessonPlan.

    ``style`` (optional) picks a narrative voice from NARRATIVE_STYLES:
    intuition_first | rigor_first | socratic | speedrun.

    Phase 2 (build_scene) calls are independent once the narrative is fixed,
    so they run concurrently via a thread pool — reducing latency from ~N×4s
    to ~4s regardless of scene count (N = 2-4 scenes).
    """
    narrative = narrative_plan(question, max_retries=max_retries, style=style)

    # Pass sequential context hints (each scene's objective) for continuity.
    # Even though builds run in parallel, the context is the planned objective
    # from the narrative, not the runtime output — good enough for coherence.
    contexts = [""] + [sp.objective for sp in narrative.scenes[:-1]]

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = [
            pool.submit(
                _build_scene_safe,
                question,
                scene_plan,
                narrative.core_insight,
                contexts[i],
                max_retries,
            )
            for i, scene_plan in enumerate(narrative.scenes)
        ]
        tool_call_lists = [f.result() for f in futures]

    steps = [
        StepPlan(
            tool="dynamic_lesson_step",
            params={
                "title": sp.title,
                "tool_calls": [{"tool": tc.tool, "args": tc.args} for tc in tcs],
            },
            caption=sp.objective,
        )
        for sp, tcs in zip(narrative.scenes, tool_call_lists)
    ]

    return LessonPlan(
        concept=narrative.lesson_title,
        level="dynamic",
        steps=steps,
    )
