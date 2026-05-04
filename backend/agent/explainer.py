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

Given a topic and a student problem, return a concise step-by-step breakdown as
a JSON array of objects. Each object must have exactly two keys:
  "label" – short title (1-4 words)
  "body"  – one or two sentence explanation

Return 3-5 sections. Return ONLY the JSON array, no extra text or markdown fences."""


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


def explain_problem(problem: str, topic_name: str, topic_description: str) -> list[dict]:
    """Returns [{label, body}, ...] breakdown sections for the given topic/problem."""
    try:
        llm = _build_llm()
        user_msg = (
            f"Topic: {topic_name}\n"
            f"Description: {topic_description}\n"
            f"Problem: {problem or '(general explanation)'}"
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
            return [
                {"label": str(s.get("label", "")), "body": str(s.get("body", ""))}
                for s in sections
                if s.get("label") and s.get("body")
            ]
    except Exception:
        pass
    return [
        {"label": "Method", "body": f"{topic_name} — see animation for the visual intuition."},
        {"label": "Key idea", "body": topic_description},
    ]
