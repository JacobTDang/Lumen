"""
Domain classifier: routes a student question to either "math" or "dsa".

Uses a fast, lightweight model (llama-3.1-8b-instant on Groq) for this
simple binary classification — no structured output needed, just one word.
"""
import os
import re

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

_SYSTEM_PROMPT = """You are a math and computer science tutor assistant.

Classify the student's question into exactly one of these two domains:
- "math"  : calculus, algebra, arithmetic, fractions, trigonometry, geometry,
            limits, derivatives, integrals, statistics, functions, equations,
            number lines, exponentials, logarithms, series, vectors, matrices
- "dsa"   : algorithms, data structures, arrays, linked lists, trees, graphs,
            sorting, searching, binary search, two pointers, sliding window,
            dynamic programming, recursion, stacks, queues, hash maps,
            BFS, DFS, LeetCode, NeetCode, coding interviews, Big O

Reply with ONLY one word: math or dsa"""


def _build_classifier_llm() -> ChatOpenAI:
    # Priority: gpt-oss-120b → Groq llama-3.1-8b-instant → generic OpenRouter
    # gpt-oss is a reasoning model — its reasoning tokens count against
    # max_tokens even when hidden by OpenRouter, so leave plenty of headroom
    # or the final "dsa"/"math" word gets truncated to "d" / "m".
    base_or = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    if os.environ.get("OPENROUTER_GPT_OSS_120_KEY"):
        return ChatOpenAI(
            base_url=base_or,
            api_key=os.environ["OPENROUTER_GPT_OSS_120_KEY"],
            model=os.environ.get("OPENROUTER_GPT_OSS_120_MODEL", "openai/gpt-oss-120b"),
            temperature=0,
            max_tokens=2048,
            extra_body={"reasoning": {"effort": "low"}},
        )
    if os.environ.get("GROQ_API_KEY"):
        return ChatOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ["GROQ_API_KEY"],
            model=os.environ.get("GROQ_CLASSIFIER_MODEL", "llama-3.1-8b-instant"),
            temperature=0,
            max_tokens=5,
        )
    return ChatOpenAI(
        base_url=base_or,
        api_key=os.environ["OPENROUTER_API_KEY"],
        model=os.environ.get("OPENROUTER_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"),
        temperature=0,
        max_tokens=5,
    )


_DSA_KEYWORDS = (
    "bfs", "dfs", "binary tree", "linked list", "hashmap", "hash map",
    "trie", "heap", "graph", "leetcode", "neetcode", "two pointer",
    "sliding window", "binary search", "dynamic programming", "dp ",
    "subset", "permutation", "backtrack", "kadane", "dijkstra",
    "union find", "union-find", "segment tree", "lru", "monotonic",
    "prefix sum", "interval", "edit distance", "longest common",
    "subsequence", "topological", "shortest path",
)


def _keyword_fallback(question: str) -> str:
    """Cheap heuristic when the LLM response is unparseable / truncated."""
    q = question.lower()
    return "dsa" if any(kw in q for kw in _DSA_KEYWORDS) else "math"


def classify_domain(question: str) -> str:
    """Returns 'math' or 'dsa'. Falls back to keyword scan if the LLM response
    is empty/truncated, then defaults to 'math' as a last resort.
    """
    try:
        llm = _build_classifier_llm()
        response = llm.invoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=question),
        ])
        raw = response.content
        raw = re.sub(r"<\|channel\|>analysis<\|message\|>.*?(?=<\|channel\|>final<\|message\|>|$)",
                     "", raw, flags=re.DOTALL)
        raw = re.sub(r"<\|channel\|>final<\|message\|>", "", raw)
        raw = re.sub(r"<\|end\|>", "", raw)
        raw = re.sub(r"<thinking>.*?</thinking>", "", raw, flags=re.DOTALL)
        cleaned = re.sub(r"[^a-z]", "", raw.strip().lower())
        if "dsa" in cleaned or "algo" in cleaned:
            return "dsa"
        if "math" in cleaned:
            return "math"
        # Truncated or unrecognized — fall back to keyword scan
        return _keyword_fallback(question)
    except Exception:
        return _keyword_fallback(question)
