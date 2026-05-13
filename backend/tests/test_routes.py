import json

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


# ── POST /api/quiz ────────────────────────────────────────────────────────────

def test_quiz_missing_prior_returns_400(client):
    res = client.post("/api/quiz", json={})
    assert res.status_code == 400


def test_quiz_blank_prior_returns_400(client):
    res = client.post("/api/quiz", json={"prior": {"title": "", "scene": ""}})
    assert res.status_code == 400


def test_quiz_happy_path_returns_questions(client, mocker):
    """A valid prior produces questions through call_gemini."""
    fake_payload = {
        "questions": [
            {
                "q": "What invariant does this algorithm maintain?",
                "options": ["A", "B", "C", "D"],
                "correct": 1,
                "why": "Because B.",
            }
        ]
    }
    fake_response = type("R", (), {"text": json.dumps(fake_payload)})()
    mocker.patch("app.call_gemini", return_value=fake_response)

    body = {
        "prior": {
            "title": "Two Sum",
            "scene": "hashmap_iteration",
            "params": {"array": [2, 7, 11, 15], "target": 9},
            "pseudocode": "seen = {}\nfor i, v in enumerate(nums):\n    ...",
            "explanation": "Walk array, complement lookup in hashmap.",
        }
    }
    res = client.post("/api/quiz", json=body)
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["questions"]) == 1
    assert data["questions"][0]["correct"] == 1


def test_quiz_gemini_failure_returns_500(client, mocker):
    mocker.patch("app.call_gemini", side_effect=RuntimeError("LLM down"))
    res = client.post("/api/quiz", json={"prior": {"title": "x", "scene": "y"}})
    assert res.status_code == 500


# ── POST/GET /api/share ───────────────────────────────────────────────────────

def test_share_missing_parsed_returns_400(client):
    res = client.post("/api/share", json={})
    assert res.status_code == 400


def test_share_parsed_without_scene_returns_400(client):
    res = client.post("/api/share", json={"parsed": {"title": "x"}})
    assert res.status_code == 400


def test_share_round_trip(client, mocker):
    """Posting a parsed problem returns a code; GET with that code returns
    the same payload. Use an in-memory dict to avoid touching the real file."""
    fake_store: dict = {}
    mocker.patch("app._load_shares", side_effect=lambda: dict(fake_store))
    mocker.patch("app._save_shares", side_effect=lambda d: fake_store.update(d))

    parsed = {
        "title": "Two Sum",
        "scene": "hashmap_iteration",
        "params": {"array": [2, 7, 11, 15], "target": 9},
        "domain": "dsa",
    }
    res = client.post("/api/share", json={"parsed": parsed})
    assert res.status_code == 200
    code = res.get_json()["shareCode"]
    assert len(code) == 8

    # Now fetch it back
    res2 = client.get(f"/api/share/{code}")
    assert res2.status_code == 200
    assert res2.get_json()["parsed"]["title"] == "Two Sum"


def test_share_get_invalid_code_returns_400(client):
    res = client.get("/api/share/abc")
    assert res.status_code == 400


def test_share_get_unknown_code_returns_404(client, mocker):
    mocker.patch("app._load_shares", return_value={})
    res = client.get("/api/share/aaaabbbb")
    assert res.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Phase D — pin/unpin endpoints
# ─────────────────────────────────────────────────────────────────────────────

def test_pin_endpoint_missing_jobid(client):
    res = client.post("/api/pin", json={})
    assert res.status_code == 400


def test_pin_endpoint_unknown_job_returns_404(client, mocker):
    mocker.patch("app.pin_video", side_effect=ValueError("unknown job_id: x"))
    res = client.post("/api/pin", json={"jobId": "x"})
    assert res.status_code == 404


def test_pin_endpoint_pending_job_returns_409(client, mocker):
    mocker.patch("app.pin_video", side_effect=ValueError("cannot pin job in status='pending'"))
    res = client.post("/api/pin", json={"jobId": "x"})
    assert res.status_code == 409


def test_pin_endpoint_happy_path(client, mocker):
    mocker.patch("app.pin_video", return_value="/media/lessons/abc.mp4")
    res = client.post("/api/pin", json={"jobId": "abc"})
    assert res.status_code == 200
    assert res.get_json()["url"] == "/media/lessons/abc.mp4"


def test_unpin_endpoint_happy_path(client, mocker):
    mocker.patch("app.unpin_video", return_value=True)
    res = client.delete("/api/pin/abc")
    assert res.status_code == 200
    assert res.get_json()["ok"] is True


def test_unpin_endpoint_idempotent(client, mocker):
    mocker.patch("app.unpin_video", return_value=False)
    res = client.delete("/api/pin/nonexistent")
    assert res.status_code == 200  # idempotent: still 200 even if not pinned


# ─────────────────────────────────────────────────────────────────────────────
# /api/trace/<job_id> — render trace endpoint
# ─────────────────────────────────────────────────────────────────────────────

def test_trace_endpoint_not_found(client):
    res = client.get("/api/trace/nonexistent-job")
    assert res.status_code == 404


def test_init_sentry_noop_when_dsn_unset(monkeypatch):
    """No-op (does not raise) when SENTRY_DSN is absent."""
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    from app import _init_sentry
    _init_sentry()  # must not raise


def test_init_sentry_handles_missing_sdk_gracefully(monkeypatch):
    """When SENTRY_DSN is set but sentry-sdk isn't installed, log + skip."""
    monkeypatch.setenv("SENTRY_DSN", "https://fake@example.com/0")
    from app import _init_sentry
    # sentry_sdk almost certainly isn't installed in this env, so ImportError
    # path triggers. Either way: must not raise.
    _init_sentry()


def test_trace_endpoint_returns_active_trace(client):
    """An in-memory trace is served directly from the registry."""
    from agent.trace import new_trace, LLMCall

    trace = new_trace("test-trace-active")
    trace.add_call(LLMCall(
        label="narrative_plan", model="gpt-oss-120b",
        elapsed_ms=1234, prompt_chars=500, response_chars=800,
    ))
    res = client.get("/api/trace/test-trace-active")
    assert res.status_code == 200
    body = res.get_json()
    assert body["job_id"] == "test-trace-active"
    assert body["total_calls"] == 1
    assert body["calls"][0]["label"] == "narrative_plan"


# ─────────────────────────────────────────────────────────────────────────────
# /media/<path> — CDN cache headers (item #23)
# ─────────────────────────────────────────────────────────────────────────────

def test_media_lesson_has_immutable_cache_header(client, tmp_path, monkeypatch):
    """Item #23 regression: /media/lessons/*.mp4 must respond with a long
    max-age + immutable Cache-Control so a CDN can cache aggressively."""
    import os as _os
    # Build a fake media dir with a lesson file
    media_dir = _os.path.realpath(_os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "media",
    ))
    lessons_dir = _os.path.join(media_dir, "lessons")
    _os.makedirs(lessons_dir, exist_ok=True)
    test_path = _os.path.join(lessons_dir, "test_cdn_header.mp4")
    with open(test_path, "wb") as fh:
        fh.write(b"\x00\x00\x00\x18ftypmp42")   # minimal mp4 magic
    try:
        res = client.get("/media/lessons/test_cdn_header.mp4")
        assert res.status_code == 200
        cc = res.headers.get("Cache-Control", "")
        assert "immutable" in cc, f"expected immutable in Cache-Control, got: {cc}"
        assert "max-age=31536000" in cc, f"expected year-long max-age, got: {cc}"
    finally:
        try: _os.remove(test_path)
        except OSError: pass


def test_direct_lesson_stream_requires_question(client):
    res = client.post("/api/direct-lesson-stream", json={})
    assert res.status_code == 400


def test_direct_lesson_stream_rejects_invalid_style(client):
    res = client.post("/api/direct-lesson-stream",
                       json={"question": "x", "style": "bogus"})
    assert res.status_code == 400


def test_direct_lesson_stream_returns_event_stream(client, mocker):
    """Item #11 regression: endpoint must emit text/event-stream and deliver
    the expected progression of SSE events."""
    from agent.lesson_director import NarrativePlan, ScenePlan, ToolCall

    fake_narrative = NarrativePlan(
        lesson_title="t", core_insight="i", narrative_arc="a",
        scenes=[ScenePlan(title="One", objective="o", is_aha_moment=True),
                ScenePlan(title="Two", objective="o2")],
    )
    mocker.patch("agent.lesson_director.narrative_plan", return_value=fake_narrative)
    mocker.patch("agent.lesson_director._build_scene_safe",
                 return_value=[ToolCall(tool="set_caption", args={"text": "x"})])
    mocker.patch("app.submit_lesson", return_value="lesson-from-sse")

    res = client.post("/api/direct-lesson-stream",
                       json={"question": "anything"})
    assert res.status_code == 200
    assert res.headers["Content-Type"].startswith("text/event-stream")
    body = res.get_data(as_text=True)
    # Must contain at least the stage transitions, scene_done events, and job_id
    assert "event: stage" in body
    assert "planning_narrative" in body
    assert "building_scenes" in body
    assert "queued" in body
    assert "event: scene_done" in body
    assert "event: job_id" in body
    assert "lesson-from-sse" in body
    assert "event: done" in body


def test_media_job_does_not_have_immutable_header(client, tmp_path):
    """Non-lessons paths (job temp output) must NOT be marked immutable."""
    import os as _os
    media_dir = _os.path.realpath(_os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "media",
    ))
    jobs_dir = _os.path.join(media_dir, "jobs", "test_job_no_cdn")
    _os.makedirs(jobs_dir, exist_ok=True)
    test_path = _os.path.join(jobs_dir, "x.mp4")
    with open(test_path, "wb") as fh:
        fh.write(b"\x00\x00\x00\x18ftypmp42")
    try:
        res = client.get("/media/jobs/test_job_no_cdn/x.mp4")
        assert res.status_code == 200
        cc = res.headers.get("Cache-Control", "")
        assert "immutable" not in cc, f"job files should NOT be immutable: {cc}"
    finally:
        try: _os.remove(test_path)
        except OSError: pass
