import json
from unittest.mock import MagicMock

import pytest

from schemas.types import LessonPlan, StepPlan


def _mock_llm(content: str):
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=content)
    return llm


def _resp(concept: str, level: str, steps: list) -> str:
    return json.dumps({"concept": concept, "level": level, "steps": steps})


# ---------------------------------------------------------------------------
# Unit tests (mocked LLM)
# ---------------------------------------------------------------------------

def test_plan_single_step(mocker):
    payload = _resp("function graphing", "calculus", [
        {"tool": "function_plot", "params": {"expression": "x**2", "domain": [-4, 4]}, "caption": "Graph of x²"},
    ])
    mocker.patch("agent.planner._build_llm", return_value=_mock_llm(payload))
    from agent.planner import plan
    result = plan("plot x squared")
    assert isinstance(result, LessonPlan)
    assert len(result.steps) == 1
    assert result.steps[0].tool == "function_plot"
    assert result.steps[0].caption == "Graph of x²"


def test_plan_multi_step(mocker):
    payload = _resp("derivative concept", "calculus", [
        {"tool": "function_plot",  "params": {"expression": "x**3", "domain": [-3, 3]}, "caption": "The function"},
        {"tool": "tangent_line",   "params": {"expression": "x**3", "x_point": 1.0, "domain": [-3, 3]}, "caption": "Derivative as slope"},
        {"tool": "critical_points","params": {"expression": "x**3", "domain": [-3, 3]}, "caption": "Where derivative is zero"},
    ])
    mocker.patch("agent.planner._build_llm", return_value=_mock_llm(payload))
    from agent.planner import plan
    result = plan("explain derivatives of x cubed")
    assert len(result.steps) == 3
    assert result.steps[1].tool == "tangent_line"


def test_plan_strips_markdown_fences(mocker):
    raw = "```json\n" + _resp("limits", "calculus", [
        {"tool": "limit", "params": {"expression": "sin(x)/x", "limit_point": 0, "domain": [-5, 5]}, "caption": "L'Hopital"},
    ]) + "\n```"
    mocker.patch("agent.planner._build_llm", return_value=_mock_llm(raw))
    from agent.planner import plan
    result = plan("limit of sin(x)/x")
    assert result.steps[0].tool == "limit"


def test_plan_new_algebra_tools(mocker):
    payload = _resp("linear equations", "algebra", [
        {"tool": "linear_function", "params": {"expression": "2*x + 1", "domain": [-5, 5]}, "caption": "Slope and intercept"},
    ])
    mocker.patch("agent.planner._build_llm", return_value=_mock_llm(payload))
    from agent.planner import plan
    result = plan("show me a linear function")
    assert result.steps[0].tool == "linear_function"
    assert result.level == "algebra"


def test_plan_trig_tool(mocker):
    payload = _resp("trig functions", "pre_calculus", [
        {"tool": "trig_unit_circle", "params": {"angle": 1.57, "animate_rotation": True}, "caption": "Sin and cos on the unit circle"},
    ])
    mocker.patch("agent.planner._build_llm", return_value=_mock_llm(payload))
    from agent.planner import plan
    result = plan("show me sin and cos on the unit circle")
    assert result.steps[0].tool == "trig_unit_circle"


def test_plan_unknown_tool_raises(mocker):
    payload = _resp("something", "calculus", [
        {"tool": "not_real_tool", "params": {}, "caption": "oops"},
    ])
    mocker.patch("agent.planner._build_llm", return_value=_mock_llm(payload))
    from agent.planner import plan
    with pytest.raises(ValueError, match="Unknown tool"):
        plan("some question")


def test_plan_empty_steps_raises(mocker):
    payload = _resp("empty", "calculus", [])
    mocker.patch("agent.planner._build_llm", return_value=_mock_llm(payload))
    from agent.planner import plan
    with pytest.raises(ValueError, match="no steps"):
        plan("some question")


# ---------------------------------------------------------------------------
# /ask route tests
# ---------------------------------------------------------------------------

def test_ask_returns_new_fields(client, mocker):
    from schemas.types import StepPlan, LessonPlan
    mocker.patch("app.plan", return_value=LessonPlan(
        concept="derivative", level="calculus",
        steps=[StepPlan(tool="function_plot", params={"expression": "x**2", "domain": [-4, 4]}, caption="")],
    ))
    mocker.patch("app.submit_lesson", return_value="lesson-job-id")
    res = client.post("/ask", json={"question": "plot x squared"})
    assert res.status_code == 202
    data = res.get_json()
    assert data["job_id"] == "lesson-job-id"
    assert data["concept"] == "derivative"
    assert data["scene_count"] == 1


# ---------------------------------------------------------------------------
# Real API integration tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_plan_real_api_single():
    from agent.planner import plan
    result = plan("plot the function sin(x)")
    assert isinstance(result, LessonPlan)
    assert len(result.steps) >= 1
    assert result.steps[0].tool in {
        "function_plot", "trig_unit_circle", "limit",
        "tangent_line", "riemann_sum", "critical_points",
        "linear_function", "quadratic",
    }


@pytest.mark.integration
def test_plan_real_api_multi():
    from agent.planner import plan
    result = plan("explain why the derivative of x squared is 2x")
    assert isinstance(result, LessonPlan)
    assert len(result.steps) >= 2
