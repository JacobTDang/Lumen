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


def _response(scene: str, params: dict) -> str:
    return json.dumps({"scene": scene, "params": params})


# ---------------------------------------------------------------------------
# Classification unit tests (mocked LLM)
# ---------------------------------------------------------------------------

def test_classify_tangent_line(mocker):
    mocker.patch(
        "agent.classifier._build_llm",
        return_value=_mock_llm(_response("tangent_line", {
            "expression": "x**2", "x_point": 2.0, "domain": [-4, 4],
        })),
    )
    from agent.classifier import classify
    result = classify("show me the derivative of x squared at x = 2")
    assert isinstance(result, TangentLineSchema)
    assert result.expression == "x**2"
    assert result.x_point == 2.0


def test_classify_limit(mocker):
    mocker.patch(
        "agent.classifier._build_llm",
        return_value=_mock_llm(_response("limit", {
            "expression": "sin(x)/x", "limit_point": 0, "domain": [-5, 5],
        })),
    )
    from agent.classifier import classify
    result = classify("what is the limit of sin(x)/x as x approaches 0?")
    assert isinstance(result, LimitSchema)
    assert result.limit_point == 0


def test_classify_riemann_sum(mocker):
    mocker.patch(
        "agent.classifier._build_llm",
        return_value=_mock_llm(_response("riemann_sum", {
            "expression": "x**2", "domain": [0, 3], "n": 6, "method": "left",
        })),
    )
    from agent.classifier import classify
    result = classify("show the area under x squared from 0 to 3")
    assert isinstance(result, RiemannSumSchema)
    assert result.n == 6


def test_classify_function_plot(mocker):
    mocker.patch(
        "agent.classifier._build_llm",
        return_value=_mock_llm(_response("function_plot", {
            "expression": "sin(x)", "domain": [-6, 6], "x_point": None,
        })),
    )
    from agent.classifier import classify
    result = classify("plot sin(x)")
    assert isinstance(result, FunctionPlotSchema)
    assert result.expression == "sin(x)"


def test_classify_critical_points(mocker):
    mocker.patch(
        "agent.classifier._build_llm",
        return_value=_mock_llm(_response("critical_points", {
            "expression": "x**3 - 3*x", "domain": [-3, 3],
        })),
    )
    from agent.classifier import classify
    result = classify("find the local max and min of x cubed minus 3x")
    assert isinstance(result, CriticalPointsSchema)


def test_classify_strips_markdown_fences(mocker):
    raw = "```json\n" + _response("function_plot", {
        "expression": "cos(x)", "domain": [-4, 4], "x_point": None,
    }) + "\n```"
    mocker.patch("agent.classifier._build_llm", return_value=_mock_llm(raw))
    from agent.classifier import classify
    result = classify("graph cosine")
    assert isinstance(result, FunctionPlotSchema)


def test_classify_unknown_scene_raises(mocker):
    mocker.patch(
        "agent.classifier._build_llm",
        return_value=_mock_llm(json.dumps({"scene": "not_real", "params": {}})),
    )
    from agent.classifier import classify
    with pytest.raises(ValueError, match="Unknown scene type"):
        classify("something the model misclassifies")


# ---------------------------------------------------------------------------
# /ask route unit tests
# ---------------------------------------------------------------------------

def test_ask_missing_question_returns_400(client):
    res = client.post("/ask", json={})
    assert res.status_code == 400


def test_ask_returns_job_id_and_scene(client, mocker):
    from schemas.types import LessonPlan, StepPlan
    mocker.patch("app.plan", return_value=LessonPlan(
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
    mocker.patch("app.plan", side_effect=ValueError("bad json from model"))
    res = client.post("/ask", json={"question": "some question"})
    assert res.status_code == 422
    assert "planning failed" in res.get_json()["error"]


# ---------------------------------------------------------------------------
# Real API integration test
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_classify_real_api_limit():
    from agent.classifier import classify
    result = classify("show me the limit of sin(x) divided by x as x goes to 0")
    assert isinstance(result, LimitSchema)


@pytest.mark.integration
def test_classify_real_api_riemann():
    from agent.classifier import classify
    result = classify("visualize the area under x squared from 0 to 2 using Riemann sums")
    assert isinstance(result, RiemannSumSchema)
