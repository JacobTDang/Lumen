"""
Problem explainer: generates step-by-step breakdown sections for a topic.

Uses an LLM to produce pedagogically useful explanations as a list of
{label, body} sections. Falls back to a minimal description if the LLM fails.
"""
import json
import os
import re

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

_SYSTEM_PROMPT = """You are a math and computer science tutor.

Given a topic and a student problem, return EXACTLY THREE breakdown sections as
a JSON array of objects, in this exact order and with these exact labels:

  1. {"label": "Formula", "body": "..."}
       The general formula, definition, or rule that applies. Use plain text
       symbols (^, /, *, =, sqrt, pi, etc.). One or two sentences.
  2. {"label": "Example", "body": "..."}
       A concrete worked example illustrating the formula in action. If a
       problem was provided, use that problem's specific values; otherwise
       invent a simple, representative case. One or two sentences setting up
       the example.
  3. {"label": "Answer", "body": "..."}
       The worked answer to the example: substitute values into the formula,
       simplify step by step, and state the final result. Two to four sentences.

Each "body" should be 1-4 sentences. Use plain prose; no markdown, no LaTeX.
Return ONLY the JSON array, no extra text, no markdown fences, no commentary."""


def _build_llm() -> ChatOpenAI:
    base_or = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    if os.environ.get("GROQ_API_KEY"):
        return ChatOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ["GROQ_API_KEY"],
            model=os.environ.get("GROQ_PLANNER_MODEL", "llama-3.3-70b-versatile"),
            temperature=0.3,
            max_tokens=1024,
        )
    return ChatOpenAI(
        base_url=base_or,
        api_key=os.environ["OPENROUTER_API_KEY"],
        model=os.environ.get("OPENROUTER_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"),
        temperature=0.3,
        max_tokens=1024,
    )


_REQUIRED_LABELS = ("Formula", "Example", "Answer")


def _coerce_to_required_shape(sections: list[dict]) -> list[dict] | None:
    """Reshape arbitrary LLM output into the required Formula/Example/Answer
    triple. We try a case-insensitive label lookup first; if any of the three
    labels are missing, return None so the caller can use the fallback."""
    by_label: dict[str, str] = {}
    for s in sections:
        label = str(s.get("label", "")).strip()
        body  = str(s.get("body", "")).strip()
        if not label or not body:
            continue
        # Normalize common synonyms the LLM might emit despite instructions
        norm = label.lower().rstrip(":").strip()
        if norm in ("formula", "general formula", "rule", "definition", "method"):
            by_label.setdefault("Formula", body)
        elif norm in ("example", "worked example", "problem", "question",
                      "scenario", "illustration", "setup"):
            by_label.setdefault("Example", body)
        elif norm in ("answer", "solution", "result", "worked answer", "computation"):
            by_label.setdefault("Answer", body)

    if all(label in by_label for label in _REQUIRED_LABELS):
        return [{"label": label, "body": by_label[label]} for label in _REQUIRED_LABELS]
    return None


def explain_problem(problem: str, topic_name: str, topic_description: str) -> list[dict]:
    """Returns exactly three sections — Formula, Question, Answer — for the
    given topic/problem. Falls back to topic-only placeholders if the LLM is
    unreachable or returns malformed output."""
    try:
        llm = _build_llm()
        user_msg = (
            f"Topic: {topic_name}\n"
            f"Description: {topic_description}\n"
            f"Problem: {problem or '(general explanation — invent a representative example)'}"
        )
        response = llm.invoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=user_msg),
        ])
        raw = response.content.strip()
        raw = re.sub(r"```(?:json)?\s*", "", raw)
        raw = re.sub(r"```", "", raw).strip()
        sections = json.loads(raw)
        if isinstance(sections, list) and sections:
            coerced = _coerce_to_required_shape(sections)
            if coerced:
                return coerced
    except Exception:
        pass

    return [
        {"label": "Formula", "body": f"See the animation for the {topic_name} formula and visual intuition."},
        {"label": "Example", "body": problem.strip() or f"A typical {topic_name} problem."},
        {"label": "Answer",  "body": topic_description},
    ]
