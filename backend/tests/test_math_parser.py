"""
Tests for backend/agent/math_parser.py.

Mirrors test_leetcode_parser.py — mock the _call_model seam, no real API.
"""
import json

import pytest


def _patch_model(mocker, payload: str):
    return mocker.patch("agent.math_parser._call_model", return_value=payload)


def _patch_model_sequence(mocker, payloads: list[str]):
    return mocker.patch("agent.math_parser._call_model", side_effect=payloads)


# ── happy paths ──────────────────────────────────────────────────────────────

def test_parse_definite_integral_routes_to_riemann_sum(mocker):
    payload = json.dumps({
        "title": "Definite Integral",
        "scene": "riemann_sum",
        "params": {
            "expression": "x**2",
            "domain": [0, 4],
            "n": 8,
            "method": "midpoint",
        },
        "explanation": "Approximate ∫x² dx from 0 to 4 with 8 midpoint rectangles.",
        "why_this_pattern": "Riemann sums show how integration is the limit of rectangle sums.",
        "steps": [
            "Step 1: Set up ∫x² dx from 0 to 4",
            "Step 2: Apply the power rule: x³/3",
            "Step 3: Evaluate F(4) - F(0) = 64/3 ≈ 21.33",
        ],
    })
    _patch_model(mocker, payload)

    from agent.math_parser import parse_math
    result = parse_math("Compute ∫x² dx from 0 to 4 using a Riemann sum.")

    assert result.scene == "riemann_sum"
    assert result.params["expression"] == "x**2"
    assert result.params["domain"] == [0.0, 4.0]
    assert len(result.steps) == 3
    assert "power rule" in result.steps[1].lower()


def test_parse_limit_routes_to_limit(mocker):
    payload = json.dumps({
        "title": "Find the Limit",
        "scene": "limit",
        "params": {
            "expression": "sin(x)/x",
            "limit_point": 0,
            "domain": [-2, 2],
        },
        "explanation": "Animate the limit as x approaches 0 from both sides.",
        "why_this_pattern": "The two-sided animation makes the value at the singularity visible.",
        "steps": [
            "Step 1: Note that sin(0)/0 is indeterminate",
            "Step 2: Apply L'Hopital: lim sin(x)/x = lim cos(x)/1",
            "Step 3: Evaluate cos(0) = 1",
        ],
    })
    _patch_model(mocker, payload)

    from agent.math_parser import parse_math
    result = parse_math("Find lim x→0 of sin(x)/x")

    assert result.scene == "limit"
    assert result.params["expression"] == "sin(x)/x"
    assert result.params["limit_point"] == 0


def test_parse_tangent_routes_to_tangent_line(mocker):
    payload = json.dumps({
        "title": "Derivative at a Point",
        "scene": "tangent_line",
        "params": {"expression": "x**3", "x_point": 2, "domain": [-3, 3]},
        "explanation": "Show the secant approaching the tangent at x = 2.",
        "why_this_pattern": "Visualizes derivative as the slope of the tangent line.",
        "steps": [
            "Step 1: f(x) = x³, so f'(x) = 3x²",
            "Step 2: f'(2) = 3·4 = 12",
            "Step 3: Tangent line: y = 12(x - 2) + 8",
        ],
    })
    _patch_model(mocker, payload)

    from agent.math_parser import parse_math
    result = parse_math("Find the derivative of x^3 at x = 2")

    assert result.scene == "tangent_line"
    assert result.params["x_point"] == 2


def test_parse_integration_by_parts(mocker):
    payload = json.dumps({
        "title": "Integration by Parts",
        "scene": "integration_by_parts",
        "params": {
            "u_expression": "x",
            "dv_expression": "exp(x)",
            "domain": [0, 2],
        },
        "explanation": "Apply ∫u dv = uv − ∫v du with u=x, dv=eˣ dx.",
        "why_this_pattern": "LIATE rule prefers x over eˣ as u.",
        "steps": [
            "Step 1: Choose u = x, dv = eˣ dx",
            "Step 2: Compute du = dx, v = eˣ",
            "Step 3: Apply formula: x·eˣ - ∫eˣ dx",
            "Step 4: Result: x·eˣ - eˣ + C",
        ],
    })
    _patch_model(mocker, payload)

    from agent.math_parser import parse_math
    result = parse_math("Integrate x·e^x by parts from 0 to 2")

    assert result.scene == "integration_by_parts"
    assert result.params["u_expression"] == "x"
    assert len(result.steps) == 4


# ── output cleanup ───────────────────────────────────────────────────────────

def test_parse_strips_markdown_fences(mocker):
    payload = "```json\n" + json.dumps({
        "title": "X", "scene": "function_plot",
        "params": {"expression": "x**2", "domain": [-3, 3]},
        "explanation": "ok", "why_this_pattern": "ok", "steps": [],
    }) + "\n```"
    _patch_model(mocker, payload)

    from agent.math_parser import parse_math
    result = parse_math("plot x squared")
    assert result.scene == "function_plot"


def test_parse_steps_as_string_normalized(mocker):
    """Some models return steps as a single string with newlines instead of a list."""
    payload = json.dumps({
        "title": "X", "scene": "limit",
        "params": {"expression": "x", "limit_point": 0, "domain": [-1, 1]},
        "explanation": "ok", "why_this_pattern": "ok",
        "steps": "Step 1: First\nStep 2: Second\nStep 3: Third",
    })
    _patch_model(mocker, payload)

    from agent.math_parser import parse_math
    result = parse_math("anything")
    assert result.steps == ["Step 1: First", "Step 2: Second", "Step 3: Third"]


# ── retry behavior ───────────────────────────────────────────────────────────

def test_parse_retries_on_first_attempt_failure(mocker):
    good = json.dumps({
        "title": "Integral", "scene": "riemann_sum",
        "params": {"expression": "x", "domain": [0, 1], "n": 5, "method": "left"},
        "explanation": "ok", "why_this_pattern": "ok", "steps": [],
    })
    mock = _patch_model_sequence(mocker, ["this is not json", good])

    from agent.math_parser import parse_math
    result = parse_math("integrate x")
    assert result.scene == "riemann_sum"
    assert mock.call_count == 2


def test_parse_raises_after_all_retries_fail(mocker):
    _patch_model_sequence(mocker, ["garbage one", "garbage two"])

    from agent.math_parser import parse_math
    with pytest.raises(ValueError, match="parse failed"):
        parse_math("anything")


# ── validation ───────────────────────────────────────────────────────────────

def test_parse_unknown_scene_raises(mocker):
    payload = json.dumps({
        "title": "X", "scene": "lru_cache",  # DSA scene, not math
        "params": {}, "explanation": "x", "why_this_pattern": "y", "steps": [],
    })
    _patch_model_sequence(mocker, [payload, payload])

    from agent.math_parser import parse_math
    with pytest.raises(ValueError, match="unknown math scene"):
        parse_math("anything")


def test_parse_invalid_params_raises(mocker):
    """riemann_sum requires n in 1..50; 100 should fail Pydantic."""
    payload = json.dumps({
        "title": "X", "scene": "riemann_sum",
        "params": {"expression": "x", "domain": [0, 1], "n": 100, "method": "left"},
        "explanation": "x", "why_this_pattern": "y", "steps": [],
    })
    _patch_model_sequence(mocker, [payload, payload])

    from agent.math_parser import parse_math
    with pytest.raises(ValueError, match="invalid params"):
        parse_math("anything")


def test_parse_empty_response_raises(mocker):
    _patch_model_sequence(mocker, ["", ""])

    from agent.math_parser import parse_math
    with pytest.raises(ValueError):
        parse_math("anything")


def test_parse_empty_input_raises():
    from agent.math_parser import parse_math
    with pytest.raises(ValueError, match="raw_text"):
        parse_math("   ")


# ── integration (real model) ─────────────────────────────────────────────────

@pytest.mark.integration
def test_parse_real_riemann_routes_correctly():
    """End-to-end: real LLM should route a Riemann-sum problem correctly."""
    from agent.math_parser import parse_math
    result = parse_math(
        "Approximate the integral of x squared from 0 to 4 using a Riemann sum "
        "with 8 rectangles."
    )
    assert result.scene in ("riemann_sum", "function_plot", "ftc")
    assert isinstance(result.params.get("expression"), str)
    assert "x" in result.params["expression"]
