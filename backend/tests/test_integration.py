"""
Full pipeline integration tests.
POST /ask → render job → poll /status → video file exists on disk.

Run with: pytest backend/tests/test_integration.py -v -m integration
These take 30–90s each (real LLM call + Manim render).
"""
import time
from pathlib import Path

import pytest

from renderer.worker import _MEDIA_DIR


def _poll(client, job_id: str, timeout: int = 90) -> dict:
    for _ in range(timeout):
        data = client.get(f"/status/{job_id}").get_json()
        if data["status"] in ("done", "error"):
            return data
        time.sleep(1)
    pytest.fail(f"Job {job_id} did not finish within {timeout}s")


@pytest.mark.integration
def test_pipeline_function_plot(client):
    res = client.post("/ask", json={"question": "plot the function x squared"})
    assert res.status_code == 202
    data = res.get_json()
    assert "job_id" in data
    assert data["scene"] == "function_plot"

    result = _poll(client, data["job_id"])
    assert result["status"] == "done", f"Render error: {result.get('error')}"
    assert result["url"].startswith("/media/")
    assert (Path(_MEDIA_DIR) / result["url"].removeprefix("/media/")).exists()


@pytest.mark.integration
def test_pipeline_limit(client):
    res = client.post("/ask", json={
        "question": "show me the limit of sin(x) over x as x approaches 0"
    })
    assert res.status_code == 202
    result = _poll(client, res.get_json()["job_id"])
    assert result["status"] == "done", f"Render error: {result.get('error')}"
    assert (Path(_MEDIA_DIR) / result["url"].removeprefix("/media/")).exists()


@pytest.mark.integration
def test_pipeline_tangent_line(client):
    res = client.post("/ask", json={
        "question": "show the derivative of x cubed at x equals 2 as a tangent line"
    })
    assert res.status_code == 202
    result = _poll(client, res.get_json()["job_id"])
    assert result["status"] == "done", f"Render error: {result.get('error')}"
    assert (Path(_MEDIA_DIR) / result["url"].removeprefix("/media/")).exists()


@pytest.mark.integration
def test_pipeline_riemann_sum(client):
    res = client.post("/ask", json={
        "question": "visualize the area under x squared from 0 to 3 using left Riemann sums"
    })
    assert res.status_code == 202
    result = _poll(client, res.get_json()["job_id"])
    assert result["status"] == "done", f"Render error: {result.get('error')}"
    assert (Path(_MEDIA_DIR) / result["url"].removeprefix("/media/")).exists()


@pytest.mark.integration
def test_pipeline_critical_points(client):
    res = client.post("/ask", json={
        "question": "find the local maxima and minima of x cubed minus 3x"
    })
    assert res.status_code == 202
    result = _poll(client, res.get_json()["job_id"])
    assert result["status"] == "done", f"Render error: {result.get('error')}"
    assert (Path(_MEDIA_DIR) / result["url"].removeprefix("/media/")).exists()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_ask_empty_question_returns_400(client):
    res = client.post("/ask", json={"question": "   "})
    assert res.status_code == 400


def test_status_nonexistent_job_returns_404(client):
    res = client.get("/status/definitely-not-a-real-job-id")
    assert res.status_code == 404


def test_render_unknown_scene_results_in_error_status(client):
    res = client.post("/render", json={"scene": "not_a_scene", "params": {}})
    assert res.status_code == 202
    job_id = res.get_json()["job_id"]
    # Worker sets error immediately for unknown scenes (no subprocess needed)
    time.sleep(0.5)
    result = client.get(f"/status/{job_id}").get_json()
    assert result["status"] == "error"
    assert "unknown scene type" in result["error"]


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

def test_cors_header_present(client):
    res = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert res.status_code == 200
    assert "Access-Control-Allow-Origin" in res.headers


def test_cors_preflight(client):
    res = client.options(
        "/ask",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert res.status_code in (200, 204)
    assert "Access-Control-Allow-Origin" in res.headers
