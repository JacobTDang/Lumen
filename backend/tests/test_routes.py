import pytest

def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


def test_render_missing_scene_returns_400(client):
    res = client.post("/render", json={"params": {"array": [1, 2, 3]}})
    assert res.status_code == 400


def test_render_returns_job_id(client, mocker):
    # /render routes through submit_lesson (so single-scene renders share the
    # content-hash cache with /prerender). See app.py:323.
    mocker.patch("app.submit_lesson", return_value="test-job-id")
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


# ── POST /api/parse-problem-v2 ────────────────────────────────────────────────

def test_parse_v2_math_routes_to_math_parser(client, mocker):
    """Math text should route through parse_math, not parse_leetcode."""
    from agent.math_parser import ParsedMath
    mocker.patch("app.classify_domain", return_value="math")
    mock_result = ParsedMath(
        title="Definite Integral",
        scene="riemann_sum",
        params={"expression": "x**2", "domain": [0.0, 4.0], "n": 8, "method": "midpoint", "caption": ""},
        explanation="Approximate ∫x² dx with rectangles.",
        why_this_pattern="Riemann sum.",
        steps=["Step 1", "Step 2"],
    )
    mocker.patch("app.parse_math", return_value=mock_result)

    res = client.post("/api/parse-problem-v2",
                      json={"rawText": "Compute integral of x squared from 0 to 4"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["domain"] == "math"
    assert data["scene"] == "riemann_sum"
    assert data["steps"] == ["Step 1", "Step 2"]


def test_parse_v2_dsa_routes_to_leetcode_parser(client, mocker):
    """DSA text should route through parse_leetcode_problem."""
    from agent.leetcode_parser import ParsedLeetCode
    mocker.patch("app.classify_domain", return_value="dsa")
    mock_result = ParsedLeetCode(
        title="Two Sum",
        scene="hashmap_iteration",
        params={"array": [2, 7, 11, 15], "algorithm": "two_sum_hashmap", "target": 9, "caption": ""},
        explanation="Walk array, look up complement.",
        why_this_pattern="O(1) lookup.",
        pseudocode="seen = {}",
        step_lines={"match": 3},
    )
    mocker.patch("app.parse_leetcode_problem", return_value=mock_result)

    res = client.post("/api/parse-problem-v2",
                      json={"rawText": "Two Sum nums=[2,7,11,15] target=9"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["domain"] == "dsa"
    assert data["scene"] == "hashmap_iteration"
    assert data["pseudocode"] == "seen = {}"


def test_parse_v2_missing_raw_text_returns_400(client):
    res = client.post("/api/parse-problem-v2", json={})
    assert res.status_code == 400


def test_parse_v2_value_error_returns_422(client, mocker):
    mocker.patch("app.classify_domain", return_value="math")
    mocker.patch("app.parse_math", side_effect=ValueError("unknown math scene from model"))
    res = client.post("/api/parse-problem-v2", json={"rawText": "garbage"})
    assert res.status_code == 422


# ── POST /api/fetch-leetcode ──────────────────────────────────────────────────

def test_fetch_leetcode_invalid_url_returns_400(client):
    res = client.post("/api/fetch-leetcode", json={"url": "https://google.com"})
    assert res.status_code == 400


def test_fetch_leetcode_missing_url_returns_400(client):
    res = client.post("/api/fetch-leetcode", json={})
    assert res.status_code == 400


def test_fetch_leetcode_success(client, mocker):
    """Mock the requests.post call to LeetCode's GraphQL — verify the
    endpoint extracts title + plain-text content from their HTML."""
    mock_resp = mocker.Mock()
    mock_resp.json.return_value = {
        "data": {
            "question": {
                "title": "Two Sum",
                "content": "<p>Given an array of integers <code>nums</code>, return indices of the two numbers such that they add up to <code>target</code>.</p>",
                "sampleTestCase": "[2,7,11,15]\n9",
                "difficulty": "Easy",
            }
        }
    }
    mocker.patch("requests.post", return_value=mock_resp)

    res = client.post("/api/fetch-leetcode",
                      json={"url": "https://leetcode.com/problems/two-sum/"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["title"] == "Two Sum"
    assert "indices" in data["rawText"]
    assert data["sampleInput"] == "[2,7,11,15]\n9"
    assert data["difficulty"] == "Easy"


def test_fetch_leetcode_unknown_slug_returns_404(client, mocker):
    mock_resp = mocker.Mock()
    mock_resp.json.return_value = {"data": {"question": None}}
    mocker.patch("requests.post", return_value=mock_resp)
    res = client.post("/api/fetch-leetcode",
                      json={"url": "https://leetcode.com/problems/nonexistent-foo/"})
    assert res.status_code == 404


# ── POST /api/parse-followup ──────────────────────────────────────────────────

def test_parse_followup_missing_followup_returns_400(client):
    res = client.post("/api/parse-followup", json={"prior": {}})
    assert res.status_code == 400


def test_parse_followup_blank_followup_returns_400(client):
    res = client.post("/api/parse-followup", json={"prior": {}, "followUp": "   "})
    assert res.status_code == 400


def test_parse_followup_routes_to_math_with_prior_context(client, mocker):
    """A math follow-up routes through parse_math with prior context baked in."""
    from agent.math_parser import ParsedMath
    mocker.patch("app.classify_domain", return_value="math")
    mock_result = ParsedMath(
        title="Updated Riemann",
        scene="riemann_sum",
        params={"expression": "x**3", "domain": [0.0, 4.0], "n": 8, "method": "midpoint", "caption": ""},
        explanation="x", why_this_pattern="x", steps=["new step"],
    )
    parse_mock = mocker.patch("app.parse_math", return_value=mock_result)

    body = {
        "prior": {
            "title": "Riemann sum for x²",
            "scene": "riemann_sum",
            "params": {"expression": "x**2", "domain": [0, 4], "n": 8},
        },
        "followUp": "Now do it with x cubed instead",
    }
    res = client.post("/api/parse-followup", json=body)
    assert res.status_code == 200
    assert res.get_json()["scene"] == "riemann_sum"
    # The rich_text passed to parse_math should include the prior context
    rich_text = parse_mock.call_args[0][0]
    assert "Previous scene: riemann_sum" in rich_text
    assert "x cubed" in rich_text


def test_parse_followup_value_error_returns_422(client, mocker):
    mocker.patch("app.classify_domain", return_value="dsa")
    mocker.patch("app.parse_leetcode_problem",
                 side_effect=ValueError("unknown scene"))
    res = client.post("/api/parse-followup", json={"prior": {}, "followUp": "any"})
    assert res.status_code == 422


def test_parse_followup_works_without_prior(client, mocker):
    """If prior is empty/absent, the follow-up is parsed standalone."""
    from agent.leetcode_parser import ParsedLeetCode
    mocker.patch("app.classify_domain", return_value="dsa")
    mocker.patch("app.parse_leetcode_problem", return_value=ParsedLeetCode(
        title="Two Sum", scene="hashmap_iteration",
        params={"array": [2, 7], "algorithm": "two_sum_hashmap", "target": 9, "caption": ""},
        explanation="x", why_this_pattern="x",
    ))
    res = client.post("/api/parse-followup",
                      json={"followUp": "two sum [2,7] target 9"})
    assert res.status_code == 200
    assert res.get_json()["scene"] == "hashmap_iteration"


# ── POST /api/render-lesson ───────────────────────────────────────────────────

def test_render_lesson_happy_path(client, mocker):
    mocker.patch("app.submit_lesson", return_value="lesson-job-id")
    body = {
        "steps": [
            {"scene": "function_plot",
             "params": {"expression": "x**2", "domain": [0, 4]},
             "caption": "the curve"},
            {"scene": "riemann_sum",
             "params": {"expression": "x**2", "domain": [0, 4], "n": 4, "method": "midpoint"},
             "caption": "rectangles"},
        ],
    }
    res = client.post("/api/render-lesson", json=body)
    assert res.status_code == 202
    assert res.get_json()["job_id"] == "lesson-job-id"


def test_render_lesson_missing_steps_returns_400(client):
    res = client.post("/api/render-lesson", json={})
    assert res.status_code == 400


def test_render_lesson_empty_list_returns_400(client):
    res = client.post("/api/render-lesson", json={"steps": []})
    assert res.status_code == 400


def test_render_lesson_too_many_steps_returns_400(client):
    body = {"steps": [{"scene": "function_plot", "params": {}}] * 7}
    res = client.post("/api/render-lesson", json=body)
    assert res.status_code == 400


def test_render_lesson_step_missing_scene_returns_400(client):
    body = {"steps": [{"params": {"x": 1}}]}
    res = client.post("/api/render-lesson", json=body)
    assert res.status_code == 400


def test_parse_v2_falls_back_to_dsa_when_classifier_errors(client, mocker):
    """If the classifier raises, the endpoint defaults to DSA routing rather
    than 500'ing — graceful degradation."""
    from agent.leetcode_parser import ParsedLeetCode
    mocker.patch("app.classify_domain", side_effect=RuntimeError("classifier down"))
    mock_result = ParsedLeetCode(
        title="Two Sum",
        scene="hashmap_iteration",
        params={"array": [1, 2], "algorithm": "two_sum_hashmap", "target": 3, "caption": ""},
        explanation="x", why_this_pattern="x",
    )
    mocker.patch("app.parse_leetcode_problem", return_value=mock_result)

    res = client.post("/api/parse-problem-v2", json={"rawText": "anything"})
    assert res.status_code == 200
    assert res.get_json()["domain"] == "dsa"
