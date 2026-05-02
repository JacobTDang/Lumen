"""
Tests for the stitch + lesson pipeline.
Run with: pytest backend/tests/test_stitch.py -v -m integration
"""
import time
from pathlib import Path

import pytest

from renderer.worker import _MEDIA_DIR
from schemas.types import StepPlan


@pytest.mark.integration
def test_lesson_two_different_scenes(client):
    """Two different scene types → stitched into one video."""
    steps = [
        StepPlan(tool="function_plot",
                 params={"expression": "x**2", "domain": [-3, 3]},
                 caption="Start: graph of x squared"),
        StepPlan(tool="tangent_line",
                 params={"expression": "x**2", "x_point": 1.0, "domain": [-3, 3]},
                 caption="Derivative as tangent line at x = 1"),
    ]
    from renderer.worker import submit_lesson
    lesson_id = submit_lesson(steps)
    assert lesson_id

    # Poll
    for _ in range(120):
        data = client.get(f"/status/{lesson_id}").get_json()
        if data["status"] == "done":
            break
        if data["status"] == "error":
            pytest.fail(f"Lesson failed: {data['error']}")
        time.sleep(1)
    else:
        pytest.fail("Lesson timed out")

    assert data["url"].startswith("/media/")
    video = Path(_MEDIA_DIR) / data["url"].removeprefix("/media/")
    assert video.exists()
    assert video.stat().st_size > 10_000  # sanity: not an empty file


@pytest.mark.integration
def test_lesson_single_step_no_stitch(client):
    """Single-step lesson should skip FFmpeg and return a direct video URL."""
    steps = [
        StepPlan(tool="quadratic",
                 params={"expression": "x**2 - 4", "domain": [-4, 4]},
                 caption="Parabola with roots"),
    ]
    from renderer.worker import submit_lesson
    lesson_id = submit_lesson(steps)

    for _ in range(90):
        data = client.get(f"/status/{lesson_id}").get_json()
        if data["status"] == "done":
            break
        if data["status"] == "error":
            pytest.fail(f"Single-step lesson failed: {data['error']}")
        time.sleep(1)
    else:
        pytest.fail("Timed out")

    assert data["status"] == "done"
    video = Path(_MEDIA_DIR) / data["url"].removeprefix("/media/")
    assert video.exists()


@pytest.mark.integration
def test_full_pipeline_via_ask_endpoint(client):
    """POST /ask → planner → lesson render → stitched video."""
    res = client.post("/ask", json={
        "question": "show me the derivative of x squared"
    })
    assert res.status_code == 202
    body = res.get_json()
    assert "job_id" in body
    assert "concept" in body
    assert body["scene_count"] >= 1

    for _ in range(180):
        data = client.get(f"/status/{body['job_id']}").get_json()
        if data["status"] == "done":
            break
        if data["status"] == "error":
            pytest.fail(f"Pipeline failed: {data['error']}")
        time.sleep(1)
    else:
        pytest.fail("Full pipeline timed out")

    assert data["url"].startswith("/media/")
    video = Path(_MEDIA_DIR) / data["url"].removeprefix("/media/")
    assert video.exists()
