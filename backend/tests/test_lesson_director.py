"""
Tests for the Lesson Director agent and the dynamic tool executor.

Unit tests: mock the LLM (_call_model) — fast, no Manim, no API keys.
Integration tests: marked with @pytest.mark.integration — render a real DynamicScene.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent.lesson_director import (
    NarrativePlan,
    ScenePlan,
    ToolCall,
    narrative_plan,
    build_scene,
    direct_lesson,
)
from schemas.tools import VALID_TOOL_NAMES, VISUAL_TOOLS
from schemas.types import LessonPlan, StepPlan


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / helpers
# ─────────────────────────────────────────────────────────────────────────────

MOCK_NARRATIVE = {
    "lesson_title": "Two Pointers for Palindrome",
    "core_insight": "Using two pointers from opposite ends avoids redundant comparisons.",
    "narrative_arc": "hook: show O(n²) nested loops → insight: opposite pointer convergence → resolution: O(n) palindrome check",
    "scenes": [
        {"title": "The Brute Force Problem", "objective": "Understand why nested loops are slow.", "is_aha_moment": False},
        {"title": "The Pointer Insight", "objective": "See how two pointers replace the inner loop.", "is_aha_moment": True},
        {"title": "The Solution", "objective": "Watch the algorithm find 'racecar' is a palindrome.", "is_aha_moment": False},
    ],
}

MOCK_TOOL_CALLS = [
    {"tool": "show_array", "args": {"values": ["r","a","c","e","c","a","r"], "element_id": "array_0", "label": "s"}},
    {"tool": "set_caption", "args": {"text": "Two pointers converge from both ends"}},
    {"tool": "add_pointer", "args": {"name": "L", "element_id": "array_0", "index": 0, "color": "GREEN"}},
    {"tool": "add_pointer", "args": {"name": "R", "element_id": "array_0", "index": 6, "color": "RED"}},
    {"tool": "highlight_cells", "args": {"element_id": "array_0", "indices": [0, 6], "color": "YELLOW"}},
    {"tool": "emphasize", "args": {"element_id": "array_0", "index": -1}},
    {"tool": "pause", "args": {"beats": 2}},
    {"tool": "show_result", "args": {"value": "True", "label": "is_palindrome"}},
]


# ─────────────────────────────────────────────────────────────────────────────
# Phase A — tool schema sanity checks
# ─────────────────────────────────────────────────────────────────────────────

def test_all_tools_have_required_fields():
    for t in VISUAL_TOOLS:
        assert "name" in t, f"Tool missing 'name': {t}"
        assert "description" in t, f"Tool '{t['name']}' missing 'description'"
        assert "parameters" in t, f"Tool '{t['name']}' missing 'parameters'"


def test_valid_tool_names_matches_catalog():
    assert len(VALID_TOOL_NAMES) == len(VISUAL_TOOLS)
    for t in VISUAL_TOOLS:
        assert t["name"] in VALID_TOOL_NAMES


def test_tool_names_are_snake_case():
    for name in VALID_TOOL_NAMES:
        assert name == name.lower(), f"Tool name not lowercase: {name}"
        assert " " not in name, f"Tool name contains space: {name}"


# ─────────────────────────────────────────────────────────────────────────────
# Phase C — lesson director unit tests (mocked LLM)
# ─────────────────────────────────────────────────────────────────────────────

def test_narrative_plan_parses_correctly(mocker):
    mocker.patch(
        "agent.lesson_director._call_model",
        return_value=json.dumps(MOCK_NARRATIVE),
    )
    plan = narrative_plan("Check if a string is a palindrome")
    assert plan.lesson_title == "Two Pointers for Palindrome"
    assert len(plan.scenes) == 3
    assert any(s.is_aha_moment for s in plan.scenes)
    assert plan.core_insight


def test_narrative_plan_enforces_2_to_4_scenes(mocker):
    bad = {**MOCK_NARRATIVE, "scenes": [MOCK_NARRATIVE["scenes"][0]]}  # only 1 scene
    mocker.patch("agent.lesson_director._call_model", return_value=json.dumps(bad))
    with pytest.raises(ValueError, match="2-4 scenes"):
        narrative_plan("anything")


def test_build_scene_returns_valid_tool_calls(mocker):
    mocker.patch(
        "agent.lesson_director._call_model",
        return_value=json.dumps(MOCK_TOOL_CALLS),
    )
    scene_plan = ScenePlan(
        title="The Pointer Insight",
        objective="See how two pointers replace the inner loop.",
        is_aha_moment=True,
    )
    calls = build_scene("palindrome check", scene_plan, "two pointers avoid redundancy")
    assert len(calls) > 0
    for c in calls:
        assert isinstance(c, ToolCall)
        assert c.tool in VALID_TOOL_NAMES


def test_build_scene_skips_unknown_tools(mocker):
    tool_calls_with_bad = MOCK_TOOL_CALLS + [{"tool": "nonexistent_tool", "args": {}}]
    mocker.patch(
        "agent.lesson_director._call_model",
        return_value=json.dumps(tool_calls_with_bad),
    )
    scene_plan = ScenePlan(title="Test", objective="Test.", is_aha_moment=False)
    calls = build_scene("test", scene_plan, "insight")
    assert all(c.tool in VALID_TOOL_NAMES for c in calls)


# ─────────────────────────────────────────────────────────────────────────────
# critique_scene — self-critique pass
# ─────────────────────────────────────────────────────────────────────────────

def test_critique_scene_returns_revised_calls(mocker):
    """When the critique LLM returns a valid revised array, those calls are returned."""
    from agent.lesson_director import critique_scene, ToolCall
    revised = [
        {"tool": "set_caption", "args": {"text": "improved"}},
        {"tool": "show_array", "args": {"values": ["a"], "element_id": "arr"}},
        {"tool": "emphasize", "args": {"element_id": "arr"}},
        {"tool": "pause", "args": {"beats": 2}},
        {"tool": "show_result", "args": {"value": "ok"}},
    ]
    mocker.patch("agent.lesson_director._call_model", return_value=json.dumps(revised))
    original = [ToolCall(tool="show_array", args={"values": ["a"]})]
    sp = ScenePlan(title="t", objective="o", is_aha_moment=True)
    out = critique_scene(original, sp, "insight")
    assert [c.tool for c in out] == [
        "set_caption", "show_array", "emphasize", "pause", "show_result"
    ]


def test_critique_scene_falls_back_on_invalid_json(mocker):
    """If the critique LLM returns garbage, original tool_calls survive."""
    from agent.lesson_director import critique_scene, ToolCall
    mocker.patch("agent.lesson_director._call_model", return_value="not json")
    original = [
        ToolCall(tool="show_array", args={"values": ["a"]}),
        ToolCall(tool="emphasize", args={"element_id": "arr"}),
        ToolCall(tool="show_result", args={"value": "x"}),
    ]
    sp = ScenePlan(title="t", objective="o", is_aha_moment=True)
    out = critique_scene(original, sp, "insight")
    assert out == original


def test_critique_scene_falls_back_on_too_few_calls(mocker):
    """If critique returns suspiciously few calls (parse partial fail), keep original."""
    from agent.lesson_director import critique_scene, ToolCall
    # Returns only 1 call, but original had 5 — likely partial parse, reject
    mocker.patch(
        "agent.lesson_director._call_model",
        return_value=json.dumps([{"tool": "pause", "args": {}}]),
    )
    original = [ToolCall(tool=t, args={}) for t in
                ["show_array", "set_caption", "emphasize", "pause", "show_result"]]
    sp = ScenePlan(title="t", objective="o", is_aha_moment=True)
    out = critique_scene(original, sp, "insight")
    assert len(out) == 5


def test_critique_scene_empty_input_returns_empty(mocker):
    """If build_scene returned no calls, critique short-circuits."""
    from agent.lesson_director import critique_scene
    mock = mocker.patch("agent.lesson_director._call_model")
    sp = ScenePlan(title="t", objective="o", is_aha_moment=False)
    out = critique_scene([], sp, "insight")
    assert out == []
    mock.assert_not_called()


def test_build_scene_safe_invokes_critique(mocker):
    """_build_scene_safe runs critique after a successful build_scene."""
    from agent.lesson_director import _build_scene_safe, ToolCall

    built = [
        ToolCall(tool="set_caption", args={"text": "x"}),
        ToolCall(tool="show_array", args={"values": ["a"]}),
        ToolCall(tool="emphasize", args={"element_id": "arr"}),
        ToolCall(tool="show_result", args={"value": "y"}),
    ]
    mocker.patch("agent.lesson_director.build_scene", return_value=built)
    critique = mocker.patch("agent.lesson_director.critique_scene", return_value=built)

    sp = ScenePlan(title="t", objective="o", is_aha_moment=False)
    _build_scene_safe("q", sp, "insight", "", max_retries=2)
    critique.assert_called_once()


def test_build_scene_includes_previous_error_in_prompt(mocker):
    """When previous_error is given, the user message embeds it as guidance."""
    from agent.lesson_director import build_scene
    captured = {}
    def fake_call(system, user):
        captured["user"] = user
        return json.dumps(MOCK_TOOL_CALLS)
    mocker.patch("agent.lesson_director._call_model", side_effect=fake_call)
    sp = ScenePlan(title="t", objective="o", is_aha_moment=False)
    build_scene("q", sp, "core", previous_error="IndexError: 5 out of range")
    assert "previous attempt" in captured["user"].lower()
    assert "IndexError" in captured["user"]


def test_build_scene_without_previous_error_has_clean_prompt(mocker):
    """Default path: no error-recovery note in the user message."""
    from agent.lesson_director import build_scene
    captured = {}
    def fake_call(system, user):
        captured["user"] = user
        return json.dumps(MOCK_TOOL_CALLS)
    mocker.patch("agent.lesson_director._call_model", side_effect=fake_call)
    sp = ScenePlan(title="t", objective="o", is_aha_moment=False)
    build_scene("q", sp, "core")
    assert "previous attempt" not in captured["user"].lower()


def test_emphasize_supports_pace_arg():
    """The pace arg is wired through the tool catalog."""
    from schemas.tools import VISUAL_TOOLS
    emp = next(t for t in VISUAL_TOOLS if t["name"] == "emphasize")
    assert "pace" in emp["parameters"]
    assert set(emp["parameters"]["pace"]["enum"]) == {"slow", "normal", "fast"}


def test_tool_executor_emphasize_honors_pace():
    """Calling emphasize with pace='slow' triggers a longer play + an extra wait."""
    from scenes.tool_executor import ToolExecutor

    class _Stub:
        def __init__(self):
            self.plays = []
            self.waits = []
        def play(self, *anims, **kwargs):
            self.plays.append(kwargs.get("run_time"))
        def wait(self, t=None):
            self.waits.append(t)

    # Seed an element to emphasize
    sc = _Stub()
    executor = ToolExecutor(sc)
    from scenes.dsa_primitives import ArrayStrip
    strip = ArrayStrip(["1", "2"], position=(0, 0, 0))
    executor.state["arr"] = strip
    executor.vgroups["arr"] = strip.vgroup

    executor._tool_emphasize("arr", index=-1, pace="slow")
    assert sc.plays == [1.0]
    assert sc.waits == [0.6]    # slow includes the built-in hold

    sc.plays.clear(); sc.waits.clear()
    executor._tool_emphasize("arr", index=-1, pace="fast")
    assert sc.plays == [0.3]
    assert sc.waits == []        # fast has no hold


def test_direct_lesson_produces_lesson_plan(mocker):
    call_count = {"n": 0}

    def mock_call(system, user):
        if call_count["n"] == 0:
            call_count["n"] += 1
            return json.dumps(MOCK_NARRATIVE)
        call_count["n"] += 1
        return json.dumps(MOCK_TOOL_CALLS)

    mocker.patch("agent.lesson_director._call_model", side_effect=mock_call)
    lesson = direct_lesson("Check if a string is a palindrome")

    assert isinstance(lesson, LessonPlan)
    assert lesson.concept == "Two Pointers for Palindrome"
    assert len(lesson.steps) == 3
    for step in lesson.steps:
        assert step.tool == "dynamic_lesson_step"
        assert "tool_calls" in step.params
        assert isinstance(step.params["tool_calls"], list)


def test_direct_lesson_fallback_on_bad_scene(mocker):
    """If build_scene fails for one scene, a minimal fallback scene is used."""
    call_count = {"n": 0}

    def mock_call(system, user):
        if call_count["n"] == 0:
            call_count["n"] += 1
            return json.dumps(MOCK_NARRATIVE)
        call_count["n"] += 1
        return "not valid json"  # triggers ValueError

    mocker.patch("agent.lesson_director._call_model", side_effect=mock_call)
    # Should not raise — falls back gracefully
    lesson = direct_lesson("test question")
    assert len(lesson.steps) == 3


# ─────────────────────────────────────────────────────────────────────────────
# Phase D — endpoint tests
# ─────────────────────────────────────────────────────────────────────────────

def test_direct_lesson_endpoint_missing_question(client):
    res = client.post("/api/direct-lesson", json={})
    assert res.status_code == 400


def test_direct_lesson_endpoint_blank_question(client):
    res = client.post("/api/direct-lesson", json={"question": "   "})
    assert res.status_code == 400


def test_direct_lesson_endpoint_happy_path(client, mocker):
    """Endpoint returns a job_id immediately without waiting for the agent."""
    mocker.patch("app.submit_direct_lesson", return_value="test-job-id")
    res = client.post("/api/direct-lesson",
                      json={"question": "Explain two-pointer palindrome"})
    assert res.status_code == 202
    data = res.get_json()
    assert data["job_id"] == "test-job-id"


def test_direct_lesson_endpoint_returns_quickly(client, mocker):
    """Even if the underlying submit_direct_lesson is slow, the endpoint
    returns quickly because the agent runs in a background thread.
    We assert by mocking submit_direct_lesson to a fast no-op."""
    import time
    mocker.patch("app.submit_direct_lesson", return_value="fast-job")
    start = time.time()
    res = client.post("/api/direct-lesson", json={"question": "anything"})
    elapsed = time.time() - start
    assert res.status_code == 202
    assert elapsed < 1.0  # generous; real call is <50ms


# ─────────────────────────────────────────────────────────────────────────────
# Async submit_direct_lesson — Phase B
# ─────────────────────────────────────────────────────────────────────────────

def test_submit_direct_lesson_returns_immediately(mocker):
    """submit_direct_lesson must return a job_id without blocking on the agent."""
    from renderer.worker import submit_direct_lesson, get_job
    import time

    # Mock the agent to sleep 1 second; submit_direct_lesson should still
    # return in well under that.
    def slow_narrative(*args, **kwargs):
        time.sleep(1.0)
        from agent.lesson_director import NarrativePlan, ScenePlan
        return NarrativePlan(
            lesson_title="x", core_insight="y", narrative_arc="z",
            scenes=[ScenePlan(title="A", objective="o"),
                    ScenePlan(title="B", objective="o")],
        )

    mocker.patch("agent.lesson_director.narrative_plan", side_effect=slow_narrative)

    start = time.time()
    job_id = submit_direct_lesson("test")
    elapsed = time.time() - start

    assert elapsed < 0.2  # must return immediately
    job = get_job(job_id)
    assert job is not None
    assert job["status"] == "pending"
    assert job["stage"] == "planning_narrative"


def test_run_direct_lesson_stage_progression(mocker):
    """As the agent advances, stage transitions through planning → building → mirror."""
    from renderer.worker import _run_direct_lesson, _jobs
    from agent.lesson_director import NarrativePlan, ScenePlan, ToolCall

    fake_narrative = NarrativePlan(
        lesson_title="T", core_insight="I", narrative_arc="A",
        scenes=[ScenePlan(title="One", objective="o")],
    )
    mocker.patch("agent.lesson_director.narrative_plan", return_value=fake_narrative)
    mocker.patch("agent.lesson_director.build_scene", return_value=[
        ToolCall(tool="set_caption", args={"text": "test"}),
    ])

    # Stub submit_lesson — set inner job to done immediately
    def stub_submit(steps):
        from renderer.worker import _jobs
        inner_id = "inner-test-job"
        _jobs[inner_id] = {"status": "done", "url": "/media/lessons/x.mp4",
                           "error": None, "progress": 1.0, "stage": "done"}
        return inner_id
    mocker.patch("renderer.worker.submit_lesson", side_effect=stub_submit)

    outer_id = "outer-test"
    _jobs[outer_id] = {"status": "pending", "url": None, "error": None,
                       "progress": 0.0, "stage": "planning_narrative"}
    _run_direct_lesson(outer_id, "test question")

    assert _jobs[outer_id]["status"] == "done"
    assert _jobs[outer_id]["stage"] == "done"
    assert _jobs[outer_id]["url"] == "/media/lessons/x.mp4"


def test_run_direct_lesson_agent_failure_records_error(mocker):
    """If the agent raises, the outer job ends in error with stage='error'."""
    from renderer.worker import _run_direct_lesson, _jobs
    mocker.patch("agent.lesson_director.narrative_plan",
                 side_effect=ValueError("LLM down"))

    outer_id = "outer-err-test"
    _jobs[outer_id] = {"status": "pending", "url": None, "error": None,
                       "progress": 0.0, "stage": "planning_narrative"}
    _run_direct_lesson(outer_id, "anything")

    assert _jobs[outer_id]["status"] == "error"
    assert _jobs[outer_id]["stage"] == "error"
    assert "LLM down" in _jobs[outer_id]["error"]


# ─────────────────────────────────────────────────────────────────────────────
# Phase B — ToolExecutor unit test (no Manim render — uses mock scene)
# ─────────────────────────────────────────────────────────────────────────────

class MockScene:
    """Minimal stand-in for a Manim Scene so ToolExecutor can be unit-tested."""
    def __init__(self):
        self.played = []

    def play(self, *anims, **kwargs):
        self.played.extend(anims)

    def wait(self, t=None):
        pass


def test_tool_executor_skips_unknown_tool():
    """ToolExecutor.execute must not raise on an unknown tool name."""
    # Import here to avoid Manim import at module level in non-render context
    from scenes.tool_executor import ToolExecutor
    mock_scene = MockScene()
    executor = ToolExecutor(mock_scene)
    # Should log a warning and return without raising
    executor.execute("completely_made_up_tool", {"foo": "bar"})


# ─────────────────────────────────────────────────────────────────────────────
# Integration — render a real DynamicScene
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_dynamic_scene_renders(tmp_path):
    """
    Render a minimal DynamicScene with a known tool call sequence.
    Asserts the output MP4 exists and is non-empty.
    """
    import json, subprocess, tempfile

    job_id = "test_dynamic_001"
    temp_dir = str(tmp_path)
    params = {
        "title": "Two Pointers",
        "tool_calls": [
            {"tool": "show_array",
             "args": {"values": ["r","a","c","e","c","a","r"],
                      "label": "s", "element_id": "arr"}},
            {"tool": "set_caption",
             "args": {"text": "L and R converge from opposite ends"}},
            {"tool": "add_pointer",
             "args": {"name": "L", "element_id": "arr", "index": 0, "color": "GREEN"}},
            {"tool": "add_pointer",
             "args": {"name": "R", "element_id": "arr", "index": 6, "color": "RED"}},
            {"tool": "highlight_cells",
             "args": {"element_id": "arr", "indices": [0, 6], "color": "YELLOW"}},
            {"tool": "emphasize", "args": {"element_id": "arr", "index": -1}},
            {"tool": "pause", "args": {"beats": 1}},
            {"tool": "show_result", "args": {"value": "True", "label": "palindrome"}},
        ],
    }

    params_path = tmp_path / f"{job_id}.json"
    params_path.write_text(json.dumps(params))

    backend_dir = os.path.dirname(os.path.dirname(__file__))
    media_dir = str(tmp_path / "media")
    os.makedirs(media_dir, exist_ok=True)

    env = {**os.environ,
           "MANIM_JOB_ID": job_id,
           "MANIM_TEMP_DIR": str(tmp_path)}

    result = subprocess.run(
        [sys.executable, "-m", "manim", "-ql",
         "--media_dir", media_dir,
         "--disable_caching",
         os.path.join(backend_dir, "scenes", "tool_executor.py"),
         "DynamicScene"],
        capture_output=True,
        text=True,
        cwd=backend_dir,
        env=env,
        timeout=120,
    )

    assert result.returncode == 0, (
        f"DynamicScene render failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    # Find the output MP4
    mp4_files = list(tmp_path.rglob("DynamicScene.mp4"))
    assert mp4_files, (
        f"No DynamicScene.mp4 found under {tmp_path}. "
        f"Manim output:\n{result.stderr[-1000:]}"
    )
    assert mp4_files[0].stat().st_size > 1000, "MP4 is suspiciously small"


def _run_dynamic_scene(tmp_path, job_id: str, params: dict):
    """Helper: write params JSON, invoke Manim, return subprocess result."""
    import json, subprocess
    params_path = tmp_path / f"{job_id}.json"
    params_path.write_text(json.dumps(params))
    backend_dir = os.path.dirname(os.path.dirname(__file__))
    media_dir = str(tmp_path / "media")
    os.makedirs(media_dir, exist_ok=True)
    env = {**os.environ, "MANIM_JOB_ID": job_id, "MANIM_TEMP_DIR": str(tmp_path)}
    return subprocess.run(
        [sys.executable, "-m", "manim", "-ql",
         "--media_dir", media_dir, "--disable_caching",
         os.path.join(backend_dir, "scenes", "tool_executor.py"), "DynamicScene"],
        capture_output=True, text=True, cwd=backend_dir, env=env, timeout=120,
    )


@pytest.mark.integration
def test_dynamic_scene_hashmap_and_stack_render(tmp_path):
    """Regression test for bugs A+B: show_hashmap and show_stack must render
    without crashing (both had silent errors before the fix)."""
    params = {
        "title": "Hashmap + Stack smoke test",
        "tool_calls": [
            {"tool": "show_array",
             "args": {"values": ["3", "1", "4", "1", "5"], "label": "nums", "element_id": "arr"}},
            {"tool": "show_hashmap",
             "args": {"title": "seen", "anchor": "UR", "element_id": "map"}},
            {"tool": "show_stack",
             "args": {"title": "mono_stack", "anchor": "DR", "element_id": "stk"}},
            {"tool": "set_caption", "args": {"text": "Building frequency map and monotonic stack"}},
            {"tool": "set_hashmap_entry", "args": {"element_id": "map", "key": "3", "value": "1"}},
            {"tool": "push_stack", "args": {"element_id": "stk", "value": "3", "color": "YELLOW"}},
            {"tool": "push_stack", "args": {"element_id": "stk", "value": "1", "color": "GREEN"}},
            {"tool": "pop_stack", "args": {"element_id": "stk"}},
            {"tool": "emphasize", "args": {"element_id": "map"}},
            {"tool": "show_result", "args": {"value": "OK", "label": "test"}},
        ],
    }
    result = _run_dynamic_scene(tmp_path, "test_hashmap_stack_001", params)
    assert result.returncode == 0, (
        f"Hashmap+Stack render failed:\n{result.stdout}\n{result.stderr}"
    )
    mp4_files = list(tmp_path.rglob("DynamicScene.mp4"))
    assert mp4_files and mp4_files[0].stat().st_size > 1000
