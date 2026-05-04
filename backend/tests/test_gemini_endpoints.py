"""
Tests for the Gemini-backed /api/* endpoints and the call_gemini fallback chain.

All tests mock the Gemini client — no real API calls are made.
The `client` fixture comes from conftest.py (Flask test client).
"""
import json
import os
from io import BytesIO

import pytest


# ── helpers ──────────────────────────────────────────────────────────────────

def _mock_response(mocker, text: str):
    """Return a Mock that looks like a GenerateContentResponse."""
    r = mocker.Mock()
    r.text = text
    return r


# ── GET /api/topics ──────────────────────────────────────────────────────────

def test_api_topics_returns_list(client):
    res = client.get("/api/topics")
    assert res.status_code == 200
    data = res.get_json()
    assert "topics" in data
    assert isinstance(data["topics"], list)
    assert len(data["topics"]) > 0


def test_api_topics_entry_shape(client):
    res = client.get("/api/topics")
    topic = res.get_json()["topics"][0]
    for key in ("id", "name", "category", "keywords", "description"):
        assert key in topic, f"missing key: {key}"
    assert isinstance(topic["keywords"], list)


# ── POST /api/ocr ─────────────────────────────────────────────────────────────

def test_ocr_success(client, mocker):
    mocker.patch("app.call_gemini", return_value=_mock_response(mocker, "Extracted text here."))
    data = {"file": (BytesIO(b"fake png bytes"), "test.png", "image/png")}
    res = client.post("/api/ocr", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    assert res.get_json()["text"] == "Extracted text here."


def test_ocr_pdf_accepted(client, mocker):
    mocker.patch("app.call_gemini", return_value=_mock_response(mocker, "PDF text."))
    data = {"file": (BytesIO(b"%PDF fake"), "doc.pdf", "application/pdf")}
    res = client.post("/api/ocr", data=data, content_type="multipart/form-data")
    assert res.status_code == 200


def test_ocr_no_file_returns_400(client):
    res = client.post("/api/ocr", data={}, content_type="multipart/form-data")
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_ocr_unsupported_type_returns_400(client):
    data = {"file": (BytesIO(b"data"), "file.exe", "application/octet-stream")}
    res = client.post("/api/ocr", data=data, content_type="multipart/form-data")
    assert res.status_code == 400


def test_ocr_gemini_error_returns_500(client, mocker):
    mocker.patch("app.call_gemini", side_effect=RuntimeError("Gemini down"))
    data = {"file": (BytesIO(b"img"), "img.jpg", "image/jpeg")}
    res = client.post("/api/ocr", data=data, content_type="multipart/form-data")
    assert res.status_code == 500
    body = res.get_json()
    assert "error" in body
    assert "detail" in body


# ── POST /api/format-note ─────────────────────────────────────────────────────

def test_format_note_success(client, mocker):
    payload = json.dumps({"title": "My Note", "html": "<p>Hello</p>"})
    mocker.patch("app.call_gemini", return_value=_mock_response(mocker, payload))
    res = client.post("/api/format-note", json={"rawText": "Hello world"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["title"] == "My Note"
    assert data["html"] == "<p>Hello</p>"


def test_format_note_missing_rawtext_returns_400(client):
    res = client.post("/api/format-note", json={})
    assert res.status_code == 400
    assert res.get_json()["error"] == "rawText is required"


def test_format_note_empty_rawtext_returns_400(client):
    res = client.post("/api/format-note", json={"rawText": "   "})
    assert res.status_code == 400


def test_format_note_gemini_error_returns_500(client, mocker):
    mocker.patch("app.call_gemini", side_effect=RuntimeError("quota exceeded"))
    res = client.post("/api/format-note", json={"rawText": "Some text"})
    assert res.status_code == 500
    assert "detail" in res.get_json()


# ── POST /api/parse-problem ───────────────────────────────────────────────────

def test_parse_problem_success_with_match(client, mocker):
    payload = json.dumps({"problem": "Find the volume.", "topicId": "shell-method"})
    mocker.patch("app.call_gemini", return_value=_mock_response(mocker, payload))
    body = {
        "rawText": "Find the volume of the solid revolved around y-axis.",
        "topics": [{"id": "shell-method", "name": "Cylindrical Shell Method",
                    "keywords": ["shell method"], "description": "Volume by shells."}],
    }
    res = client.post("/api/parse-problem", json=body)
    assert res.status_code == 200
    data = res.get_json()
    assert data["problem"] == "Find the volume."
    assert data["topicId"] == "shell-method"


def test_parse_problem_success_no_match(client, mocker):
    payload = json.dumps({"problem": "Random text.", "topicId": None})
    mocker.patch("app.call_gemini", return_value=_mock_response(mocker, payload))
    res = client.post("/api/parse-problem", json={"rawText": "Random text.", "topics": []})
    assert res.status_code == 200
    assert res.get_json()["topicId"] is None


def test_parse_problem_missing_rawtext_returns_400(client):
    res = client.post("/api/parse-problem", json={"topics": []})
    assert res.status_code == 400


def test_parse_problem_gemini_error_returns_500(client, mocker):
    mocker.patch("app.call_gemini", side_effect=RuntimeError("rate limit"))
    res = client.post("/api/parse-problem", json={"rawText": "Some problem.", "topics": []})
    assert res.status_code == 500


# ── POST /api/breakdown ───────────────────────────────────────────────────────

def test_breakdown_success(client, mocker):
    payload = json.dumps({
        "sections": [
            {"label": "Method", "body": "Use cylindrical shells."},
            {"label": "Setup", "body": "V = 2π ∫ x·f(x) dx."},
        ]
    })
    mocker.patch("app.call_gemini", return_value=_mock_response(mocker, payload))
    body = {
        "problem": "Volume of solid revolved around y-axis.",
        "topic": {"id": "shell-method", "name": "Cylindrical Shell Method",
                  "description": "Volume by shells."},
    }
    res = client.post("/api/breakdown", json=body)
    assert res.status_code == 200
    data = res.get_json()
    assert "sections" in data
    assert len(data["sections"]) == 2
    assert data["sections"][0]["label"] == "Method"


def test_breakdown_missing_topic_name_returns_400(client):
    res = client.post("/api/breakdown", json={"problem": "...", "topic": {}})
    assert res.status_code == 400
    assert "topic.name" in res.get_json()["error"]


def test_breakdown_no_body_returns_400(client):
    res = client.post("/api/breakdown", json={})
    assert res.status_code == 400


def test_breakdown_gemini_error_returns_500(client, mocker):
    mocker.patch("app.call_gemini", side_effect=RuntimeError("service unavailable"))
    body = {"problem": "x^2", "topic": {"id": "x", "name": "Power Rule", "description": "d/dx x^n"}}
    res = client.post("/api/breakdown", json=body)
    assert res.status_code == 500


# ── call_gemini fallback chain ────────────────────────────────────────────────

def test_fallback_triggers_on_429(mocker):
    """Primary raises a 429-like error; fallback model should be tried and succeed."""
    mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})

    primary_exc = Exception("429 RESOURCE_EXHAUSTED: quota exceeded")
    fallback_resp = mocker.Mock()
    fallback_resp.text = "fallback result"

    mock_client = mocker.Mock()
    mock_client.models.generate_content.side_effect = [primary_exc, fallback_resp]
    mocker.patch("agent.gemini_client.genai.Client", return_value=mock_client)

    from agent.gemini_client import call_gemini
    result = call_gemini("test prompt")

    assert result is fallback_resp
    assert mock_client.models.generate_content.call_count == 2

    calls = mock_client.models.generate_content.call_args_list
    assert calls[0].kwargs["model"] == "gemini-flash-latest"
    assert calls[1].kwargs["model"] == "gemini-2.5-flash"


def test_non_retryable_error_not_retried(mocker):
    """A non-retryable error (e.g. invalid API key) should raise immediately."""
    mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})

    hard_error = Exception("400 INVALID_ARGUMENT: bad request")
    mock_client = mocker.Mock()
    mock_client.models.generate_content.side_effect = hard_error
    mocker.patch("agent.gemini_client.genai.Client", return_value=mock_client)

    from agent.gemini_client import call_gemini
    with pytest.raises(Exception, match="400 INVALID_ARGUMENT"):
        call_gemini("test prompt")

    assert mock_client.models.generate_content.call_count == 1


def test_fallback_failure_raises(mocker):
    """If both primary and fallback fail, the fallback exception should propagate."""
    mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})

    exc = Exception("503 service unavailable")
    mock_client = mocker.Mock()
    mock_client.models.generate_content.side_effect = exc
    mocker.patch("agent.gemini_client.genai.Client", return_value=mock_client)

    from agent.gemini_client import call_gemini
    with pytest.raises(Exception):
        call_gemini("test prompt")

    assert mock_client.models.generate_content.call_count == 2


def test_missing_api_key_raises(mocker):
    mocker.patch.dict(os.environ, {}, clear=True)
    os.environ.pop("GEMINI_API_KEY", None)

    from agent.gemini_client import call_gemini
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        call_gemini("test")
