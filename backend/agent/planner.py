import json
import os
import re

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from schemas.types import LessonPlan, StepPlan

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

SYSTEM_PROMPT = """You are a math visualization tutor. Given a student's question, create a multi-step visual lesson plan.

Available scene tools:

CALCULUS:
  function_plot   — graph any function, evaluate at a point
    params: {"expression": str, "domain": [float, float], "x_point": float|null}

  limit           — animate limit approach from left and right
    params: {"expression": str, "limit_point": float, "domain": [float, float]}

  tangent_line    — secant line becoming tangent, shows derivative
    params: {"expression": str, "x_point": float, "domain": [float, float]}

  riemann_sum     — animated rectangles converging to definite integral
    params: {"expression": str, "domain": [float, float], "n": int, "method": "left"|"right"|"midpoint"}

  critical_points — plots f and f', marks local max/min
    params: {"expression": str, "domain": [float, float]}

ALGEBRA:
  linear_function — plots a line with slope triangle and y-intercept; optionally two lines + intersection
    params: {"expression": str, "domain": [float, float], "second_expression": str|null}

  quadratic       — plots parabola with vertex, roots, axis of symmetry
    params: {"expression": str, "domain": [float, float]}

PRE-CALCULUS / TRIG:
  trig_unit_circle — animates unit circle with live sin/cos projections
    params: {"angle": float, "animate_rotation": bool}

CALCULUS EXTENDED:
  volume_revolution — disk method for solids of revolution around x-axis
    params: {"expression": str, "domain": [float, float], "n_disks": int}
    use for: volume of revolution, disk/washer method, solids of revolution, Calc 2

  taylor_series — partial sums converging to a target function
    params: {"expression": str, "center": float, "max_terms": int, "domain": [float, float]}
    use for: Taylor/Maclaurin series, polynomial approximation, infinite series

  ftc — Fundamental Theorem Part 1: growing area traces out F(x) = ∫_a^x f(t)dt
    params: {"expression": str, "domain": [float, float], "start": float}
    use for: FTC, accumulation function, area-antiderivative connection

  sequence — plots actual computed terms aₙ converging to a limit with a dashed limit line
    params: {"formula": str, "a0": float, "n_terms": int}
    use for: recursive sequences, sequence convergence, show aₙ = f(aₙ₋₁) terms numerically
    IMPORTANT: formula must use x as the variable (x represents aₙ₋₁). Example: aₙ=sqrt(aₙ₋₁+2) → formula="sqrt(x+2)"

  cobweb — cobweb/staircase diagram showing fixed-point iteration converging to L
    params: {"formula": str, "a0": float, "n_steps": int, "domain": [float, float]}
    use for: cobweb diagram, fixed-point iteration, recursive sequence convergence proof, show aₙ → L graphically
    IMPORTANT: formula must use x as the variable

INTEGRAL APPLICATIONS:
  area_between_curves — shade region between f(x) above and g(x) below with computed area
    params: {"f_expression": str, "g_expression": str, "domain": [float, float]}
    use for: area between two curves, consumer surplus, probability density regions

  washer_method — hollow disks (washers) from revolving region between two curves around x-axis
    params: {"f_expression": str, "g_expression": str, "domain": [float, float], "n_washers": int}
    use for: washer method, volume between two curves revolved, hollow solids of revolution

  shell_method — cylindrical shells from revolving region around y-axis, V = 2π∫x·f(x)dx
    params: {"expression": str, "domain": [float, float], "n_shells": int}
    use for: shell method, revolving around y-axis, cylindrical shells, alternative to disk method

  arc_length — approximate curve length with line segments converging to ∫√(1+f′²)dx
    params: {"expression": str, "domain": [float, float], "n_segments": int}
    use for: arc length, curve length formula, ds element, length of a curve

  average_value — f_avg as horizontal line, area under curve morphs to equal rectangle
    params: {"expression": str, "domain": [float, float]}
    use for: average value of a function, mean value theorem for integrals

  u_substitution — split-screen showing integrand transforming as u=g(x) substitution applied
    params: {"expression": str, "u_expression": str, "domain": [float, float]}
    use for: u-substitution, change of variables, ∫f(g(x))g′(x)dx → ∫f(u)du

  integration_by_parts — step-by-step algebra proof of ∫u dv = uv − ∫v du
    params: {"u_expression": str, "dv_expression": str, "domain": [float, float]}
    use for: integration by parts, ∫x·eˣ, ∫x·sin(x), LIATE rule

  improper_integral — upper bound slides to ∞ showing area converging or diverging
    params: {"expression": str, "domain": [float, float], "improper_bound": "right"|"left"}
    use for: improper integrals, ∫₁^∞ f(x)dx, convergence/divergence of unbounded integrals

  cross_section — stacked cross-sections (squares/semicircles) along x-axis build a volume
    params: {"expression": str, "domain": [float, float], "shape": "square"|"semicircle"|"equilateral_triangle"}
    use for: volume by cross-sections, non-revolution solids, V = ∫A(x)dx
    IMPORTANT: formula must use x as the variable. Example: aₙ=sqrt(aₙ₋₁+2) → formula="sqrt(x+2)"

CALCULUS 3 / MULTIVARIABLE:
  surface_plot — 3D surface z=f(x,y) with rotating camera, colored by height
    params: {"expression": str, "x_domain": [float, float], "y_domain": [float, float]}
    use for: multivariable functions, Calc 3, paraboloids, saddle points,
             3D surface visualization, any question involving z = f(x, y)

  contour — level curves of z=f(x,y) colored by height
    params: {"expression": str, "x_domain": [float, float], "y_domain": [float, float], "num_levels": int}
    use for: level curves, contour maps, topographic view of a function

  vector_field — 2D vector field with arrows or streamlines
    params: {"x_expression": str, "y_expression": str, "domain": [float, float], "show_streamlines": bool}
    use for: vector fields, gradient fields, flow visualization, Calc 3/DiffEq

  partial_derivative — 3D surface with vertical cross-section showing partial derivative as slope
    params: {"expression": str, "variable": "x"|"y", "fixed_value": float,
             "x_domain": [float, float], "y_domain": [float, float]}
    use for: partial derivatives, multivariable slopes, Calc 3

ARITHMETIC:
  number_line — animate addition, subtraction, inequalities, or absolute value on a number line
    params: {"mode": "addition"|"subtraction"|"inequality"|"absolute_value",
             "values": [float, ...], "domain": [float, float], "inequality_sign": str}
    use for: K-8 arithmetic, basic operations, number sense, inequalities, absolute value

  fraction — visual fraction bars for representing, comparing, adding, or subtracting fractions
    params: {"mode": "represent"|"compare"|"add"|"subtract", "fractions": [[num, denom], ...]}
    use for: fractions, equivalent fractions, adding/subtracting fractions, comparing fractions

  area_model — rectangle area model for multiplication or algebraic expansion
    params: {"mode": "integer"|"algebraic", "a": str, "b": str}
    use for: multiplication, FOIL, distributive property, polynomial products

ALGEBRA EXTENDED:
  inequality — solve and shade inequality solution on number line
    params: {"expression": str, "domain": [float, float]}
    use for: linear/quadratic inequalities, solution sets, interval notation

  exponential — plot exponential growth/decay with doubling/half-life markers
    params: {"expression": str, "domain": [float, float], "show_key_points": bool}
    use for: exponential functions, growth/decay, doubling time, half-life, e^x, compound interest

  transformation — show a function transformation: shift, reflect, or stretch
    params: {"base_expression": str, "transformed_expression": str, "domain": [float, float]}
    use for: function transformations, horizontal/vertical shifts, reflections, stretches

Expression syntax (sympy/Python): x**2  sin(x)  cos(x)  exp(x)  log(x)  sqrt(x)  tan(x)  pi  E

Planning rules:
- 1 step  : simple/factual questions ("graph X", "what is slope", "plot sin")
- 2 steps : "what is X and how does it work"
- 3 steps : "explain why X", "prove X", conceptual understanding
- 4 steps : "walk me through solving X step by step" (complex multi-concept)
- Order   : broad overview first → specific detail → result/application
- Caption : one clear sentence telling the student exactly what to notice in this step
- Domains : use [-5,5] default; trig on [-6.3,6.3]; zoom in tight for local features
- Always use syntactically valid sympy expressions
- Prefer simple clean expressions: x**2 over nested forms
- Domain should be symmetric and contain the key feature: e.g. [-4,4] for x**2

Respond with ONLY valid JSON — no markdown fences, no explanation:
{"concept": "brief concept name", "level": "arithmetic|algebra|pre_calculus|calculus", "steps": [
  {"tool": "<scene_key>", "params": {<params>}, "caption": "<one sentence>"},
  ...
]}"""

_VALID_TOOLS = {
    "function_plot", "limit", "tangent_line", "riemann_sum", "critical_points",
    "volume_revolution", "taylor_series", "ftc", "sequence", "cobweb",
    "area_between_curves", "washer_method", "shell_method", "arc_length",
    "average_value", "u_substitution", "integration_by_parts",
    "improper_integral", "cross_section",
    "linear_function", "quadratic", "trig_unit_circle",
    "surface_plot", "contour", "vector_field", "partial_derivative",
    "number_line", "fraction", "area_model",
    "inequality", "exponential", "transformation",
}


def _build_llm() -> ChatOpenAI:
    # Use Groq if key is available, fall back to OpenRouter
    if os.environ.get("GROQ_API_KEY"):
        return ChatOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ["GROQ_API_KEY"],
            model=os.environ.get("GROQ_PLANNER_MODEL", "llama-3.3-70b-versatile"),
            temperature=0,
        )
    return ChatOpenAI(
        base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        api_key=os.environ["OPENROUTER_API_KEY"],
        model=os.environ.get("OPENROUTER_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"),
        temperature=0,
    )


def plan(question: str, max_retries: int = 3) -> LessonPlan:
    llm = _build_llm()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=question),
    ]

    last_error: Exception = RuntimeError("no attempts made")
    for attempt in range(1, max_retries + 1):
        try:
            response = llm.invoke(messages)
            raw = response.content.strip()
            if not raw:
                raise ValueError(f"Model returned empty response (attempt {attempt})")
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            raw = raw.strip()
            data = json.loads(raw)
            break  # success
        except Exception as e:
            last_error = e
            if attempt == max_retries:
                raise ValueError(f"Planner failed after {max_retries} attempts: {last_error}") from last_error
            continue

    steps = []
    for s in data.get("steps", []):
        tool = s.get("tool", "")
        if tool not in _VALID_TOOLS:
            raise ValueError(f"Unknown tool from planner: {tool!r}")
        steps.append(StepPlan(
            tool=tool,
            params=s.get("params", {}),
            caption=s.get("caption", ""),
        ))

    if not steps:
        raise ValueError("Planner returned no steps")

    return LessonPlan(
        concept=data.get("concept", ""),
        level=data.get("level", "calculus"),
        steps=steps,
    )
