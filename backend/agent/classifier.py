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
    # gpt-oss is a reasoning model so we allow more tokens; thinking is stripped in classify_domain.
    base_or = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    if os.environ.get("OPENROUTER_GPT_OSS_120_KEY"):
        return ChatOpenAI(
            base_url=base_or,
            api_key=os.environ["OPENROUTER_GPT_OSS_120_KEY"],
            model=os.environ.get("OPENROUTER_GPT_OSS_120_MODEL", "openai/gpt-oss-120b"),
            temperature=0,
            max_tokens=512,
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


def classify_domain(question: str) -> str:
    """Returns 'math' or 'dsa'. Defaults to 'math' on any failure."""
    try:
        llm = _build_classifier_llm()
        response = llm.invoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=question),
        ])
        raw = response.content
        # Strip reasoning artifacts (gpt-oss harmony channels, generic <thinking>)
        raw = re.sub(r"<\|channel\|>analysis<\|message\|>.*?(?=<\|channel\|>final<\|message\|>|$)",
                     "", raw, flags=re.DOTALL)
        raw = re.sub(r"<\|channel\|>final<\|message\|>", "", raw)
        raw = re.sub(r"<\|end\|>", "", raw)
        raw = re.sub(r"<thinking>.*?</thinking>", "", raw, flags=re.DOTALL)
        raw = raw.strip().lower()
        raw = re.sub(r"[^a-z]", "", raw)
        if "dsa" in raw or "algo" in raw or "data" in raw:
            return "dsa"
        return "math"
    except Exception:
        return "math"
