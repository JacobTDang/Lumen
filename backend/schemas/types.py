from typing import List, Literal, Optional, Union
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


class SurfacePlotSchema(BaseModel):
    scene: Literal["surface_plot"] = "surface_plot"
    expression: str
    x_domain: List[float] = [-3.0, 3.0]
    y_domain: List[float] = [-3.0, 3.0]
    caption: str = ""


# ---------------------------------------------------------------------------
# DSA schemas
# ---------------------------------------------------------------------------

class ArrayPointerSchema(BaseModel):
    scene: Literal["array_pointer"] = "array_pointer"
    array: List[Union[int, str]]
    algorithm: Literal["binary_search", "two_pointers", "palindrome"] = "binary_search"
    target: Optional[int] = None
    caption: str = ""


class SlidingWindowSchema(BaseModel):
    scene: Literal["sliding_window"] = "sliding_window"
    array: List[Union[int, str]]
    algorithm: Literal["max_subarray_fixed", "longest_unique_substring"] = "max_subarray_fixed"
    k: Optional[int] = 3
    caption: str = ""


class LinkedListSchema(BaseModel):
    scene: Literal["linked_list"] = "linked_list"
    values: List[int]
    algorithm: Literal["reverse", "find_middle", "merge_sorted"] = "reverse"
    values2: Optional[List[int]] = None
    caption: str = ""


class TreeTraversalSchema(BaseModel):
    scene: Literal["tree_traversal"] = "tree_traversal"
    values: List[Optional[int]]
    algorithm: Literal["inorder", "preorder", "postorder", "bfs", "dfs", "height"] = "bfs"
    caption: str = ""


class GraphSchema(BaseModel):
    scene: Literal["graph_traversal"] = "graph_traversal"
    num_nodes: int
    edges: List[List[int]]
    start_node: int = 0
    algorithm: Literal["bfs", "dfs", "has_cycle"] = "bfs"
    directed: bool = False
    caption: str = ""


class DPArraySchema(BaseModel):
    scene: Literal["dp_array"] = "dp_array"
    algorithm: Literal["fibonacci", "climbing_stairs", "house_robber", "coin_change"]
    n: Optional[int] = 8
    coins: Optional[List[int]] = None
    amount: Optional[int] = None
    caption: str = ""


class StackQueueSchema(BaseModel):
    scene: Literal["stack_queue"] = "stack_queue"
    operations: List[str]
    structure: Literal["stack", "queue"] = "stack"
    caption: str = ""


# ---------------------------------------------------------------------------
# Arithmetic schemas
# ---------------------------------------------------------------------------

class NumberLineSchema(BaseModel):
    scene: Literal["number_line"] = "number_line"
    mode: Literal["addition", "subtraction", "inequality", "absolute_value"] = "addition"
    values: List[float]
    domain: List[float] = [-2.0, 12.0]
    inequality_sign: str = ">"
    caption: str = ""


class FractionSchema(BaseModel):
    scene: Literal["fraction"] = "fraction"
    mode: Literal["represent", "compare", "add", "subtract"] = "represent"
    fractions: List[List[int]]
    caption: str = ""


class AreaModelSchema(BaseModel):
    scene: Literal["area_model"] = "area_model"
    mode: Literal["integer", "algebraic"] = "integer"
    a: str
    b: str
    caption: str = ""


# ---------------------------------------------------------------------------
# Algebra extension schemas
# ---------------------------------------------------------------------------

class InequalitySchema(BaseModel):
    scene: Literal["inequality"] = "inequality"
    expression: str
    domain: List[float] = [-10.0, 10.0]
    caption: str = ""


class ExponentialSchema(BaseModel):
    scene: Literal["exponential"] = "exponential"
    expression: str
    domain: List[float] = [-3.0, 5.0]
    show_key_points: bool = True
    caption: str = ""


class TransformationSchema(BaseModel):
    scene: Literal["transformation"] = "transformation"
    base_expression: str
    transformed_expression: str
    domain: List[float] = [-5.0, 5.0]
    caption: str = ""


# ---------------------------------------------------------------------------
# Calculus extension schemas
# ---------------------------------------------------------------------------

class VolumeRevolutionSchema(BaseModel):
    scene: Literal["volume_revolution"] = "volume_revolution"
    expression: str
    domain: List[float]
    n_disks: int = 8
    caption: str = ""


class TaylorSeriesSchema(BaseModel):
    scene: Literal["taylor_series"] = "taylor_series"
    expression: str
    center: float = 0.0
    max_terms: int = 5
    domain: List[float] = [-5.0, 5.0]
    caption: str = ""


class FTCSchema(BaseModel):
    scene: Literal["ftc"] = "ftc"
    expression: str
    domain: List[float] = [-1.0, 5.0]
    start: float = 0.0
    caption: str = ""


class SequenceSchema(BaseModel):
    scene: Literal["sequence"] = "sequence"
    formula: str                        # recursive formula f(x), where aₙ = f(aₙ₋₁)
    a0: float = 0.0
    n_terms: int = 8
    caption: str = ""


class CobwebSchema(BaseModel):
    scene: Literal["cobweb"] = "cobweb"
    formula: str
    a0: float = 0.0
    n_steps: int = 8
    domain: List[float] = [0.0, 4.0]
    caption: str = ""


class AreaBetweenCurvesSchema(BaseModel):
    scene: Literal["area_between_curves"] = "area_between_curves"
    f_expression: str
    g_expression: str
    domain: List[float]
    caption: str = ""


class WasherMethodSchema(BaseModel):
    scene: Literal["washer_method"] = "washer_method"
    f_expression: str
    g_expression: str
    domain: List[float]
    n_washers: int = 8
    caption: str = ""


class ShellMethodSchema(BaseModel):
    scene: Literal["shell_method"] = "shell_method"
    expression: str
    domain: List[float]
    n_shells: int = 8
    caption: str = ""


class ArcLengthSchema(BaseModel):
    scene: Literal["arc_length"] = "arc_length"
    expression: str
    domain: List[float]
    n_segments: int = 8
    caption: str = ""


class AverageValueSchema(BaseModel):
    scene: Literal["average_value"] = "average_value"
    expression: str
    domain: List[float]
    caption: str = ""


class USubstitutionSchema(BaseModel):
    scene: Literal["u_substitution"] = "u_substitution"
    expression: str
    u_expression: str
    domain: List[float]
    caption: str = ""


class IntegrationByPartsSchema(BaseModel):
    scene: Literal["integration_by_parts"] = "integration_by_parts"
    u_expression: str
    dv_expression: str
    domain: List[float] = [0.0, 2.0]
    caption: str = ""


class ImproperIntegralSchema(BaseModel):
    scene: Literal["improper_integral"] = "improper_integral"
    expression: str
    domain: List[float]
    improper_bound: Literal["right", "left", "both"] = "right"
    caption: str = ""


class CrossSectionSchema(BaseModel):
    scene: Literal["cross_section"] = "cross_section"
    expression: str
    domain: List[float]
    shape: Literal["square", "semicircle", "equilateral_triangle"] = "square"
    caption: str = ""


# ---------------------------------------------------------------------------
# Calc 3 extension schemas
# ---------------------------------------------------------------------------

class ContourSchema(BaseModel):
    scene: Literal["contour"] = "contour"
    expression: str
    x_domain: List[float] = [-3.0, 3.0]
    y_domain: List[float] = [-3.0, 3.0]
    num_levels: int = 8
    caption: str = ""


class VectorFieldSchema(BaseModel):
    scene: Literal["vector_field"] = "vector_field"
    x_expression: str
    y_expression: str
    domain: List[float] = [-3.0, 3.0]
    show_streamlines: bool = False
    caption: str = ""


class PartialDerivativeSchema(BaseModel):
    scene: Literal["partial_derivative"] = "partial_derivative"
    expression: str
    variable: Literal["x", "y"] = "x"
    fixed_value: float = 0.0
    x_domain: List[float] = [-3.0, 3.0]
    y_domain: List[float] = [-3.0, 3.0]
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
    | SurfacePlotSchema
    | NumberLineSchema
    | FractionSchema
    | AreaModelSchema
    | InequalitySchema
    | ExponentialSchema
    | TransformationSchema
    | VolumeRevolutionSchema
    | TaylorSeriesSchema
    | FTCSchema
    | SequenceSchema
    | CobwebSchema
    | ContourSchema
    | VectorFieldSchema
    | PartialDerivativeSchema
    | ArrayPointerSchema
    | SlidingWindowSchema
    | LinkedListSchema
    | TreeTraversalSchema
    | GraphSchema
    | DPArraySchema
    | StackQueueSchema
    | AreaBetweenCurvesSchema
    | WasherMethodSchema
    | ShellMethodSchema
    | ArcLengthSchema
    | AverageValueSchema
    | USubstitutionSchema
    | IntegrationByPartsSchema
    | ImproperIntegralSchema
    | CrossSectionSchema
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
