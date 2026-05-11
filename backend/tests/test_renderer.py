import threading
from unittest.mock import MagicMock, patch

from renderer.worker import get_job, submit_render


def test_submit_render_returns_string_id():
    with patch("renderer.worker._run_render"):
        with patch("threading.Thread") as mock_thread:
            mock_thread.return_value = MagicMock()
            job_id = submit_render("bubble_sort", {"array": [3, 1, 2]})
    assert isinstance(job_id, str)
    assert len(job_id) > 0


def test_initial_status_is_pending():
    with patch("threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        job_id = submit_render("bubble_sort", {"array": [3, 1, 2]})
    job = get_job(job_id)
    assert job is not None
    assert job["status"] == "pending"


def test_unknown_job_returns_none():
    assert get_job("does-not-exist") is None


def test_unknown_scene_type_sets_error(tmp_path, monkeypatch):
    monkeypatch.setattr("renderer.worker._TEMP_DIR", str(tmp_path))
    monkeypatch.setattr("renderer.worker._MEDIA_DIR", str(tmp_path))

    # Run _run_render directly (synchronously) with an unknown scene type
    from renderer.worker import _run_render, _jobs
    job_id = "test-unknown-scene"
    _jobs[job_id] = {"status": "pending", "url": None, "error": None}
    _run_render(job_id, "not_a_real_scene", {})

    assert _jobs[job_id]["status"] == "error"
    assert "unknown scene type" in _jobs[job_id]["error"]


# ─────────────────────────────────────────────────────────────────────────────
# Phase A — stage tracking
# ─────────────────────────────────────────────────────────────────────────────

def test_submit_render_initializes_with_queued_stage():
    with patch("threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        job_id = submit_render("bubble_sort", {"array": [3, 1, 2]})
    job = get_job(job_id)
    assert job is not None
    assert job.get("stage") == "queued"


def test_submit_lesson_initializes_with_queued_stage():
    from renderer.worker import submit_lesson
    with patch("threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        lesson_id = submit_lesson([])  # empty steps OK for init check
    job = get_job(lesson_id)
    assert job is not None
    assert job.get("stage") == "queued"


def test_get_job_includes_stage_field():
    with patch("threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        job_id = submit_render("bubble_sort", {"array": [1]})
    job = get_job(job_id)
    assert "stage" in job


def test_unknown_scene_sets_stage_error(tmp_path, monkeypatch):
    monkeypatch.setattr("renderer.worker._TEMP_DIR", str(tmp_path))
    monkeypatch.setattr("renderer.worker._MEDIA_DIR", str(tmp_path))
    from renderer.worker import _run_render, _jobs
    job_id = "test-unknown-stage"
    _jobs[job_id] = {"status": "pending", "url": None, "error": None,
                     "progress": 0.0, "stage": "queued"}
    _run_render(job_id, "not_a_real_scene", {})
    assert _jobs[job_id]["stage"] == "error"


def test_run_lesson_sets_done_stage_on_cache_hit(tmp_path, monkeypatch):
    """When the cache returns a URL, the lesson immediately finalizes with stage=done."""
    monkeypatch.setattr("renderer.worker._MEDIA_DIR", str(tmp_path))
    monkeypatch.setattr("renderer.worker._LESSONS_DIR", str(tmp_path))

    from renderer.worker import _run_lesson, _jobs
    monkeypatch.setattr("renderer.worker._cache_lookup", lambda key: "/media/lessons/cached.mp4")

    lesson_id = "test-cache-hit"
    _jobs[lesson_id] = {"status": "pending", "url": None, "error": None,
                        "progress": 0.0, "stage": "queued"}
    _run_lesson(lesson_id, [])
    assert _jobs[lesson_id]["stage"] == "done"
    assert _jobs[lesson_id]["status"] == "done"


def test_aggregate_progress_sets_rendering_x_of_n(tmp_path, monkeypatch):
    """The progress aggregator sets stage='rendering_X_of_N' based on completed steps."""
    from renderer.worker import _aggregate_progress, _jobs

    lesson_id = "test-agg-progress"
    step_ids = ["s1", "s2", "s3"]
    _jobs[lesson_id] = {"status": "pending", "url": None, "error": None,
                        "progress": 0.0, "stage": "queued"}
    # Two steps done, third in-progress
    _jobs["s1"] = {"status": "done", "progress": 1.0}
    _jobs["s2"] = {"status": "done", "progress": 1.0}
    _jobs["s3"] = {"status": "pending", "progress": 0.3}

    stop = threading.Event()
    t = threading.Thread(target=_aggregate_progress, args=(lesson_id, step_ids, stop), daemon=True)
    t.start()
    # Give the ticker (250ms loop) a moment to update
    import time
    time.sleep(0.4)
    stop.set()
    t.join(timeout=1.0)

    assert _jobs[lesson_id]["stage"] == "rendering_3_of_3"
