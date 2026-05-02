import pytest

def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


def test_render_missing_scene_returns_400(client):
    res = client.post("/render", json={"params": {"array": [1, 2, 3]}})
    assert res.status_code == 400


def test_render_returns_job_id(client, mocker):
    mocker.patch("app.submit_render", return_value="test-job-id")
    res = client.post("/render", json={"scene": "bubble_sort", "params": {"array": [3, 1, 2]}})
    assert res.status_code == 202
    assert res.get_json()["job_id"] == "test-job-id"


def test_status_unknown_job_returns_404(client):
    res = client.get("/status/nonexistent-job-id")
    assert res.status_code == 404


def test_status_known_job(client, mocker):
    mocker.patch(
        "app.get_job",
        return_value={"status": "done", "url": "/media/test.mp4", "error": None},
    )
    res = client.get("/status/some-job-id")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "done"
    assert data["url"] == "/media/test.mp4"
