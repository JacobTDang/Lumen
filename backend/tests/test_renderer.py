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
