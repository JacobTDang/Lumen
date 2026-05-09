"""
Lesson Director — two-phase agent that composes animated lessons from visual tools.

Phase 1 (narrative_plan):  One LLM call → NarrativePlan {title, arc, 2-4 scenes}
Phase 2 (build_scene):     One LLM call per scene → list of tool calls

The resulting StepPlan objects feed directly into submit_lesson() via the
existing rendering pipeline (no new infrastructure required).
"""
from __future__ import annotations

import json
import os
import re
from typing import List

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, ValidationError

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


# ─────────────────────────────────────────────────────────────────────────────
# LLM client (same stack as planner.py / leetcode_parser.py)
# ─────────────────────────────────────────────────────────────────────────────

def _build_llm() -> ChatOpenAI:
    base_or = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    if os.environ.get("OPENROUTER_GPT_OSS_120_KEY"):
        return ChatOpenAI(
            base_url=base_or,
            api_key=os.environ["OPENROUTER_GPT_OSS_120_KEY"],
            model=os.environ.get("OPENROUTER_GPT_OSS_120_MODEL", "openai/gpt-oss-120b"),
            temperature=0,
            extra_body={"reasoning": {"effort": "low"}},
        )
    if os.environ.get("GROQ_API_KEY"):
        return ChatOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ["GROQ_API_KEY"],
            model=os.environ.get("GROQ_PLANNER_MODEL", "llama-3.3-70b-versatile"),
            temperature=0,
        )
    return ChatOpenAI(
        base_url=base_or,
        api_key=os.environ["OPENROUTER_API_KEY"],
        model=os.environ.get("OPENROUTER_MODEL",
                             "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"),
        temperature=0,
    )


def _call_model(system: str, user: str) -> str:
    """Single seam tests can mock to avoid real LLM calls."""
    llm = _build_llm()
    response = llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=user),
    ])
    return response.content or ""


def _clean_raw(raw: str) -> str:
    raw = re.sub(r"<\|channel\|>analysis<\|message\|>.*?(?=<\|channel\|>final<\|message\|>|$)",
                 "", raw, flags=re.DOTALL)
    raw = re.sub(r"<\|channel\|>final<\|message\|>", "", raw)
    raw = re.sub(r"<\|end\|>", "", raw)
    raw = re.sub(r"<thinking>.*?</thinking>", "", raw, flags=re.DOTALL)
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    raw = re.sub(r",(\s*[}\]])", r"\1", raw)
    return raw.strip()


def _parse_json(raw: str):
    cleaned = _clean_raw(raw)
    if not cleaned:
        raise ValueError("model returned empty response")
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find the outermost JSON object or array
        for start_char, end_char in [('{', '}'), ('[', ']')]:
            s = cleaned.find(start_char)
            e = cleaned.rfind(end_char)
            if s != -1 and e > s:
                try:
                    return json.loads(cleaned[s:e + 1])
                except json.JSONDecodeError:
                    continue
        raise ValueError(f"could not parse JSON from model response: {cleaned[:200]}")


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
"""


def narrative_plan(question: str, max_retries: int = 2) -> NarrativePlan:
    if not question.strip():
        raise ValueError("question is required")
    last_error: Exception = ValueError("no attempts")
    for _ in range(max_retries):
        try:
            raw = _call_model(_NARRATIVE_SYSTEM, f"Topic or question:\n{question.strip()}")
            data = _parse_json(raw)
            plan = NarrativePlan(**data)
            if not 2 <= len(plan.scenes) <= 4:
                raise ValueError(f"expected 2-4 scenes, got {len(plan.scenes)}")
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
4. Call pause(2) immediately after emphasize() to let the insight land.
5. Never have a stretch longer than 3 seconds without a tool call.
6. End every scene with show_result() OR fade_out_element() before the next idea.
7. Keep element_ids consistent: if you create "array_0", reference it as "array_0" later.
8. Move pointers BEFORE highlighting — the pointer shows WHERE, the highlight shows WHAT.

Return ONLY a valid JSON array of tool calls:
[
  {{"tool": "tool_name", "args": {{...}}}},
  {{"tool": "tool_name", "args": {{...}}}},
  ...
]

No explanation. No markdown fences. Just the JSON array.
"""


def build_scene(
    question: str,
    scene_plan: ScenePlan,
    core_insight: str,
    previous_scene_context: str = "",
    max_retries: int = 2,
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

    user = (
        f"Overall lesson question: {question}\n"
        f"Core insight of the lesson: {core_insight}\n"
        f"{context_block}"
        f"{aha_note}"
        f"Build scene: \"{scene_plan.title}\"\n"
        f"Scene objective: {scene_plan.objective}\n"
        f"\nOutput a JSON array of tool calls for this scene."
    )

    last_error: Exception = ValueError("no attempts")
    for _ in range(max_retries):
        try:
            raw = _call_model(system, user)
            data = _parse_json(raw)
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
# Orchestrator — direct_lesson
# ─────────────────────────────────────────────────────────────────────────────

def direct_lesson(question: str, max_retries: int = 2) -> LessonPlan:
    """
    Full pipeline: narrative plan → build each scene → return LessonPlan.

    The returned LessonPlan feeds directly into submit_lesson() without
    any changes to the rendering infrastructure.
    """
    narrative = narrative_plan(question, max_retries=max_retries)

    steps: list[StepPlan] = []
    prev_context = ""

    for scene_plan in narrative.scenes:
        try:
            tool_calls = build_scene(
                question=question,
                scene_plan=scene_plan,
                core_insight=narrative.core_insight,
                previous_scene_context=prev_context,
                max_retries=max_retries,
            )
        except ValueError as exc:
            # Log and produce a minimal fallback scene rather than aborting the lesson
            print(f"[lesson_director] build_scene failed for '{scene_plan.title}': {exc}")
            tool_calls = [
                ToolCall(tool="set_caption", args={"text": scene_plan.objective}),
                ToolCall(tool="show_text",
                         args={"content": scene_plan.title, "position": "CENTER"}),
                ToolCall(tool="pause", args={"beats": 2}),
            ]

        steps.append(StepPlan(
            tool="dynamic_lesson_step",
            params={
                "title": scene_plan.title,
                "tool_calls": [
                    {"tool": tc.tool, "args": tc.args}
                    for tc in tool_calls
                ],
            },
            caption=scene_plan.objective,
        ))
        prev_context = scene_plan.objective

    return LessonPlan(
        concept=narrative.lesson_title,
        level="dynamic",
        steps=steps,
    )
