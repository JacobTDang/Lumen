"""
Unit tests mock the LLM call entirely — no API key needed.
The integration test hits the real OpenRouter API and is marked slow.
"""
import json
from unittest.mock import MagicMock

import pytest

from schemas.types import (
    CriticalPointsSchema,
    FunctionPlotSchema,
    LimitSchema,
    RiemannSumSchema,
    TangentLineSchema,
)


def _mock_llm(content: str):
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=content)
    return llm


def _plan_response(concept: str, tool: str, params: dict) -> str:
    return json.dumps({"concept": concept, "level": "calculus",
                       "steps": [{"tool": tool, "params": params, "caption": ""}]})


# ---------------------------------------------------------------------------
# Math planner unit tests (plan() returns LessonPlan)
# ---------------------------------------------------------------------------

def test_classify_tangent_line(mocker):
    mocker.patch("agent.planner._build_llm", return_value=_mock_llm(
        _plan_response("derivative", "tangent_line",
                       {"expression": "x**2", "x_point": 2.0, "domain": [-4, 4]})))
    from agent.planner import plan
    result = plan("show me the derivative of x squared at x = 2")
    assert result.steps[0].tool == "tangent_line"
    assert result.steps[0].params["expression"] == "x**2"


def test_classify_limit(mocker):
    mocker.patch("agent.planner._build_llm", return_value=_mock_llm(
        _plan_response("limits", "limit",
                       {"expression": "sin(x)/x", "limit_point": 0, "domain": [-5, 5]})))
    from agent.planner import plan
    result = plan("what is the limit of sin(x)/x as x approaches 0?")
    assert result.steps[0].tool == "limit"


def test_classify_riemann_sum(mocker):
    mocker.patch("agent.planner._build_llm", return_value=_mock_llm(
        _plan_response("integral", "riemann_sum",
                       {"expression": "x**2", "domain": [0, 3], "n": 6, "method": "left"})))
    from agent.planner import plan
    result = plan("show the area under x squared from 0 to 3")
    assert result.steps[0].tool == "riemann_sum"
    assert result.steps[0].params["n"] == 6


def test_classify_function_plot(mocker):
    mocker.patch("agent.planner._build_llm", return_value=_mock_llm(
        _plan_response("function", "function_plot",
                       {"expression": "sin(x)", "domain": [-6, 6], "x_point": None})))
    from agent.planner import plan
    result = plan("plot sin(x)")
    assert result.steps[0].tool == "function_plot"


def test_classify_critical_points(mocker):
    mocker.patch("agent.planner._build_llm", return_value=_mock_llm(
        _plan_response("optimization", "critical_points",
                       {"expression": "x**3 - 3*x", "domain": [-3, 3]})))
    from agent.planner import plan
    result = plan("find the local max and min of x cubed minus 3x")
    assert result.steps[0].tool == "critical_points"


def test_classify_strips_markdown_fences(mocker):
    raw = "```json\n" + _plan_response("function", "function_plot",
                                        {"expression": "cos(x)", "domain": [-4, 4],
                                         "x_point": None}) + "\n```"
    mocker.patch("agent.planner._build_llm", return_value=_mock_llm(raw))
    from agent.planner import plan
    result = plan("graph cosine")
    assert result.steps[0].tool == "function_plot"


def test_classify_unknown_scene_raises(mocker):
    mocker.patch("agent.planner._build_llm", return_value=_mock_llm(
        json.dumps({"concept": "x", "level": "calculus",
                    "steps": [{"tool": "not_real", "params": {}, "caption": ""}]})))
    from agent.planner import plan
    with pytest.raises(ValueError, match="Unknown tool"):
        plan("something the model misclassifies")


# ---------------------------------------------------------------------------
# /ask route unit tests
# ---------------------------------------------------------------------------

def test_ask_missing_question_returns_400(client):
    res = client.post("/ask", json={})
    assert res.status_code == 400


def test_ask_returns_job_id_and_scene(client, mocker):
    from schemas.types import LessonPlan, StepPlan
    mocker.patch("app.classify_domain", return_value="math")
    mocker.patch("app.plan_math", return_value=LessonPlan(
        concept="derivative", level="calculus",
        steps=[StepPlan(tool="tangent_line",
                        params={"expression": "x**2", "x_point": 1.0, "domain": [-4, 4]},
                        caption="")],
    ))
    mocker.patch("app.submit_lesson", return_value="test-job-id")
    res = client.post("/ask", json={"question": "derivative of x squared at 1"})
    assert res.status_code == 202
    data = res.get_json()
    assert data["job_id"] == "test-job-id"
    assert data["concept"] == "derivative"


def test_ask_classifier_failure_returns_422(client, mocker):
    mocker.patch("app.classify_domain", return_value="math")
    mocker.patch("app.plan_math", side_effect=ValueError("bad json from model"))
    res = client.post("/ask", json={"question": "some question"})
    assert res.status_code == 422
    assert "planning failed" in res.get_json()["error"]


# ---------------------------------------------------------------------------
# Real API integration test
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_classify_real_api_limit():
    from agent.planner import plan as classify
    result = classify("show me the limit of sin(x) divided by x as x goes to 0")
    assert isinstance(result, LimitSchema)


@pytest.mark.integration
def test_classify_real_api_riemann():
    from agent.planner import plan as classify
    result = classify("visualize the area under x squared from 0 to 2 using Riemann sums")
    assert isinstance(result, RiemannSumSchema)
