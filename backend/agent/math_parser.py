"""
Math problem → renderable scene + algebraic step-by-step breakdown.

Mirrors `leetcode_parser.py` but for math/calculus scenes. Where the LeetCode
parser returns a `pseudocode` string + `step_lines` mapping (because DSA
scenes show code), this returns `steps: list[str]` — a numbered algebraic
breakdown of how to solve the problem (because math scenes already visualize
the process and don't need code).

Output shape:
    {
        "title":            "Riemann Sum",
        "scene":            "riemann_sum",
        "params":           {"expression": "x**2", "domain": [0, 4], "n": 8, "method": "midpoint"},
        "explanation":      "We're approximating ∫x² dx from 0 to 4 with 8 midpoint rectangles.",
        "why_this_pattern": "Riemann sums show how integration is the limit of rectangle sums.",
        "steps": [
            "Step 1: Set up ∫x² dx from 0 to 4",
            "Step 2: Apply the power rule: x³/3",
            "Step 3: Evaluate F(4) - F(0) = 64/3 - 0 = 21.33"
        ]
    }

Same model stack as dsa_planner / leetcode_parser:
    Primary  : openai/gpt-oss-120b   (OpenRouter, reasoning: low)
    Fallback : llama-3.3-70b-versatile (Groq)
    Last     : OPENROUTER_MODEL env var
"""
import json
import os
import re
from typing import List, Type

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ValidationError

from schemas.types import (
    AreaBetweenCurvesSchema,
    ArcLengthSchema,
    AverageValueSchema,
    CobwebSchema,
    ContourSchema,
    CriticalPointsSchema,
    CrossSectionSchema,
    ExponentialSchema,
    FTCSchema,
    FractionSchema,
    FunctionPlotSchema,
    ImproperIntegralSchema,
    InequalitySchema,
    IntegrationByPartsSchema,
    LimitSchema,
    LinearFunctionSchema,
    NumberLineSchema,
    PartialDerivativeSchema,
    QuadraticSchema,
    RiemannSumSchema,
    SequenceSchema,
    ShellMethodSchema,
    SurfacePlotSchema,
    TangentLineSchema,
    TaylorSeriesSchema,
    TransformationSchema,
    TrigUnitCircleSchema,
    USubstitutionSchema,
    VectorFieldSchema,
    VolumeRevolutionSchema,
    WasherMethodSchema,
)

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


_SCENE_SCHEMAS: dict[str, Type[BaseModel]] = {
    # core calculus
    "function_plot":         FunctionPlotSchema,
    "limit":                 LimitSchema,
    "tangent_line":          TangentLineSchema,
    "riemann_sum":           RiemannSumSchema,
    "critical_points":       CriticalPointsSchema,
    # calculus extended
    "volume_revolution":     VolumeRevolutionSchema,
    "taylor_series":         TaylorSeriesSchema,
    "ftc":                   FTCSchema,
    "sequence":              SequenceSchema,
    "cobweb":                CobwebSchema,
    "area_between_curves":   AreaBetweenCurvesSchema,
    "washer_method":         WasherMethodSchema,
    "shell_method":          ShellMethodSchema,
    "arc_length":            ArcLengthSchema,
    "average_value":         AverageValueSchema,
    "u_substitution":        USubstitutionSchema,
    "integration_by_parts":  IntegrationByPartsSchema,
    "improper_integral":     ImproperIntegralSchema,
    "cross_section":         CrossSectionSchema,
    # algebra
    "linear_function":       LinearFunctionSchema,
    "quadratic":             QuadraticSchema,
    "inequality":            InequalitySchema,
    "exponential":           ExponentialSchema,
    "transformation":        TransformationSchema,
    # arithmetic
    "number_line":           NumberLineSchema,
    "fraction":              FractionSchema,
    # trig + 3D
    "trig_unit_circle":      TrigUnitCircleSchema,
    "surface_plot":          SurfacePlotSchema,
    "contour":               ContourSchema,
    "vector_field":          VectorFieldSchema,
    "partial_derivative":    PartialDerivativeSchema,
}

_SCENE_KEYS = sorted(_SCENE_SCHEMAS.keys())


class Alternative(BaseModel):
    """A different scene that could illustrate the same math problem from
    another angle. Surfaced as 1-click 'show me with X instead' buttons."""
    scene: str
    params: dict
    label: str
    why: str = ""


class LessonStep(BaseModel):
    """One scene in a multi-scene math lesson. Each step adds a distinct
    insight, not a parameter tweak of the same scene."""
    scene: str
    params: dict
    caption: str = ""


class ParsedMath(BaseModel):
    title: str
    scene: str
    params: dict
    explanation: str
    why_this_pattern: str
    steps: List[str] = []
    alternatives: List[Alternative] = []
    lesson_steps: List[LessonStep] = []


_SYSTEM_PROMPT = """You are converting a pasted math problem (calculus, algebra,
or arithmetic) into a runnable visualization spec for a Manim-based teaching tool.

You MUST pick exactly one `scene` key from the catalog below and fill in `params`
that match that scene's required schema. Extract the literal expression and
domain from the problem prose — do NOT make up generic examples when the user
provides a specific function or interval.

Expression syntax: use Python / sympy conventions —
    x**2     not x^2
    sin(x), cos(x), tan(x), exp(x), log(x), sqrt(x), pi, E
    No imports, no `import math`.

SCENE CATALOG:

CORE CALCULUS
  function_plot — graph any single-variable function, optionally evaluate at a point
    params: {expression: str, domain: [float, float], x_point: float|null}
    when: "graph f(x)", "plot sin(x)", "evaluate f(2)"

  limit — animate one- and two-sided limit approach
    params: {expression: str, limit_point: float, domain: [float, float]}
    when: "lim x→0 sin(x)/x", "find the limit", continuity questions

  tangent_line — secant line becoming tangent, shows derivative as slope
    params: {expression: str, x_point: float, domain: [float, float]}
    when: "derivative at a point", "tangent line", "instantaneous rate"

  riemann_sum — animated rectangles converging to definite integral
    params: {expression: str, domain: [float, float], n: int (1-50), method: "left"|"right"|"midpoint"}
    when: "definite integral", "Riemann sum", "area under curve"

  critical_points — plots f and f' marking local max/min via first/second derivative tests
    params: {expression: str, domain: [float, float]}
    when: "find local max/min", "critical points", "increasing/decreasing"

CALCULUS EXTENDED (Calc 2 / Series / Integral Apps)
  volume_revolution — disk method for solids of revolution around x-axis
    params: {expression: str, domain: [float, float], n_disks: int (1-20)}
    when: "volume of revolution", "disk method", "solid of revolution"

  taylor_series — partial sums converging to a target function
    params: {expression: str, center: float, max_terms: int (1-12), domain: [float, float]}
    when: "Taylor series", "Maclaurin series", "polynomial approximation"

  ftc — Fundamental Theorem Pt 1: growing area traces F(x) = ∫_a^x f(t)dt
    params: {expression: str, domain: [float, float], start: float}
    when: "FTC", "accumulation function", "antiderivative connection"

  sequence — plot computed terms of a recursive sequence converging to a limit
    params: {formula: str (uses x as aₙ₋₁), a0: float, n_terms: int (1-20)}
    when: "recursive sequence", "convergence of aₙ", aₙ = f(aₙ₋₁) problems

  cobweb — cobweb diagram showing fixed-point iteration
    params: {formula: str, a0: float, n_steps: int, domain: [float, float]}
    when: "cobweb diagram", "fixed-point iteration"

  area_between_curves — shade region between f(x) above and g(x) below
    params: {f_expression: str, g_expression: str, domain: [float, float]}
    when: "area between two curves"

  washer_method — washers from revolving region between two curves around x-axis
    params: {f_expression: str, g_expression: str, domain: [float, float], n_washers: int}
    when: "washer method", "volume between two curves revolved"

  shell_method — cylindrical shells from revolving around y-axis
    params: {expression: str, domain: [float, float], n_shells: int}
    when: "shell method", "revolving around y-axis"

  arc_length — approximate curve length, segments converging to ∫√(1+f′²)dx
    params: {expression: str, domain: [float, float], n_segments: int}
    when: "arc length", "length of a curve"

  average_value — f_avg as horizontal line, area morphs to equal rectangle
    params: {expression: str, domain: [float, float]}
    when: "average value of a function"

  u_substitution — split-screen showing integrand transforming under u=g(x)
    params: {expression: str, u_expression: str, domain: [float, float]}
    when: "u-substitution", "change of variables"

  integration_by_parts — step-by-step ∫u dv = uv − ∫v du
    params: {u_expression: str, dv_expression: str, domain: [float, float]}
    when: "integration by parts", "∫x·eˣ", LIATE rule

  improper_integral — upper bound slides to ∞ showing area converging or diverging
    params: {expression: str, domain: [float, float], improper_bound: "right"|"left"|"both"}
    when: "improper integral", "∫₁^∞ ... dx"

  cross_section — stacked cross-sections (squares/semicircles/triangles) build a volume
    params: {expression: str, domain: [float, float], shape: "square"|"semicircle"|"equilateral_triangle"}
    when: "volume by cross-sections", "non-revolution solid"

ALGEBRA / PRE-CALC
  linear_function — line with slope triangle and y-intercept; optional second line
    params: {expression: str, domain: [float, float], second_expression: str|null}
    when: "graph y = mx + b", "intersection of two lines", "find slope"

  quadratic — parabola with vertex, roots, axis of symmetry
    params: {expression: str, domain: [float, float]}
    when: "graph y = x² + ...", "find vertex", "quadratic roots"

  inequality — solve and shade inequality solution on a number line
    params: {expression: str, domain: [float, float]}
    when: "solve x² < 4", "graph the solution"

  exponential — exponential growth/decay with doubling/half-life markers
    params: {expression: str, domain: [float, float], show_key_points: bool}
    when: "exponential growth", "half-life", "compound interest"

  transformation — function transformation: shift, reflect, stretch
    params: {base_expression: str, transformed_expression: str, domain: [float, float]}
    when: "shift up by 3", "reflect across y-axis", "function transformations"

ARITHMETIC
  number_line — animate addition, subtraction, inequality, or absolute value
    params: {mode: "addition"|"subtraction"|"inequality"|"absolute_value", values: list[float], domain: [float, float], inequality_sign: str}
    when: K-8 arithmetic, basic ops, number sense

  fraction — visual fraction bars for representing/comparing/adding/subtracting fractions
    params: {mode: "represent"|"compare"|"add"|"subtract", fractions: list[[num, denom]]}
    when: fractions, equivalent fractions, adding/subtracting

TRIG + 3D
  trig_unit_circle — unit circle with live sin/cos projections
    params: {angle: float (radians), animate_rotation: bool}
    when: "unit circle", "sin/cos at angle", trig identities

  surface_plot — 3D surface z=f(x,y) with rotating camera
    params: {expression: str, x_domain: [float, float], y_domain: [float, float]}
    when: "3D surface", "z = f(x,y)", multivariable

  contour — level curves of z=f(x,y) colored by height
    params: {expression: str, x_domain: [float, float], y_domain: [float, float], num_levels: int}
    when: "level curves", "contour map"

  vector_field — 2D vector field with arrows or streamlines
    params: {x_expression: str, y_expression: str, domain: [float, float], show_streamlines: bool}
    when: "vector field", "gradient field", flow visualization

  partial_derivative — 3D surface with vertical cross-section showing partial derivative as slope
    params: {expression: str, variable: "x"|"y", fixed_value: float, x_domain: [float, float], y_domain: [float, float]}
    when: "partial derivative", multivariable slope

ROUTING TIEBREAKERS
- "compute / evaluate the integral" / "∫f dx from a to b" → riemann_sum
- "by parts" → integration_by_parts
- "u-substitution" / "let u = ..." → u_substitution
- "improper" / "∫_a^∞" / "∫_-∞^b" → improper_integral
- "volume" + "revolved around x-axis" → volume_revolution
- "volume" + "revolved around y-axis" → shell_method
- "volume between" two curves → washer_method
- "volume by cross-sections" / "stacked squares" → cross_section
- "average value" → average_value
- "arc length" / "length of curve" → arc_length
- "Taylor" / "Maclaurin" → taylor_series
- "FTC" / "F(x) = ∫" / "antiderivative as area" → ftc
- "lim x→" → limit
- "derivative at" / "tangent line at" → tangent_line
- "max" / "min" / "critical points" / "increasing/decreasing" → critical_points
- "sequence aₙ = f(aₙ₋₁)" / "converges to L" → sequence (or cobweb if proof requested)
- "y = mx + b" / "linear" → linear_function
- "y = ax² + bx + c" / "quadratic" / "parabola" → quadratic
- "z = f(x, y)" / 3D surface → surface_plot
- "level curves" / "contour" → contour
- "vector field" / "F(x,y) = ⟨..., ...⟩" → vector_field
- "partial derivative" / "∂f/∂x" → partial_derivative
- "exponential growth/decay" / "e^x" → exponential
- "shift" / "reflect" / "stretch" → transformation
- "graph" / "plot" with no other context → function_plot

Respond with ONLY a single JSON object — no markdown fences, no prose before or after.

Required fields:
  - title:            short problem name (e.g. "Definite Integral", "Find Limit", "Tangent Line")
  - scene:            one of the catalog keys above
  - params:           object matching that scene's schema
  - explanation:      2-3 sentences explaining what the visualization shows
  - why_this_pattern: 1 sentence on why this scene best illustrates the problem
  - steps:            list of 3-7 short algebraic breakdown steps. Each step is
                      one short string showing one move (e.g. "Step 1: Apply
                      power rule: x³/3"). Use plain text — Unicode math symbols
                      (∫, π, ∞, ²) are fine but avoid raw LaTeX backslash
                      sequences. Keep each step under 80 chars.
  - alternatives:     0-2 alternative scene/algorithm combinations that ALSO
                      illustrate this problem from a DIFFERENT ANGLE. For each:
                        - scene:  a different catalog key (not the primary)
                        - params: parameters matching THAT scene's schema
                        - label:  short verb phrase (≤ 35 chars), e.g.
                                  "Show with FTC", "Compare via Riemann"
                        - why:    1 sentence on what the alternative reveals
                      Pick alternatives that change perspective, not minor
                      parameter tweaks. Examples:
                        ∫x·eˣ dx by-parts → primary integration_by_parts,
                                            alt riemann_sum (numerical)
                        Riemann sum       → primary riemann_sum,
                                            alt ftc (antiderivative connection)
                        Derivative at pt  → primary tangent_line,
                                            alt critical_points (broader view)
                        Volume revolution → primary volume_revolution,
                                            alt washer_method (if 2 curves)
                        Linear function   → alt none (not enough variety)
                      Return [] if no alternatives genuinely add value — do NOT
                      pad with weak alternatives.
  - lesson_steps:     0 OR 2-4 ordered scenes for a multi-scene MINI-LESSON.
                      Use only when the problem genuinely benefits from
                      multiple connected visualizations that each add a
                      DISTINCT insight. Each step:
                        - scene:   a catalog key
                        - params:  parameters matching that scene's schema
                        - caption: one short sentence the student should
                                   focus on this step
                      Order: broad context → core concept → application/result.
                      Examples (math):
                        "Explain Riemann sums for ∫x² dx 0 to 4"
                          → 1. function_plot of x² on [0, 4] (the function)
                            2. riemann_sum n=4 (coarse approximation)
                            3. riemann_sum n=20 (converging)
                            4. ftc (antiderivative connection)
                        "Walk through u-substitution for ∫2x·eˣ² dx"
                          → 1. function_plot of 2x·eˣ²
                            2. u_substitution (transformation step)
                            3. ftc (final integration)
                        "Find the derivative of x² at x=2"
                          → leave empty; single tangent_line is direct
                      For STRAIGHTFORWARD problems (single derivative, single
                      limit, plot a function), leave lesson_steps EMPTY.
                      Don't pad. Reserve lesson_steps for problems where
                      the user asks for a walkthrough / breakdown / step-by-
                      step, or where the concept needs multiple viewpoints.
"""


def _build_llm() -> ChatOpenAI:
    """Same model stack as dsa_planner.py and leetcode_parser.py."""
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
        model=os.environ.get("OPENROUTER_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"),
        temperature=0,
    )


def _call_model(system: str, user: str) -> str:
    """Single seam tests can mock to stand in for the LLM call."""
    llm = _build_llm()
    response = llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=user),
    ])
    return response.content or ""


def _clean_raw(raw: str) -> str:
    """Strip reasoning-model artifacts and markdown fences."""
    raw = re.sub(r"<\|channel\|>analysis<\|message\|>.*?(?=<\|channel\|>final<\|message\|>|$)",
                 "", raw, flags=re.DOTALL)
    raw = re.sub(r"<\|channel\|>final<\|message\|>", "", raw)
    raw = re.sub(r"<\|end\|>", "", raw)
    raw = re.sub(r"<thinking>.*?</thinking>", "", raw, flags=re.DOTALL)
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    raw = re.sub(r",(\s*[}\]])", r"\1", raw)  # trailing commas
    return raw.strip()


def _extract_json(raw: str) -> dict:
    cleaned = _clean_raw(raw)
    if not cleaned:
        raise ValueError("model returned empty response")
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end   = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(cleaned[start:end + 1])


def _validate(data: dict) -> ParsedMath:
    scene = data.get("scene")
    if scene not in _SCENE_SCHEMAS:
        raise ValueError(f"unknown math scene from model: {scene!r}")

    schema_cls = _SCENE_SCHEMAS[scene]
    params = data.get("params", {}) or {}
    params.pop("scene", None)
    try:
        validated = schema_cls(**params)
    except ValidationError as exc:
        raise ValueError(f"invalid params for math scene {scene!r}: {exc}") from exc

    clean_params = validated.model_dump()
    clean_params.pop("scene", None)

    # Normalize steps — accept list of strings, or string with newlines, or empty
    raw_steps = data.get("steps", [])
    if isinstance(raw_steps, str):
        steps = [s.strip() for s in raw_steps.split("\n") if s.strip()]
    elif isinstance(raw_steps, list):
        steps = [str(s).strip() for s in raw_steps if str(s).strip()]
    else:
        steps = []

    # Validate alternatives — drop any with bad params (graceful)
    raw_alts = data.get("alternatives") or []
    if not isinstance(raw_alts, list):
        raw_alts = []
    alternatives: List[Alternative] = []
    for raw in raw_alts:
        if not isinstance(raw, dict):
            continue
        alt_scene = raw.get("scene")
        if alt_scene == scene or alt_scene not in _SCENE_SCHEMAS:
            continue
        alt_schema = _SCENE_SCHEMAS[alt_scene]
        alt_params = raw.get("params", {}) or {}
        alt_params.pop("scene", None)
        try:
            alt_validated = alt_schema(**alt_params)
        except ValidationError:
            continue
        alt_clean = alt_validated.model_dump()
        alt_clean.pop("scene", None)
        alternatives.append(Alternative(
            scene=alt_scene,
            params=alt_clean,
            label=str(raw.get("label", ""))[:60].strip() or f"Show as {alt_scene}",
            why=str(raw.get("why", "")).strip(),
        ))
        if len(alternatives) == 2:
            break

    # Validate lesson_steps — drop the WHOLE list if any step has bad params
    raw_lesson = data.get("lesson_steps") or []
    lesson_steps: List[LessonStep] = []
    if isinstance(raw_lesson, list) and 2 <= len(raw_lesson) <= 4:
        candidate: List[LessonStep] = []
        ok = True
        for raw_step in raw_lesson:
            if not isinstance(raw_step, dict):
                ok = False; break
            step_scene = raw_step.get("scene")
            if step_scene not in _SCENE_SCHEMAS:
                ok = False; break
            step_schema = _SCENE_SCHEMAS[step_scene]
            step_params = raw_step.get("params", {}) or {}
            step_params.pop("scene", None)
            try:
                step_validated = step_schema(**step_params)
            except ValidationError:
                ok = False; break
            step_clean = step_validated.model_dump()
            step_clean.pop("scene", None)
            candidate.append(LessonStep(
                scene=step_scene,
                params=step_clean,
                caption=str(raw_step.get("caption", "")).strip(),
            ))
        if ok and len(candidate) >= 2:
            lesson_steps = candidate

    return ParsedMath(
        title=str(data.get("title", "")).strip() or "Untitled",
        scene=scene,
        params=clean_params,
        explanation=str(data.get("explanation", "")).strip(),
        why_this_pattern=str(data.get("why_this_pattern", "")).strip(),
        steps=steps,
        alternatives=alternatives,
        lesson_steps=lesson_steps,
    )


def parse_math(raw_text: str, max_retries: int = 2) -> ParsedMath:
    """Parse a pasted math problem into a renderable scene + algebraic steps.

    Retries once on JSON parse / validation failure (open-source models
    occasionally emit malformed structure on the first attempt).
    Raises ValueError on empty input or after all retries are exhausted.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("raw_text is required")

    user_msg = f"Math problem:\n{raw_text.strip()}"
    last_error: Exception = ValueError("no attempts made")
    for _ in range(max_retries):
        try:
            raw = _call_model(_SYSTEM_PROMPT, user_msg)
            data = _extract_json(raw)
            return _validate(data)
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            continue

    raise ValueError(f"math parse failed after {max_retries} attempts: {last_error}") from last_error
