"""Tests for the render trace module (agent/trace.py)."""
import json
import os
import threading
import time

import pytest

from agent.trace import (
    LLMCall,
    StageTiming,
    new_trace,
    get_trace,
    load_trace,
    set_current,
    get_current,
    use_trace,
)


def test_new_trace_creates_registry_entry():
    trace = new_trace("test-new-001")
    assert get_trace("test-new-001") is trace


def test_trace_add_call_persists_to_disk(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.trace._TRACES_DIR", str(tmp_path))
    trace = new_trace("test-disk-002")
    trace.add_call(LLMCall(
        label="narrative_plan", model="m",
        elapsed_ms=42, prompt_chars=100, response_chars=200,
    ))
    on_disk = json.load(open(tmp_path / "test-disk-002.json"))
    assert on_disk["total_calls"] == 1
    assert on_disk["calls"][0]["label"] == "narrative_plan"
    assert on_disk["calls"][0]["elapsed_ms"] == 42


def test_trace_add_stage_persists_to_disk(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.trace._TRACES_DIR", str(tmp_path))
    trace = new_trace("test-stage-003")
    trace.add_stage("planning_narrative", 1500)
    trace.add_stage("building_scenes", 4200)
    on_disk = json.load(open(tmp_path / "test-stage-003.json"))
    assert len(on_disk["stages"]) == 2
    assert on_disk["stages"][1]["elapsed_ms"] == 4200


def test_trace_finalize_sets_finished_at(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.trace._TRACES_DIR", str(tmp_path))
    trace = new_trace("test-final-004")
    assert trace.finished_at is None
    trace.finalize()
    assert trace.finished_at is not None
    on_disk = json.load(open(tmp_path / "test-final-004.json"))
    assert on_disk["finished_at"] is not None


def test_load_trace_returns_none_for_missing_job(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.trace._TRACES_DIR", str(tmp_path))
    assert load_trace("does-not-exist") is None


def test_load_trace_reads_from_disk(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.trace._TRACES_DIR", str(tmp_path))
    trace = new_trace("test-load-005")
    trace.note("hello")
    trace.finalize()
    loaded = load_trace("test-load-005")
    assert loaded is not None
    assert loaded["notes"] == ["hello"]


def test_use_trace_context_manager_sets_and_restores():
    """use_trace binds the trace for the duration, restores prior state on exit."""
    set_current(None)
    assert get_current() is None
    t = new_trace("test-ctx-006")
    with use_trace(t):
        assert get_current() is t
    assert get_current() is None


def test_call_model_records_to_active_trace(mocker, tmp_path, monkeypatch):
    """When a trace is active, call_model records an LLMCall after invocation."""
    monkeypatch.setattr("agent.trace._TRACES_DIR", str(tmp_path))
    from agent.llm_client import call_model

    # Stub the LLM so no real network call happens
    class FakeLLM:
        model_name = "test-fake-model"
        def invoke(self, messages):
            class R:
                content = "result"
                response_metadata = {"token_usage": {"prompt_tokens": 10, "completion_tokens": 5}}
            return R()
    mocker.patch("agent.llm_client.build_llm", return_value=FakeLLM())

    trace = new_trace("test-record-007")
    with use_trace(trace):
        result = call_model("system prompt", "user prompt", label="test_call")

    assert result == "result"
    assert len(trace.calls) == 1
    c = trace.calls[0]
    assert c.label == "test_call"
    assert c.model == "test-fake-model"
    assert c.response_chars == len("result")
    assert c.prompt_tokens == 10
    assert c.completion_tokens == 5


def test_call_model_without_trace_does_not_record(mocker):
    """When no trace is active, call_model still works — just records nothing."""
    from agent.llm_client import call_model
    class FakeLLM:
        model_name = "x"
        def invoke(self, messages):
            class R:
                content = "fine"
                response_metadata = {}
            return R()
    mocker.patch("agent.llm_client.build_llm", return_value=FakeLLM())
    set_current(None)
    assert call_model("s", "u") == "fine"   # does not raise
