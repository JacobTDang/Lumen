from pydantic import BaseModel
from typing import List, Optional


class BubbleSortSchema(BaseModel):
    scene: str = "bubble_sort"
    array: List[int]


class FunctionPlotSchema(BaseModel):
    scene: str = "function_plot"
    expression: str
    domain: List[float] = [-5.0, 5.0]
    point: Optional[float] = None
