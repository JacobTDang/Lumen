from typing import List, Literal, Optional
from pydantic import BaseModel, field_validator


class BubbleSortSchema(BaseModel):
    scene: Literal["bubble_sort"] = "bubble_sort"
    array: List[int]


class FunctionPlotSchema(BaseModel):
    scene: Literal["function_plot"] = "function_plot"
    expression: str
    domain: List[float] = [-4.0, 4.0]
    x_point: Optional[float] = None


class LimitSchema(BaseModel):
    scene: Literal["limit"] = "limit"
    expression: str
    limit_point: float
    domain: List[float] = [-5.0, 5.0]


class TangentLineSchema(BaseModel):
    scene: Literal["tangent_line"] = "tangent_line"
    expression: str
    x_point: float
    domain: List[float] = [-4.0, 4.0]


class RiemannSumSchema(BaseModel):
    scene: Literal["riemann_sum"] = "riemann_sum"
    expression: str
    domain: List[float]
    n: int = 5
    method: Literal["left", "right", "midpoint"] = "left"

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


VisualizationSchema = (
    BubbleSortSchema
    | FunctionPlotSchema
    | LimitSchema
    | TangentLineSchema
    | RiemannSumSchema
    | CriticalPointsSchema
)
