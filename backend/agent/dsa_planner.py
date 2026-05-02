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

ARRAYS:
  array_pointer — two-pointer or binary search with animated pointer arrows
    params: {"array": [int, ...], "algorithm": "binary_search"|"two_pointers"|"palindrome",
             "target": int|null}
    use for: binary search, two sum, three sum, palindrome check, container water
    note: for binary_search the array MUST be sorted ascending

  sliding_window — window sliding over array tracking max/min/unique elements
    params: {"array": [int, ...], "algorithm": "max_subarray_fixed"|"longest_unique_substring",
             "k": int|null}
    use for: sliding window pattern, max subarray of size k, longest unique substring

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

Planning rules:
- Use small realistic data (arrays 5-8 elements, trees 7-15 nodes, graphs 5-7 nodes)
- 1 step  : "show me X" or "visualize X"
- 2 steps : "how does X work" — show the data structure, then the algorithm
- 3 steps : "explain why X" or "compare X and Y"
- Caption : one sentence describing what the student should observe in this step
- Arrays for binary search MUST be sorted
- Respond with ONLY valid JSON — no markdown fences

{"concept": "brief concept name", "level": "beginner|intermediate|advanced", "steps": [
  {"tool": "<scene_key>", "params": {<params>}, "caption": "<one sentence>"},
  ...
]}"""

_VALID_DSA_TOOLS = {
    "array_pointer", "sliding_window", "linked_list",
    "tree_traversal", "graph_traversal", "dp_array", "stack_queue",
}


def _build_llm() -> ChatOpenAI:
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
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            raw = raw.strip()
            data = json.loads(raw)
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
