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


# ── POST /api/parse-leetcode ─────────────────────────────────────────────────

def test_parse_leetcode_missing_raw_text_returns_400(client):
    res = client.post("/api/parse-leetcode", json={})
    assert res.status_code == 400
    assert "rawText" in res.get_json()["error"]


def test_parse_leetcode_blank_raw_text_returns_400(client):
    res = client.post("/api/parse-leetcode", json={"rawText": "   "})
    assert res.status_code == 400


def test_parse_leetcode_happy_path(client, mocker):
    from agent.leetcode_parser import ParsedLeetCode
    mock_result = ParsedLeetCode(
        title="Two Sum",
        scene="hashmap_iteration",
        params={"array": [2, 7, 11, 15], "algorithm": "two_sum_hashmap", "target": 9, "caption": ""},
        explanation="Walk the array, look up complement.",
        why_this_pattern="O(1) lookup beats O(n) brute scan.",
    )
    mocker.patch("app.parse_leetcode_problem", return_value=mock_result)

    res = client.post("/api/parse-leetcode",
                      json={"rawText": "Two Sum: nums=[2,7,11,15], target=9"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["scene"] == "hashmap_iteration"
    assert data["params"]["array"] == [2, 7, 11, 15]
    assert data["params"]["target"] == 9
    assert data["title"] == "Two Sum"
    assert data["explanation"]
    assert data["why_this_pattern"]


def test_parse_leetcode_value_error_returns_422(client, mocker):
    mocker.patch("app.parse_leetcode_problem",
                 side_effect=ValueError("unknown scene from model: 'banana'"))
    res = client.post("/api/parse-leetcode", json={"rawText": "anything"})
    assert res.status_code == 422
    assert "could not parse" in res.get_json()["error"]


def test_parse_leetcode_unexpected_error_returns_500(client, mocker):
    mocker.patch("app.parse_leetcode_problem", side_effect=RuntimeError("gemini quota"))
    res = client.post("/api/parse-leetcode", json={"rawText": "anything"})
    assert res.status_code == 500
