"""
DSA planner: routes student questions about algorithms and data structures
to the correct visualization scene with appropriate parameters.
"""
import json
import os
import re

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from schemas.types import LessonPlan, StepPlan

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

SYSTEM_PROMPT = """You are a DSA (Data Structures & Algorithms) visualization tutor.
Given a student's question, create a visual lesson plan using the scene tools below.

Available scene tools:

ARRAY PATTERNS (PREFER THESE — they are pattern-specific and visually richer):
  two_pointers_opposite — L from left, R from right, converge inward
    params: {"array": [...], "algorithm": "palindrome"|"two_sum_sorted"|"container_water"|"reverse_array",
             "target": int|null}
    use for: palindrome check, two sum on sorted array, container with most water, reverse array
    note: array MUST be sorted for two_sum_sorted

  two_pointers_same_dir — slow + fast pointers both starting from left
    params: {"array": [int, ...], "algorithm": "remove_duplicates"|"move_zeros"}
    use for: remove duplicates from sorted array, move zeros to end

  sliding_window_variable — expanding/contracting window with hashmap counter
    params: {"array": [...], "algorithm": "longest_no_repeat"|"longest_at_most_k_distinct",
             "k": int|null}
    use for: longest substring without repeating characters, longest substring with at most K distinct

  binary_search_index — L/M/R pointers on sorted array searching for an index
    params: {"array": [int, ...], "algorithm": "find_target"|"first_occurrence", "target": int}
    use for: binary search, first occurrence, search insertion position
    note: array MUST be sorted ascending

  binary_search_answer — search the answer space (not indices)
    params: {"min_value": int, "max_value": int, "true_at": int, "predicate_label": "feasible(x)"}
    use for: koko bananas, capacity to ship, smallest divisor — when the search is over a numeric ANSWER, not array indices
    note: true_at = the smallest value where the predicate becomes true

  monotonic_stack — stack maintains monotonic invariant
    params: {"array": [int, ...], "algorithm": "next_greater"|"daily_temperatures",
             "monotone": "increasing"|"decreasing"}
    use for: next greater element, daily temperatures, largest rectangle skeleton

  hashmap_iteration — iterate left to right, updating a hashmap
    params: {"array": [...], "algorithm": "frequency_count"|"two_sum_hashmap"|"anagram_check",
             "target": int|null}
    use for: two sum (unsorted), frequency counting, anagram check

  prefix_sum — cumulative sum array (input on top, prefix below)
    params: {"array": [int, ...], "algorithm": "build_prefix"|"range_sum_query",
             "query_range": [l, r]|null}
    use for: range sum queries, subarray sum, prefix-sum-based problems

  kadanes — running max-subarray sum
    params: {"array": [int, ...]}
    use for: maximum subarray sum, largest contiguous sum, "find best window of any size"

ADVANCED DSA PATTERNS:
  interval_merging — number-line bars, merge overlapping intervals
    params: {"intervals": [[s1,e1],[s2,e2],...]}
    use for: merge intervals, insert interval, meeting rooms

  backtracking_subsets — DFS decision tree growing live
    params: {"array": [int, ...], "algorithm": "subsets"|"permutations"}
    use for: subsets, permutations, combinations, decision-tree problems

  lru_cache — hashmap + doubly-linked list with eviction
    params: {"operations": ["put k v", "get k", ...], "capacity": int}
    use for: LRU cache, MRU cache, design-cache problems

  grid_traversal — 2D grid BFS/DFS with frontier expansion
    params: {"grid": [[0|1, ...], ...], "start": [r,c], "target": [r,c],
             "algorithm": "bfs"|"dfs"}
    use for: shortest path on grid, flood fill, reachability, number of islands skeleton

  heap_ops — binary heap push/pop with sift up/down
    params: {"operations": ["push N", "pop", ...], "heap_type": "min"|"max"}
    use for: priority queue, k-largest, k-smallest, top-K problems, heap-sort

  dp_2d — fill 2D DP table with dependency arrows
    params: {"algorithm": "lcs"|"edit_distance"|"unique_paths",
             "input1": str, "input2": str}
    use for: longest common subsequence, edit distance, unique paths, 2D DP problems
    note: for unique_paths pass dimensions as strings, e.g. input1="3", input2="3"

  trie_ops — character-by-character tree insert + search
    params: {"words": [str, ...], "queries": [str, ...]}
    use for: trie/prefix tree, autocomplete, word search, dictionary lookup

  union_find — disjoint-set forest with parent[] array
    params: {"n": int, "operations": ["union a b", "find x", ...]}
    use for: union-find, disjoint-set, connected components, redundant connection

  dijkstra — graph + distance hashmap, edge relaxation
    params: {"num_nodes": int, "edges": [[u,v,w], ...], "source": int}
    use for: shortest path on weighted graph, network delay, cheapest flights

  segment_tree — segment tree build + range queries
    params: {"array": [int, ...], "queries": [[l,r], ...]}
    use for: range sum queries, range min/max queries, online range problems

PHASE 7 PATTERNS (newer, prefer over legacy when applicable):
  floyd_cycle — Floyd's tortoise & hare cycle detection
    params: {"values": [int, ...], "cycle_at": int|null}
    use for: linked list cycle detection, find duplicate (LC 287), happy number
    note: cycle_at = index where the tail loops back; null = no cycle

  trapping_rain_water — two-pointer water trapping on a histogram
    params: {"heights": [int, ...]}
    use for: trapping rain water (LC 42), container that catches water

  greedy_interval — greedy reach/tank-based decisions
    params: {"values": [int, ...], "algorithm": "jump_game"|"gas_station"}
    use for: jump game (LC 55), gas station (LC 134), reach-based greedy

  bit_manipulation — bit-level XOR / Brian-Kernighan
    params: {"values": [int, ...], "operation": "single_number"|"count_bits"}
    use for: single number (LC 136 XOR-fold), count set bits (LC 191)

  topological_sort — Kahn's BFS topological sort
    params: {"num_nodes": int, "edges": [[u, v], ...]}
    use for: course schedule (LC 207, 210), dependency resolution, DAG ordering

  matrix_rotation — in-place 2D matrix transformation
    params: {"matrix": [[int, ...], ...], "operation": "rotate_90"|"spiral"}
    use for: rotate matrix 90° (LC 48), spiral matrix (LC 54)
    note: matrix max 5x5 for visual budget

  recursion_tree_dc — divide-and-conquer recursion tree (merge sort)
    params: {"array": [int, ...], "algorithm": "merge_sort"}
    use for: merge sort, divide-and-conquer visualization, "how does merge sort work"
    note: array max 8 elements for visual budget

LEGACY ARRAYS (only fall back if no pattern above fits):
  array_pointer — generic two-pointer or binary search
    params: {"array": [...], "algorithm": "binary_search"|"two_pointers"|"palindrome",
             "target": int|null}

  sliding_window — fixed-size window
    params: {"array": [...], "algorithm": "max_subarray_fixed"|"longest_unique_substring",
             "k": int|null}

LINKED LISTS:
  linked_list — animated linked list with pointer labels
    params: {"values": [int, ...], "algorithm": "reverse"|"find_middle"|"merge_sorted",
             "values2": [int, ...]|null}
    use for: reverse linked list, find middle node, merge two sorted lists

TREES:
  tree_traversal — binary tree with animated traversal coloring
    params: {"values": [int|null, ...], "algorithm": "bfs"|"dfs"|"inorder"|"preorder"|"postorder"|"height"}
    use for: tree BFS, DFS, inorder/preorder/postorder traversal, tree height
    note: values is level-order array, use null for missing nodes, e.g. [1,2,3,null,null,4,5]

GRAPHS:
  graph_traversal — graph BFS or DFS with queue/stack state shown
    params: {"num_nodes": int, "edges": [[u,v], ...], "start_node": int,
             "algorithm": "bfs"|"dfs"|"has_cycle", "directed": bool}
    use for: graph BFS, graph DFS, cycle detection, connected components

DYNAMIC PROGRAMMING:
  dp_array — 1D DP table filling with dependency arrows
    params: {"algorithm": "fibonacci"|"climbing_stairs"|"house_robber",
             "n": int}
    use for: Fibonacci, climbing stairs, house robber, 1D DP pattern

STACKS & QUEUES:
  stack_queue — animated push/pop on stack or enqueue/dequeue on queue
    params: {"operations": ["push X", "pop", ...], "structure": "stack"|"queue"}
    use for: stack/queue operations, valid parentheses, LIFO/FIFO concepts

Pattern routing (tiebreakers):
- palindrome / two-sum-on-sorted / container-water / reverse-array → two_pointers_opposite
- remove duplicates / move zeros → two_pointers_same_dir
- longest substring without repeating / at-most-k-distinct → sliding_window_variable
- binary search for an index in sorted array → binary_search_index
- "minimum X such that …" / "maximum X such that …" / koko bananas / capacity-to-ship → binary_search_answer
- next greater element / daily temperatures → monotonic_stack
- two sum (unsorted) / frequency / anagram → hashmap_iteration
- range sum / subarray sum / cumulative anything → prefix_sum
- max subarray sum / largest contiguous sum → kadanes
- merge intervals / overlapping intervals / meeting rooms → interval_merging
- subsets / permutations / combinations / decision-tree → backtracking_subsets
- LRU cache / design-cache → lru_cache
- shortest path on grid / flood fill / number of islands / matrix BFS → grid_traversal
- priority queue / k-largest / k-smallest / heap-sort / top-K → heap_ops
- LCS / edit distance / unique paths / 2D DP → dp_2d
- trie / prefix tree / autocomplete / word dictionary → trie_ops
- connected components / disjoint set / union-find → union_find
- shortest path on weighted graph / network delay → dijkstra
- range query / segment tree / online range → segment_tree
- linked list cycle / find duplicate / cycle detection → floyd_cycle
- trapping rain water / water between bars → trapping_rain_water
- jump game / gas station / greedy reach → greedy_interval
- single number XOR / count bits / bit tricks → bit_manipulation
- course schedule / topological order / DAG → topological_sort
- rotate matrix 90° / spiral matrix → matrix_rotation
- merge sort / divide and conquer recursion → recursion_tree_dc

Planning rules:
- Use small realistic data (arrays 5-8 elements, trees 7-15 nodes, graphs 5-7 nodes)
- 1 step  : "show me X" or "visualize X"
- 2 steps : "how does X work" — show the data structure, then the algorithm
- 3 steps : "explain why X" or "compare X and Y"
- Caption : one sentence describing what the student should observe in this step
- Arrays/strings: use short examples with 5-7 elements. Prefer 'racecar' over full problem input strings.
- Never copy the full example input from a problem statement into the array param.
- Arrays for binary search MUST be sorted
- IMPORTANT: Use EXACT tool names — never abbreviate. "graph_traversal" not "graph", "tree_traversal" not "tree", "stack_queue" not "stack", "linked_list" not "list", "two_pointers_opposite" not "two_pointers", "sliding_window_variable" not "sliding_window", "dp_array" not "dp"
- Respond with ONLY valid JSON — no markdown fences

{"concept": "brief concept name", "level": "beginner|intermediate|advanced", "steps": [
  {"tool": "<scene_key>", "params": {<params>}, "caption": "<one sentence>"},
  ...
]}"""

_VALID_DSA_TOOLS = {
    # legacy
    "array_pointer", "sliding_window", "linked_list",
    "tree_traversal", "graph_traversal", "dp_array", "stack_queue",
    # pattern-specific (phase 1)
    "two_pointers_opposite", "two_pointers_same_dir", "sliding_window_variable",
    "binary_search_index", "binary_search_answer", "monotonic_stack",
    "hashmap_iteration", "prefix_sum",
    # extended pattern scenes (phase 2)
    "kadanes", "interval_merging", "backtracking_subsets", "lru_cache",
    "grid_traversal", "heap_ops", "dp_2d", "trie_ops",
    "union_find", "dijkstra", "segment_tree",
    # phase 7 — visual depth + missing patterns
    "floyd_cycle", "trapping_rain_water", "greedy_interval",
    "bit_manipulation", "topological_sort", "matrix_rotation",
    "recursion_tree_dc",
}


def _build_llm() -> ChatOpenAI:
    # Priority: gpt-oss-120b (primary, smartest pattern routing) → Groq llama → generic OpenRouter
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


def plan_dsa(question: str, max_retries: int = 3) -> LessonPlan:
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
            # Strip reasoning-model artifacts (gpt-oss harmony channels, generic <thinking> tags)
            raw = re.sub(r"<\|channel\|>analysis<\|message\|>.*?(?=<\|channel\|>final<\|message\|>|$)",
                         "", raw, flags=re.DOTALL)
            raw = re.sub(r"<\|channel\|>final<\|message\|>", "", raw)
            raw = re.sub(r"<\|end\|>", "", raw)
            raw = re.sub(r"<thinking>.*?</thinking>", "", raw, flags=re.DOTALL)
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            raw = raw.strip()
            # Strip trailing commas before } or ] — the model frequently emits
            # them (e.g. "..., }" or "..., ]") which strict JSON rejects.
            raw = re.sub(r",(\s*[}\]])", r"\1", raw)
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                # Fall back to extracting the first balanced JSON object if
                # the model wrapped the payload in prose.
                start = raw.find("{")
                end   = raw.rfind("}")
                if start == -1 or end == -1 or end <= start:
                    raise
                data = json.loads(raw[start:end + 1])
            break
        except Exception as e:
            last_error = e
            if attempt == max_retries:
                raise ValueError(f"DSA planner failed after {max_retries} attempts: {last_error}") from last_error
            continue

    steps = []
    for s in data.get("steps", []):
        tool = s.get("tool", "")
        if tool not in _VALID_DSA_TOOLS:
            raise ValueError(f"Unknown DSA tool from planner: {tool!r}")
        steps.append(StepPlan(
            tool=tool,
            params=s.get("params", {}),
            caption=s.get("caption", ""),
        ))

    if not steps:
        raise ValueError("DSA planner returned no steps")

    return LessonPlan(
        concept=data.get("concept", ""),
        level=data.get("level", "beginner"),
        steps=steps,
    )
