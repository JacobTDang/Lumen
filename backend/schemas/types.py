from typing import List, Literal, Optional
from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Visualization schemas (one per scene type)
# ---------------------------------------------------------------------------

class BubbleSortSchema(BaseModel):
    scene: Literal["bubble_sort"] = "bubble_sort"
    array: List[int]
    caption: str = ""


class FunctionPlotSchema(BaseModel):
    scene: Literal["function_plot"] = "function_plot"
    expression: str
    domain: List[float] = [-4.0, 4.0]
    x_point: Optional[float] = None
    caption: str = ""


class LimitSchema(BaseModel):
    scene: Literal["limit"] = "limit"
    expression: str
    limit_point: float
    domain: List[float] = [-5.0, 5.0]
    caption: str = ""


class TangentLineSchema(BaseModel):
    scene: Literal["tangent_line"] = "tangent_line"
    expression: str
    x_point: float
    domain: List[float] = [-4.0, 4.0]
    caption: str = ""


class RiemannSumSchema(BaseModel):
    scene: Literal["riemann_sum"] = "riemann_sum"
    expression: str
    domain: List[float]
    n: int = 5
    method: Literal["left", "right", "midpoint"] = "left"
    caption: str = ""

    @field_validator("n")
    @classmethod
    def n_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("n must be at least 1")
        return v


class CriticalPointsSchema(BaseModel):
    scene: Literal["critical_points"] = "critical_points"
    expression: str
    domain: List[float] = [-4.0, 4.0]
    caption: str = ""


class LinearFunctionSchema(BaseModel):
    scene: Literal["linear_function"] = "linear_function"
    expression: str
    domain: List[float] = [-5.0, 5.0]
    second_expression: Optional[str] = None
    caption: str = ""


class QuadraticSchema(BaseModel):
    scene: Literal["quadratic"] = "quadratic"
    expression: str
    domain: List[float] = [-5.0, 5.0]
    caption: str = ""


class TrigUnitCircleSchema(BaseModel):
    scene: Literal["trig_unit_circle"] = "trig_unit_circle"
    angle: float = 0.785
    animate_rotation: bool = True
    caption: str = ""


VisualizationSchema = (
    BubbleSortSchema
    | FunctionPlotSchema
    | LimitSchema
    | TangentLineSchema
    | RiemannSumSchema
    | CriticalPointsSchema
    | LinearFunctionSchema
    | QuadraticSchema
    | TrigUnitCircleSchema
)


# ---------------------------------------------------------------------------
# Lesson plan models (planner output)
# ---------------------------------------------------------------------------

class StepPlan(BaseModel):
    tool: str
    params: dict
    caption: str = ""


class LessonPlan(BaseModel):
    concept: str
    level: str
    steps: List[StepPlan]
