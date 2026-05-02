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
    if os.environ.get("GROQ_API_KEY"):
        return ChatOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ["GROQ_API_KEY"],
            model=os.environ.get("GROQ_CLASSIFIER_MODEL", "llama-3.1-8b-instant"),
            temperature=0,
            max_tokens=5,
        )
    return ChatOpenAI(
        base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        api_key=os.environ["OPENROUTER_API_KEY"],
        model=os.environ.get("OPENROUTER_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"),
        temperature=0,
        max_tokens=5,
    )


def classify_domain(question: str) -> str:
    """Returns 'math' or 'dsa'. Defaults to 'math' on any failure."""
    try:
        llm = _build_classifier_llm()
        response = llm.invoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=question),
        ])
        raw = response.content.strip().lower()
        raw = re.sub(r"[^a-z]", "", raw)
        if "dsa" in raw or "algo" in raw or "data" in raw:
            return "dsa"
        return "math"
    except Exception:
        return "math"
