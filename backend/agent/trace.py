"""
Render trace — accumulates per-job timing and (when available) LLM token usage.

The trace is persisted under media/traces/<job_id>.json. Exposed via the
/api/trace/<job_id> endpoint so the frontend can show a "Behind the scenes"
panel breaking down where time was spent.

Tokens: we don't always have them — LangChain's invoke() returns content only
unless we use additional metadata. For now we record what we can (call count,
model name, elapsed_ms per call) and leave token fields populated only when
the LLM response exposes them.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any


_TRACES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "media", "traces",
)


@dataclass
class LLMCall:
    label: str            # e.g. "narrative_plan", "build_scene[0]", "critique[1]"
    model: str            # what model_name was active
    elapsed_ms: int
    prompt_chars: int     # rough cost proxy when tokens aren't exposed
    response_chars: int
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    error: str | None = None


@dataclass
class StageTiming:
    stage: str
    elapsed_ms: int


@dataclass
class RenderTrace:
    job_id: str
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    calls: list[LLMCall] = field(default_factory=list)
    stages: list[StageTiming] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    # Per-trace lock. The parallel build_scene workers all call add_call()
    # concurrently — without this lock, `save()` iterating `self.calls` while
    # another thread appends raises RuntimeError: list changed size.
    # `repr=False, compare=False` keeps the dataclass machinery from trying
    # to inspect the lock object (which would deadlock on repr).
    _lock: threading.Lock = field(
        default_factory=threading.Lock, repr=False, compare=False,
    )

    def add_call(self, call: LLMCall) -> None:
        with self._lock:
            self.calls.append(call)
        self.save()

    def add_stage(self, stage: str, elapsed_ms: int) -> None:
        with self._lock:
            self.stages.append(StageTiming(stage=stage, elapsed_ms=elapsed_ms))
        self.save()

    def note(self, text: str) -> None:
        with self._lock:
            self.notes.append(text)
        self.save()

    def finalize(self) -> None:
        with self._lock:
            self.finished_at = time.time()
        self.save()

    def save(self) -> None:
        # Hold the lock for the entire snapshot + write. Concurrent saves would
        # otherwise race on the tmp file — Windows fails os.replace with
        # PermissionError when a sibling thread still has the tmp open.
        # save() is fast (~ms) so the contention is acceptable.
        os.makedirs(_TRACES_DIR, exist_ok=True)
        path = os.path.join(_TRACES_DIR, f"{self.job_id}.json")
        tmp = path + ".tmp"
        with self._lock:
            payload = {
                "job_id": self.job_id,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "calls": [asdict(c) for c in self.calls],
                "stages": [asdict(s) for s in self.stages],
                "notes": list(self.notes),
                "total_calls": len(self.calls),
                "total_call_ms": sum(c.elapsed_ms for c in self.calls),
            }
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
            os.replace(tmp, path)

    @property
    def total_call_ms(self) -> int:
        with self._lock:
            return sum(c.elapsed_ms for c in self.calls)


# ─────────────────────────────────────────────────────────────────────────────
# Active-trace registry — thread-safe per-job lookup so any agent module can
# attribute its LLM calls without explicit plumbing.
# ─────────────────────────────────────────────────────────────────────────────

_TRACES: dict[str, RenderTrace] = {}
_LOCK = threading.Lock()
_TLS = threading.local()   # holds the "current" trace for the active thread


def new_trace(job_id: str) -> RenderTrace:
    trace = RenderTrace(job_id=job_id)
    with _LOCK:
        _TRACES[job_id] = trace
    return trace


def get_trace(job_id: str) -> RenderTrace | None:
    with _LOCK:
        return _TRACES.get(job_id)


def load_trace(job_id: str) -> dict | None:
    """Read a trace from disk (used by the /api/trace endpoint after the job ends)."""
    path = os.path.join(_TRACES_DIR, f"{job_id}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None


def set_current(trace: RenderTrace | None) -> None:
    """Bind a trace to the current thread so call_model can attribute to it."""
    _TLS.current = trace


def get_current() -> RenderTrace | None:
    return getattr(_TLS, "current", None)


# Convenience context manager: with use_trace(trace): ...
class use_trace:
    def __init__(self, trace: RenderTrace | None):
        self.trace = trace
        self.prev: RenderTrace | None = None

    def __enter__(self):
        self.prev = get_current()
        set_current(self.trace)
        return self.trace

    def __exit__(self, *exc):
        set_current(self.prev)
        return False
