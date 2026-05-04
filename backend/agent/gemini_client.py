"""
Thin wrapper around the google-genai SDK with a two-model fallback chain.

Primary:  gemini-flash-latest  (alias always points to newest stable Flash)
Fallback: gemini-2.5-flash     (stable; used when primary returns 429/503/quota)

Do NOT use gemini-2.0-flash — it shuts down 2026-06-01.
"""
import logging
import os

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

_PRIMARY  = "gemini-flash-latest"
_FALLBACK = "gemini-2.5-flash"


def _is_retryable(exc: Exception) -> bool:
    for attr in ("code", "status_code"):
        if getattr(exc, attr, None) in (429, 503):
            return True
    msg = str(exc).lower()
    return any(kw in msg for kw in ("429", "503", "quota", "rate limit", "resource exhausted"))


def call_gemini(contents, response_schema=None):
    """
    Call Gemini with automatic fallback on quota/rate errors.

    contents        – anything accepted by the google-genai SDK: a string,
                      a list of strings/Parts, etc.
    response_schema – optional JSON Schema dict; when provided Gemini is asked
                      to return strict JSON matching that schema.

    Returns the raw GenerateContentResponse. Use .text to get the string.
    Raises on both primary and fallback failure.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    client = genai.Client(api_key=api_key)

    config = None
    if response_schema is not None:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
        )

    def _generate(model: str):
        kwargs = {"model": model, "contents": contents}
        if config is not None:
            kwargs["config"] = config
        return client.models.generate_content(**kwargs)

    try:
        response = _generate(_PRIMARY)
        logger.info("Gemini: primary model succeeded (%s)", _PRIMARY)
        return response
    except Exception as exc:
        if not _is_retryable(exc):
            raise
        logger.warning(
            "Gemini: primary %s failed (%s) — retrying with fallback %s",
            _PRIMARY, exc, _FALLBACK,
        )

    response = _generate(_FALLBACK)
    logger.info("Gemini: fallback model succeeded (%s)", _FALLBACK)
    return response
