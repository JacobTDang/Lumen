"""
Unit tests for DSA planner and domain classifier.
All LLM calls are mocked — no API key needed.
"""
import json
from unittest.mock import MagicMock

import pytest

from schemas.types import LessonPlan, StepPlan


def _mock_llm(content: str):
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=content)
    return llm


def _dsa_resp(concept, steps):
    return json.dumps({"concept": concept, "level": "beginner", "steps": steps})


# ---------------------------------------------------------------------------
# DSA planner unit tests
# ---------------------------------------------------------------------------

def test_plan_dsa_binary_search(mocker):
    payload = _dsa_resp("binary search", [{
        "tool": "array_pointer",
        "params": {"array": [1, 3, 5, 7, 9], "algorithm": "binary_search", "target": 7},
        "caption": "Watch L, M, R converge on the target",
    }])
    mocker.patch("agent.dsa_planner._build_llm", return_value=_mock_llm(payload))
    from agent.dsa_planner import plan_dsa
    result = plan_dsa("how does binary search work?")
    assert isinstance(result, LessonPlan)
    assert result.steps[0].tool == "array_pointer"
    assert result.steps[0].params["algorithm"] == "binary_search"


def test_plan_dsa_bfs(mocker):
    payload = _dsa_resp("graph BFS", [{
        "tool": "graph_traversal",
        "params": {"num_nodes": 5, "edges": [[0,1],[0,2],[1,3],[2,4]], "start_node": 0, "algorithm": "bfs"},
        "caption": "Watch the queue expand level by level",
    }])
    mocker.patch("agent.dsa_planner._build_llm", return_value=_mock_llm(payload))
    from agent.dsa_planner import plan_dsa
    result = plan_dsa("explain BFS on a graph")
    assert result.steps[0].tool == "graph_traversal"


def test_plan_dsa_dp(mocker):
    payload = _dsa_resp("fibonacci DP", [{
        "tool": "dp_array",
        "params": {"algorithm": "fibonacci", "n": 8},
        "caption": "Each cell is the sum of the two before it",
    }])
    mocker.patch("agent.dsa_planner._build_llm", return_value=_mock_llm(payload))
    from agent.dsa_planner import plan_dsa
    result = plan_dsa("show fibonacci using dynamic programming")
    assert result.steps[0].tool == "dp_array"


def test_plan_dsa_tree_traversal(mocker):
    payload = _dsa_resp("tree inorder", [{
        "tool": "tree_traversal",
        "params": {"values": [4, 2, 6, 1, 3, 5, 7], "algorithm": "inorder"},
        "caption": "Inorder visits left, root, right — gives sorted order for BST",
    }])
    mocker.patch("agent.dsa_planner._build_llm", return_value=_mock_llm(payload))
    from agent.dsa_planner import plan_dsa
    result = plan_dsa("show inorder traversal of a binary tree")
    assert result.steps[0].tool == "tree_traversal"


def test_plan_dsa_stack(mocker):
    payload = _dsa_resp("stack operations", [{
        "tool": "stack_queue",
        "params": {"operations": ["push 3", "push 1", "push 4", "pop", "push 5"], "structure": "stack"},
        "caption": "Last in, first out — the top is always removed first",
    }])
    mocker.patch("agent.dsa_planner._build_llm", return_value=_mock_llm(payload))
    from agent.dsa_planner import plan_dsa
    result = plan_dsa("show me how a stack works")
    assert result.steps[0].tool == "stack_queue"


def test_plan_dsa_unknown_tool_raises(mocker):
    payload = _dsa_resp("something", [{"tool": "not_dsa_tool", "params": {}, "caption": ""}])
    mocker.patch("agent.dsa_planner._build_llm", return_value=_mock_llm(payload))
    from agent.dsa_planner import plan_dsa
    with pytest.raises(ValueError, match="Unknown DSA tool"):
        plan_dsa("some question")


def test_plan_dsa_empty_response_retries(mocker):
    good = _dsa_resp("sliding window", [{
        "tool": "sliding_window",
        "params": {"array": [2, 1, 5, 1, 3, 2], "algorithm": "max_subarray_fixed", "k": 3},
        "caption": "The window slides right tracking the max sum",
    }])
    # First call empty, second call good
    call_count = {"n": 0}
    def side_effect(messages):
        call_count["n"] += 1
        content = "" if call_count["n"] == 1 else good
        return MagicMock(content=content)
    llm = MagicMock()
    llm.invoke.side_effect = side_effect
    mocker.patch("agent.dsa_planner._build_llm", return_value=llm)
    from agent.dsa_planner import plan_dsa
    result = plan_dsa("show sliding window")
    assert result.steps[0].tool == "sliding_window"
    assert call_count["n"] == 2


# ---------------------------------------------------------------------------
# Domain classifier unit tests
# ---------------------------------------------------------------------------

def test_classifier_dsa_keywords(mocker):
    mocker.patch("agent.classifier._build_classifier_llm",
                 return_value=_mock_llm("dsa"))
    from agent.classifier import classify_domain
    assert classify_domain("how does binary search work?") == "dsa"


def test_classifier_math_keywords(mocker):
    mocker.patch("agent.classifier._build_classifier_llm",
                 return_value=_mock_llm("math"))
    from agent.classifier import classify_domain
    assert classify_domain("show me the derivative of x squared") == "math"


def test_classifier_defaults_to_math_on_failure(mocker):
    mocker.patch("agent.classifier._build_classifier_llm",
                 side_effect=RuntimeError("api down"))
    from agent.classifier import classify_domain
    assert classify_domain("anything") == "math"


# ---------------------------------------------------------------------------
# /ask route — domain field returned
# ---------------------------------------------------------------------------

def test_ask_dsa_question_returns_domain(client, mocker):
    mocker.patch("app.classify_domain", return_value="dsa")
    mocker.patch("app.plan_dsa", return_value=LessonPlan(
        concept="binary search", level="beginner",
        steps=[StepPlan(tool="array_pointer",
                        params={"array": [1,3,5,7,9], "algorithm": "binary_search", "target": 7},
                        caption="")],
    ))
    mocker.patch("app.submit_lesson", return_value="test-dsa-job-id")
    res = client.post("/ask", json={"question": "how does binary search work?"})
    assert res.status_code == 202
    data = res.get_json()
    assert data["domain"] == "dsa"
    assert data["concept"] == "binary search"


def test_ask_math_question_returns_domain(client, mocker):
    mocker.patch("app.classify_domain", return_value="math")
    mocker.patch("app.plan_math", return_value=LessonPlan(
        concept="derivative", level="calculus",
        steps=[StepPlan(tool="tangent_line",
                        params={"expression": "x**2", "x_point": 1.0, "domain": [-4,4]},
                        caption="")],
    ))
    mocker.patch("app.submit_lesson", return_value="test-math-job-id")
    res = client.post("/ask", json={"question": "show me the derivative of x squared"})
    assert res.status_code == 202
    assert res.get_json()["domain"] == "math"


# ---------------------------------------------------------------------------
# Real API integration tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_dsa_planner_real_api():
    from agent.dsa_planner import plan_dsa
    result = plan_dsa("show me how binary search works on a sorted array")
    assert isinstance(result, LessonPlan)
    assert result.steps[0].tool in {"array_pointer", "sliding_window", "tree_traversal",
                                     "graph_traversal", "dp_array", "stack_queue", "linked_list"}


@pytest.mark.integration
def test_classifier_real_api_dsa():
    from agent.classifier import classify_domain
    assert classify_domain("explain BFS and DFS on a graph") == "dsa"


@pytest.mark.integration
def test_classifier_real_api_math():
    from agent.classifier import classify_domain
    assert classify_domain("show me the integral of x squared") == "math"
