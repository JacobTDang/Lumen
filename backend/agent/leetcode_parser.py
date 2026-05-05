"""
LeetCode problem → renderable scene + params.

Unlike the planner (which is tuned for short student questions), this parser
is built for full LeetCode problem statements pasted by the user. It extracts
the actual example inputs (array, target, k, capacity, etc.) directly from
the problem prose, then validates the chosen scene's params against the
existing Pydantic schemas in schemas/types.py.

Model stack matches dsa_planner.py:
    Primary  : openai/gpt-oss-120b   (OpenRouter, reasoning: low)
    Fallback : llama-3.3-70b-versatile (Groq)
    Last     : OPENROUTER_MODEL env var (free generic)

Output shape:
    {
        "title":            "Two Sum",
        "scene":            "hashmap_iteration",
        "params":           {"array": [2,7,11,15], "algorithm": "two_sum_hashmap", "target": 9},
        "explanation":      "Walk the array, look up target − v in the map.",
        "why_this_pattern": "Hashmap gives O(1) complement lookup."
    }
"""
import json
import os
import re
from typing import Type

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ValidationError

from schemas.types import (
    BinarySearchAnswerSchema,
    BinarySearchIndexSchema,
    BacktrackingSubsetsSchema,
    BitManipulationSchema,
    DijkstraSchema,
    DP2DSchema,
    DPArraySchema,
    FloydCycleSchema,
    GraphSchema,
    GreedyIntervalSchema,
    GridTraversalSchema,
    HashMapIterationSchema,
    HeapOpsSchema,
    IntervalMergingSchema,
    KadanesSchema,
    LRUCacheSchema,
    LinkedListSchema,
    MatrixRotationSchema,
    MonotonicStackSchema,
    PrefixSumSchema,
    RecursionTreeDCSchema,
    SegmentTreeSchema,
    SlidingWindowVariableSchema,
    StackQueueSchema,
    TopologicalSortSchema,
    TrappingRainWaterSchema,
    TreeTraversalSchema,
    TrieOpsSchema,
    TwoPointersOppositeSchema,
    TwoPointersSameDirSchema,
    UnionFindSchema,
)

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


_SCENE_SCHEMAS: dict[str, Type[BaseModel]] = {
    # array / string patterns
    "two_pointers_opposite":   TwoPointersOppositeSchema,
    "two_pointers_same_dir":   TwoPointersSameDirSchema,
    "sliding_window_variable": SlidingWindowVariableSchema,
    "binary_search_index":     BinarySearchIndexSchema,
    "binary_search_answer":    BinarySearchAnswerSchema,
    "monotonic_stack":         MonotonicStackSchema,
    "hashmap_iteration":       HashMapIterationSchema,
    "prefix_sum":              PrefixSumSchema,
    "kadanes":                 KadanesSchema,
    # advanced patterns
    "interval_merging":        IntervalMergingSchema,
    "backtracking_subsets":    BacktrackingSubsetsSchema,
    "lru_cache":               LRUCacheSchema,
    "grid_traversal":          GridTraversalSchema,
    "heap_ops":                HeapOpsSchema,
    "dp_2d":                   DP2DSchema,
    "trie_ops":                TrieOpsSchema,
    "union_find":              UnionFindSchema,
    "dijkstra":                DijkstraSchema,
    "segment_tree":            SegmentTreeSchema,
    # linked-list / tree / graph / DP / stack-queue
    "linked_list":             LinkedListSchema,
    "tree_traversal":          TreeTraversalSchema,
    "graph_traversal":         GraphSchema,
    "dp_array":                DPArraySchema,
    "stack_queue":             StackQueueSchema,
    # Phase 7 — visual depth + 7 missing patterns
    "floyd_cycle":             FloydCycleSchema,
    "trapping_rain_water":     TrappingRainWaterSchema,
    "greedy_interval":         GreedyIntervalSchema,
    "bit_manipulation":        BitManipulationSchema,
    "topological_sort":        TopologicalSortSchema,
    "matrix_rotation":         MatrixRotationSchema,
    "recursion_tree_dc":       RecursionTreeDCSchema,
}

_SCENE_KEYS = sorted(_SCENE_SCHEMAS.keys())


class ParsedLeetCode(BaseModel):
    title: str
    scene: str
    params: dict
    explanation: str
    why_this_pattern: str
    pseudocode: str = ""
    step_lines: dict = {}


_SYSTEM_PROMPT = """You are converting a pasted LeetCode-style problem statement into a runnable
visualization spec for a Manim-based teaching tool.

You MUST pick exactly one `scene` key from the catalog below and fill in `params`
that match that scene's required schema. Extract the literal example input
(the actual numbers, target, k, capacity, etc.) from the problem prose and use
it as the params — do NOT make up new example data when the problem provides one.

If the problem provides multiple examples, use the FIRST example.
If the example is too long for the schema cap, truncate to the first N elements
that still illustrate the pattern (caps are noted per scene).

SCENE CATALOG (pick one):

ARRAY / STRING PATTERNS
  two_pointers_opposite — L from left, R from right, converge inward
    params: {array: list, algorithm: "palindrome"|"two_sum_sorted"|"container_water"|"reverse_array", target?: int}
    when: palindrome check, two-sum on a SORTED array, container-with-most-water, reverse array

  two_pointers_same_dir — slow + fast both starting from index 0
    params: {array: list[int], algorithm: "remove_duplicates"|"move_zeros"}
    when: remove duplicates from sorted array, move zeros to end

  sliding_window_variable — expanding/contracting window with hashmap counter
    params: {array: list, algorithm: "longest_no_repeat"|"longest_at_most_k_distinct", k?: int}
    when: longest substring without repeating chars, longest substring with at most K distinct chars
    note: array can be a list of single characters for string problems

  binary_search_index — L/M/R pointers on a sorted array searching for an index
    params: {array: list[int sorted asc], algorithm: "find_target"|"first_occurrence", target: int}
    when: classic binary search, first/last occurrence, search insertion position
    note: array MUST be sorted ascending

  binary_search_answer — search a numeric ANSWER space, not array indices
    params: {min_value: int, max_value: int, true_at: int, predicate_label: str}
    when: koko bananas, capacity to ship, smallest divisor, "minimum X such that …"
    note: true_at = the smallest value where the predicate becomes true

  monotonic_stack — stack maintains a monotonic invariant
    params: {array: list[int], algorithm: "next_greater"|"daily_temperatures", monotone: "increasing"|"decreasing"}
    when: next greater element, daily temperatures, largest-rectangle skeleton

  hashmap_iteration — iterate left to right updating a hashmap
    params: {array: list, algorithm: "frequency_count"|"two_sum_hashmap"|"anagram_check", target?: int}
    when: two-sum on UNSORTED array, frequency counting, anagram check

  prefix_sum — input array on top, cumulative-sum array below
    params: {array: list[int], algorithm: "build_prefix"|"range_sum_query", query_range?: [l, r]}
    when: range sum queries, subarray sum problems

  kadanes — running maximum subarray sum
    params: {array: list[int]}
    when: maximum subarray sum, largest contiguous sum

ADVANCED PATTERNS
  interval_merging — merge overlapping intervals on a number line
    params: {intervals: list[list[int]]}    # e.g. [[1,3],[2,6],[8,10]]
    when: merge intervals, insert interval, meeting rooms (cap 12 intervals)

  backtracking_subsets — DFS decision tree growing live
    params: {array: list[int], algorithm: "subsets"|"permutations"}
    when: subsets, permutations, combinations (cap 5 elements)

  lru_cache — hashmap + doubly-linked list with eviction
    params: {operations: list[str], capacity: int}    # e.g. ["put 1 1", "put 2 2", "get 1", "put 3 3"]
    when: LRU cache, design-cache problems (cap capacity 8, ops 15)

  grid_traversal — 2D grid BFS or DFS with frontier expansion
    params: {grid: list[list[int]], start: [r,c], target: [r,c], algorithm: "bfs"|"dfs"}
    when: shortest path on grid, flood fill, number-of-islands skeleton, matrix BFS
    note: grid max 8×8, use 0=open 1=wall

  heap_ops — binary-heap push/pop with sift up/down
    params: {operations: list[str], heap_type: "min"|"max"}    # e.g. ["push 5", "push 3", "pop"]
    when: priority queue, k-largest, k-smallest, heap-sort, top-K

  dp_2d — fill a 2D DP table with dependency arrows
    params: {algorithm: "lcs"|"edit_distance"|"unique_paths", input1: str, input2: str}
    when: longest common subsequence, edit distance, unique paths
    note: for unique_paths pass dimensions as digit strings, e.g. input1="3", input2="3"

  trie_ops — character-by-character tree insert + search
    params: {words: list[str], queries: list[str]}
    when: trie / prefix tree, autocomplete, word dictionary

  union_find — disjoint-set forest with parent[] array
    params: {n: int, operations: list[str]}    # e.g. ["union 0 1", "union 2 3", "find 1"]
    when: union-find, connected components, redundant connection

  dijkstra — graph + distance hashmap, edge relaxation
    params: {num_nodes: int, edges: list[[u,v,w]], source: int}
    when: shortest path on a weighted graph, network delay, cheapest flights

  segment_tree — segment-tree build + range queries
    params: {array: list[int], queries: list[[l,r]]}
    when: range sum queries, range min/max queries (cap array 8)

PHASE 7 PATTERNS (newer — prefer over legacy when applicable)
  floyd_cycle — tortoise & hare cycle detection
    params: {values: list[int], cycle_at: int|null}
    when: linked list cycle detection, find duplicate (LC 287)
    note: cycle_at is the index where the tail loops back; null = no cycle

  trapping_rain_water — two-pointer water trapping on a histogram
    params: {heights: list[int]}
    when: trapping rain water (LC 42)

  greedy_interval — greedy reach/tank-based decisions
    params: {values: list[int], algorithm: "jump_game"|"gas_station"}
    when: jump game (LC 55), gas station (LC 134)

  bit_manipulation — XOR-fold or Brian-Kernighan
    params: {values: list[int], operation: "single_number"|"count_bits"}
    when: single number (LC 136), count set bits (LC 191)

  topological_sort — Kahn's BFS topo sort
    params: {num_nodes: int, edges: list[[u,v]]}
    when: course schedule (LC 207, 210), DAG ordering (cap nodes 8)

  matrix_rotation — in-place 2D matrix transformation
    params: {matrix: list[list[int]], operation: "rotate_90"|"spiral"}
    when: rotate matrix 90° (LC 48), spiral matrix (LC 54)
    note: matrix max 5x5

  recursion_tree_dc — divide-and-conquer recursion tree
    params: {array: list[int], algorithm: "merge_sort"}
    when: merge sort visualization, "how does merge sort work"
    note: array max 8 elements

LINKED LIST / TREE / GRAPH / DP / STACK
  linked_list      — params: {values: list[int], algorithm: "reverse"|"find_middle"|"merge_sorted", values2?: list[int]}
  tree_traversal   — params: {values: list[int|null], algorithm: "bfs"|"dfs"|"inorder"|"preorder"|"postorder"|"height"}
                     note: values is level-order with null for missing nodes, e.g. [1,2,3,null,null,4,5]
  graph_traversal  — params: {num_nodes: int, edges: list[[u,v]], start_node: int, algorithm: "bfs"|"dfs"|"has_cycle", directed: bool}
  dp_array         — params: {algorithm: "fibonacci"|"climbing_stairs"|"house_robber"|"coin_change", n?: int, coins?: list[int], amount?: int}
  stack_queue      — params: {operations: list[str], structure: "stack"|"queue"}

ROUTING TIEBREAKERS
- "two sum" + sorted array  → two_pointers_opposite (algorithm="two_sum_sorted")
- "two sum" + unsorted/no order info → hashmap_iteration (algorithm="two_sum_hashmap")
- "longest substring without repeating characters" → sliding_window_variable (algorithm="longest_no_repeat")
- "merge intervals" / "overlapping intervals" → interval_merging
- "max subarray sum" / "maximum subarray" → kadanes
- "minimum X such that predicate(X) is true" / koko bananas / capacity to ship → binary_search_answer
- "next greater element" / "daily temperatures" → monotonic_stack
- "shortest path" + weighted edges → dijkstra
- "shortest path" + unweighted grid → grid_traversal
- "LCS" / "edit distance" / "unique paths" → dp_2d
- "fibonacci" / "climbing stairs" / "house robber" → dp_array
- "subsets" / "permutations" → backtracking_subsets
- "trie" / "prefix tree" / "autocomplete" → trie_ops
- "connected components" / "union find" / "disjoint set" → union_find
- "LRU" / "design cache" → lru_cache
- "k-largest" / "k-smallest" / "top K" → heap_ops
- "range sum query" / "segment tree" → segment_tree (or prefix_sum if no updates)
- "linked list cycle" / "find duplicate number" / "happy number" → floyd_cycle
- "trapping rain water" / "water between bars" → trapping_rain_water
- "jump game" / "gas station" / "greedy reach" → greedy_interval
- "single number" XOR / "count bits" / bit-manipulation tricks → bit_manipulation
- "course schedule" / "topological order" / DAG dependency resolution → topological_sort
- "rotate matrix 90°" / "spiral matrix" → matrix_rotation
- "merge sort" / divide-and-conquer recursion visualization → recursion_tree_dc

Respond with ONLY a single JSON object — no markdown fences, no prose before or after.

Required fields:
  - title:            short problem name (e.g. "Two Sum", "Valid Palindrome")
  - scene:            one of the catalog keys above
  - params:           object matching that scene's schema
  - explanation:      2-3 sentences on the algorithm approach
  - why_this_pattern: 1 sentence on why this pattern beats the brute force
  - pseudocode:       a SHORT Python-style pseudocode (5-9 lines, max 50 chars
                      per line) implementing the chosen scene's algorithm USING
                      THE USER'S VARIABLE NAMES from the problem prose. If the
                      user wrote `nums = [2,7,11,15]` and `target = 9`, your
                      pseudocode should use `nums` and `target`, NOT `a` or `t`.
                      If they wrote `heights`, use `heights`. If they didn't
                      specify a name, fall back to a domain-appropriate one
                      (`nums`, `arr`, `s`, `heights`, `intervals`, `grid`).
                      Keep it visually digestible — this renders in a small panel.
                      Use Python conventions: `for i in range(n):`, slicing,
                      list comprehensions where natural. No imports.
  - step_lines:       a JSON object mapping each "step kind" for the chosen
                      scene to the 0-indexed LINE NUMBER in YOUR pseudocode
                      where that operation occurs. The renderer uses this to
                      highlight the active line as the algorithm steps through.
                      Use the STEP KIND REFERENCE below — only include kinds
                      relevant to the scene you picked.

STEP KIND REFERENCE (which kinds each scene emits, what they mean):

  two_pointers_opposite:
    palindrome      → match (chars equal), fail (mismatch)
    two_sum_sorted  → match (sum=target), advance_l (sum<target), advance_r (sum>target), fail
    container_water → compute (area = (r-l) * min(h[l], h[r]))
    reverse_array   → swap (a[l] ↔ a[r])
  two_pointers_same_dir:
    remove_duplicates → compare, write (a[slow]=a[fast]), advance_fast, skip
    move_zeros        → compare, swap, skip, advance_fast
  sliding_window_variable:
    longest_no_repeat | longest_at_most_k_distinct → expand (right grows), shrink (left moves), best (new best length)
  binary_search_index:
    find_target | first_occurrence → compare, match, go_right (l=m+1), go_left (r=m-1), not_found
  monotonic_stack:
    next_greater | daily_temperatures → pop (resolve top), push (current i)
  hashmap_iteration:
    two_sum_hashmap → match (complement found), store (seen[v]=i)
    frequency_count | anagram_check → increment (freq[v]+=1)
  prefix_sum:
    build_prefix    → build (prefix[i+1] = prefix[i] + a[i])
    range_sum_query → query (range_sum = prefix[r+1] - prefix[l])
  kadanes:
    no kinds — line highlight handled by catalog mapping
  interval_merging:
    sort, emit (new merged), merge (extend last)
  backtracking_subsets:
    subsets | permutations → enter (recurse), exit (return), leaf (path complete)
  lru_cache:
    hit, miss, update (existing key), insert (new key)
  grid_traversal:
    bfs | dfs → start, visit, enqueue (or recurse), path (target found), fail
  heap_ops:
    push, pop_top, replace_root, swap (sift), empty
  trie_ops:
    walk (descend existing edge), insert_char (new edge), mark_end (word complete),
    miss (search fails), final_hit, final_miss
  union_find:
    noop (same root), linked (parent[ra]=rb), find (lookup root)
  dijkstra:
    settle (heappop), relax (dist update)
  segment_tree:
    build (combine children), query (range query)
  floyd_cycle:
    init, move (slow + fast advanced), meet (cycle found), no_cycle (fast=null)
  trapping_rain_water:
    init, move (running max updated), fill (water added), done
  greedy_interval:
    jump_game   → examine, success, fail
    gas_station → examine, reset, done
  bit_manipulation:
    single_number → init, xor, done
    count_bits    → init, clear, done
  topological_sort:
    init, enqueue (zero in-degree), pop, decrement, cycle, done
  matrix_rotation:
    rotate_90 → phase, swap, reverse_row, done
    spiral    → visit, done
  recursion_tree_dc:
    split, merge, done

If the chosen scene is not listed above, return an empty `step_lines` object.
Always return ALL the kinds the scene's algorithm will actually emit — don't
omit kinds (line highlighting will silently no-op for missing kinds).
"""


def _build_llm() -> ChatOpenAI:
    """Same model stack as dsa_planner.py: gpt-oss-120b → Groq llama → generic OpenRouter."""
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
    """Parse JSON; on failure, fall back to the first balanced {...} block."""
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


def _validate(data: dict) -> ParsedLeetCode:
    scene = data.get("scene")
    if scene not in _SCENE_SCHEMAS:
        raise ValueError(f"unknown scene from model: {scene!r}")

    schema_cls = _SCENE_SCHEMAS[scene]
    params = data.get("params", {}) or {}
    params.pop("scene", None)
    try:
        validated = schema_cls(**params)
    except ValidationError as exc:
        raise ValueError(f"invalid params for scene {scene!r}: {exc}") from exc

    clean_params = validated.model_dump()
    clean_params.pop("scene", None)

    raw_step_lines = data.get("step_lines") or {}
    if not isinstance(raw_step_lines, dict):
        raw_step_lines = {}
    # Coerce values to ints; drop entries that don't parse
    step_lines = {}
    for k, v in raw_step_lines.items():
        try:
            step_lines[str(k)] = int(v)
        except (TypeError, ValueError):
            continue

    # Pseudocode may come back as either a single string with \n, OR a
    # list of strings (some models prefer list-of-lines). Normalize both
    # to a single \n-joined string.
    raw_pseudo = data.get("pseudocode", "")
    if isinstance(raw_pseudo, list):
        pseudo = "\n".join(str(line) for line in raw_pseudo).strip()
    else:
        pseudo = str(raw_pseudo).strip()

    return ParsedLeetCode(
        title=str(data.get("title", "")).strip() or "Untitled",
        scene=scene,
        params=clean_params,
        explanation=str(data.get("explanation", "")).strip(),
        why_this_pattern=str(data.get("why_this_pattern", "")).strip(),
        pseudocode=pseudo,
        step_lines=step_lines,
    )


def parse_problem(raw_text: str, max_retries: int = 2) -> ParsedLeetCode:
    """Parse a pasted LeetCode problem into a renderable scene + params.

    Retries once on JSON parse / validation failure (open-source models
    occasionally emit malformed structure on the first attempt).
    Raises ValueError on empty input or after all retries are exhausted.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("raw_text is required")

    user_msg = f"Problem:\n{raw_text.strip()}"
    last_error: Exception = ValueError("no attempts made")
    for _ in range(max_retries):
        try:
            raw = _call_model(_SYSTEM_PROMPT, user_msg)
            data = _extract_json(raw)
            return _validate(data)
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            continue

    raise ValueError(f"parse failed after {max_retries} attempts: {last_error}") from last_error
