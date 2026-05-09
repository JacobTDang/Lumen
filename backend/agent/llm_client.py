"""
Shared LLM client utilities for all agent modules.

Previously copied into 5+ files. Centralised here so model changes,
fallback order, and JSON-cleaning logic are maintained in one place.

Exports:
  build_llm()       → gpt-oss-120b → Groq llama → generic OpenRouter
  build_fast_llm()  → Groq-first, lower temperature (explainer)
  call_model(system, user)  → str
  clean_raw(raw)    → str
  extract_json(raw) → dict | list
"""
from __future__ import annotations

import json
import os
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


def build_llm() -> ChatOpenAI:
    """Primary reasoning stack: gpt-oss-120b → Groq llama → generic OpenRouter."""
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
        model=os.environ.get(
            "OPENROUTER_MODEL",
            "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        ),
        temperature=0,
    )


def build_fast_llm() -> ChatOpenAI:
    """Fast/cheap stack for low-stakes calls: Groq-first, higher temperature.
    Used by explainer.py where creativity > precision."""
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
        model=os.environ.get(
            "OPENROUTER_MODEL",
            "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        ),
        temperature=0.3,
        max_tokens=1024,
    )


def call_model(system: str, user: str, llm: ChatOpenAI | None = None) -> str:
    """Invoke the LLM. Tests mock this function to avoid real API calls."""
    if llm is None:
        llm = build_llm()
    response = llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=user),
    ])
    return response.content or ""


def clean_raw(raw: str) -> str:
    """Strip reasoning-model artifacts and markdown fences from raw output."""
    raw = re.sub(
        r"<\|channel\|>analysis<\|message\|>.*?(?=<\|channel\|>final<\|message\|>|$)",
        "", raw, flags=re.DOTALL,
    )
    raw = re.sub(r"<\|channel\|>final<\|message\|>", "", raw)
    raw = re.sub(r"<\|end\|>", "", raw)
    raw = re.sub(r"<thinking>.*?</thinking>", "", raw, flags=re.DOTALL)
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    raw = re.sub(r",(\s*[}\]])", r"\1", raw)   # trailing commas
    return raw.strip()


def extract_json(raw: str):
    """Parse JSON from a model response, with fallback to first {...} or [...] block."""
    cleaned = clean_raw(raw)
    if not cleaned:
        raise ValueError("model returned empty response")
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        for start_char, end_char in [('{', '}'), ('[', ']')]:
            s = cleaned.find(start_char)
            e = cleaned.rfind(end_char)
            if s != -1 and e > s:
                try:
                    return json.loads(cleaned[s:e + 1])
                except json.JSONDecodeError:
                    continue
        raise ValueError(f"could not parse JSON: {cleaned[:200]}")
