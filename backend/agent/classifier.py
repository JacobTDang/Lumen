import json
import os
import re

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from schemas.types import (
    CriticalPointsSchema,
    FunctionPlotSchema,
    LimitSchema,
    RiemannSumSchema,
    TangentLineSchema,
    VisualizationSchema,
)

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

SYSTEM_PROMPT = """You are a calculus visualization assistant for students.
Given a calculus question, choose the best visualization type and extract the parameters.

Scene types:
- function_plot  : graph a function, evaluate at a point
- limit          : limits, continuity, L'Hospital's rule, limit definition of derivative
- tangent_line   : derivative, tangent/secant line, instantaneous rate of change, Newton's method
- riemann_sum    : definite integral, area under/between curves, Riemann sums
- critical_points: max/min, critical points, increasing/decreasing, concavity, optimization

Expression syntax (sympy/Python): x**2  sin(x)  cos(x)  exp(x)  log(x)  sqrt(x)  tan(x)  pi  E

Respond with ONLY valid JSON — no explanation, no markdown fences:
{"scene": "<type>", "params": {<params>}}

Param schemas:
  function_plot   : {"expression": str, "domain": [float, float], "x_point": float|null}
  limit           : {"expression": str, "limit_point": float, "domain": [float, float]}
  tangent_line    : {"expression": str, "x_point": float, "domain": [float, float]}
  riemann_sum     : {"expression": str, "domain": [float, float], "n": int, "method": "left"|"right"|"midpoint"}
  critical_points : {"expression": str, "domain": [float, float]}
"""

_SCHEMA_MAP = {
    "function_plot":   FunctionPlotSchema,
    "limit":           LimitSchema,
    "tangent_line":    TangentLineSchema,
    "riemann_sum":     RiemannSumSchema,
    "critical_points": CriticalPointsSchema,
}


def _build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        api_key=os.environ["OPENROUTER_API_KEY"],
        model=os.environ.get("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct:free"),
        temperature=0,
    )


def classify(question: str) -> VisualizationSchema:
    llm = _build_llm()
    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=question),
    ])

    raw = response.content.strip()
    # Strip markdown code fences some models add despite instructions
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()

    data = json.loads(raw)
    scene_type = data["scene"]
    params = data.get("params", {})
    params["scene"] = scene_type

    schema_cls = _SCHEMA_MAP.get(scene_type)
    if schema_cls is None:
        raise ValueError(f"Unknown scene type from classifier: {scene_type!r}")

    return schema_cls(**params)
