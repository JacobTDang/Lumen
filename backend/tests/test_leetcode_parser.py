"""
Tests for backend/agent/leetcode_parser.py.

Unit tests mock the LLM via the _call_model seam — no real API calls.
The integration test (marked) hits the real model stack.
"""
import json

import pytest


def _patch_model(mocker, payload: str):
    """Patch the single LLM seam to return a fixed string."""
    return mocker.patch("agent.leetcode_parser._call_model", return_value=payload)


def _patch_model_sequence(mocker, payloads: list[str]):
    """Patch the LLM seam to return different strings on successive calls."""
    return mocker.patch("agent.leetcode_parser._call_model", side_effect=payloads)


# ── happy paths ──────────────────────────────────────────────────────────────

def test_parse_two_sum_extracts_array_and_target(mocker):
    """A Two Sum problem should map to hashmap_iteration with the literal array."""
    payload = json.dumps({
        "title": "Two Sum",
        "scene": "hashmap_iteration",
        "params": {
            "array": [2, 7, 11, 15],
            "algorithm": "two_sum_hashmap",
            "target": 9,
        },
        "explanation": "Walk the array; for each value v, check if (target − v) is already in the map.",
        "why_this_pattern": "Hashmap gives O(1) complement lookup, reducing the brute-force O(n²) to O(n).",
    })
    _patch_model(mocker, payload)

    from agent.leetcode_parser import parse_problem
    result = parse_problem("Given nums = [2,7,11,15] and target = 9, return indices of two numbers such that they add up to target.")

    assert result.scene == "hashmap_iteration"
    assert result.params["array"] == [2, 7, 11, 15]
    assert result.params["target"] == 9
    assert result.params["algorithm"] == "two_sum_hashmap"
    assert "complement" in result.why_this_pattern.lower() or "hashmap" in result.why_this_pattern.lower()


def test_parse_passes_through_pseudocode_when_present(mocker):
    """When the model returns pseudocode using the user's variable names, it
    should round-trip into ParsedLeetCode.pseudocode."""
    payload = json.dumps({
        "title": "Two Sum",
        "scene": "hashmap_iteration",
        "params": {"array": [2, 7, 11, 15], "algorithm": "two_sum_hashmap", "target": 9},
        "explanation": "ok",
        "why_this_pattern": "ok",
        "pseudocode":
            "seen = {}\n"
            "for i, v in enumerate(nums):\n"
            "    if target - v in seen:\n"
            "        return [seen[target - v], i]\n"
            "    seen[v] = i",
    })
    _patch_model(mocker, payload)

    from agent.leetcode_parser import parse_problem
    result = parse_problem("Two sum nums=[2,7,11,15] target=9")
    assert "nums" in result.pseudocode
    assert "target" in result.pseudocode


def test_parse_pseudocode_defaults_to_empty(mocker):
    """If the model omits pseudocode, the field should default to an empty
    string (no exception, parser still succeeds)."""
    payload = json.dumps({
        "title": "Kadane",
        "scene": "kadanes",
        "params": {"array": [1, -2, 3]},
        "explanation": "ok",
        "why_this_pattern": "ok",
    })
    _patch_model(mocker, payload)

    from agent.leetcode_parser import parse_problem
    result = parse_problem("max subarray of [1,-2,3]")
    assert result.pseudocode == ""


def test_parse_passes_through_step_lines(mocker):
    """When the model returns step_lines, they round-trip through the parser
    so scenes can sync line highlighting against the custom pseudocode."""
    payload = json.dumps({
        "title": "Two Sum",
        "scene": "hashmap_iteration",
        "params": {"array": [2, 7, 11, 15], "algorithm": "two_sum_hashmap", "target": 9},
        "explanation": "ok",
        "why_this_pattern": "ok",
        "pseudocode": "seen = {}\nfor i, num in enumerate(nums):\n    need = target - num\n    if need in seen:\n        return [seen[need], i]\n    seen[num] = i",
        "step_lines": {"match": 4, "store": 5},
    })
    _patch_model(mocker, payload)

    from agent.leetcode_parser import parse_problem
    result = parse_problem("Two sum nums=[2,7,11,15] target=9")
    assert result.step_lines == {"match": 4, "store": 5}


def test_parse_step_lines_defaults_to_empty(mocker):
    """If the model omits step_lines, the field defaults to {} (no errors)."""
    payload = json.dumps({
        "title": "X",
        "scene": "kadanes",
        "params": {"array": [1, 2, 3]},
        "explanation": "ok",
        "why_this_pattern": "ok",
        "pseudocode": "",
    })
    _patch_model(mocker, payload)

    from agent.leetcode_parser import parse_problem
    result = parse_problem("max subarray of [1,2,3]")
    assert result.step_lines == {}


def test_parse_alternatives_round_trip(mocker):
    """Parser returns list of Alternative entries with their own valid params."""
    payload = json.dumps({
        "title": "Two Sum",
        "scene": "hashmap_iteration",
        "params": {"array": [2, 7, 11, 15], "algorithm": "two_sum_hashmap", "target": 9},
        "explanation": "ok", "why_this_pattern": "ok",
        "pseudocode": "", "step_lines": {},
        "alternatives": [
            {
                "scene": "two_pointers_opposite",
                "params": {"array": [2, 7, 11, 15], "algorithm": "two_sum_sorted", "target": 9},
                "label": "Show with two-pointer (sorted)",
                "why": "Eliminates the hashmap O(n) space.",
            },
        ],
    })
    _patch_model(mocker, payload)

    from agent.leetcode_parser import parse_problem
    result = parse_problem("Two Sum nums=[2,7,11,15] target=9")
    assert len(result.alternatives) == 1
    alt = result.alternatives[0]
    assert alt.scene == "two_pointers_opposite"
    assert alt.params["target"] == 9
    assert "two-pointer" in alt.label.lower()


def test_parse_alternatives_drops_invalid(mocker):
    """Alternatives with bad params are dropped, not crashing the whole parse."""
    payload = json.dumps({
        "title": "X", "scene": "kadanes",
        "params": {"array": [1, 2, 3]},
        "explanation": "ok", "why_this_pattern": "ok",
        "pseudocode": "", "step_lines": {},
        "alternatives": [
            {"scene": "binary_search_index", "params": {"target": "abc"},
             "label": "broken alt", "why": ""},  # invalid: target must be int
            {"scene": "prefix_sum", "params": {"array": [1, 2, 3]},
             "label": "Show as prefix sum", "why": "Visualizes cumulative sum."},
        ],
    })
    _patch_model(mocker, payload)

    from agent.leetcode_parser import parse_problem
    result = parse_problem("max subarray of [1,2,3]")
    # Bad alt dropped, good alt kept
    assert len(result.alternatives) == 1
    assert result.alternatives[0].scene == "prefix_sum"


def test_parse_alternatives_default_empty(mocker):
    payload = json.dumps({
        "title": "X", "scene": "kadanes",
        "params": {"array": [1, 2]},
        "explanation": "ok", "why_this_pattern": "ok",
    })
    _patch_model(mocker, payload)
    from agent.leetcode_parser import parse_problem
    result = parse_problem("any")
    assert result.alternatives == []


def test_parse_alternatives_excludes_self(mocker):
    """An alternative that has the same scene as the primary is dropped."""
    payload = json.dumps({
        "title": "X", "scene": "kadanes",
        "params": {"array": [1, 2, 3]},
        "explanation": "ok", "why_this_pattern": "ok",
        "alternatives": [
            {"scene": "kadanes", "params": {"array": [4, 5, 6]},
             "label": "Same scene", "why": ""},
        ],
    })
    _patch_model(mocker, payload)
    from agent.leetcode_parser import parse_problem
    result = parse_problem("any")
    assert result.alternatives == []


def test_parse_step_lines_coerces_string_values(mocker):
    """Some models return line indexes as strings ('3' instead of 3) — the
    parser should coerce them to int. Non-numeric entries are dropped."""
    payload = json.dumps({
        "title": "X",
        "scene": "kadanes",
        "params": {"array": [1, 2, 3]},
        "explanation": "ok",
        "why_this_pattern": "ok",
        "pseudocode": "",
        "step_lines": {"match": "3", "broken": "abc", "good": 5},
    })
    _patch_model(mocker, payload)

    from agent.leetcode_parser import parse_problem
    result = parse_problem("anything")
    assert result.step_lines == {"match": 3, "good": 5}


def test_parse_palindrome_picks_two_pointers_opposite(mocker):
    payload = json.dumps({
        "title": "Valid Palindrome",
        "scene": "two_pointers_opposite",
        "params": {
            "array": ["r", "a", "c", "e", "c", "a", "r"],
            "algorithm": "palindrome",
        },
        "explanation": "Compare characters from both ends, moving inward.",
        "why_this_pattern": "Two pointers eliminates the need for reversed-string allocation.",
    })
    _patch_model(mocker, payload)

    from agent.leetcode_parser import parse_problem
    result = parse_problem("Given a string s, return true if it is a palindrome. Example: s = 'racecar'.")

    assert result.scene == "two_pointers_opposite"
    assert result.params["algorithm"] == "palindrome"


def test_parse_kadane_extracts_negative_array(mocker):
    payload = json.dumps({
        "title": "Maximum Subarray",
        "scene": "kadanes",
        "params": {"array": [-2, 1, -3, 4, -1, 2, 1, -5, 4]},
        "explanation": "Track running sum; reset when it goes negative.",
        "why_this_pattern": "Kadane's keeps O(n) time and O(1) space.",
    })
    _patch_model(mocker, payload)

    from agent.leetcode_parser import parse_problem
    result = parse_problem("Find the contiguous subarray with the largest sum in [-2,1,-3,4,-1,2,1,-5,4].")

    assert result.scene == "kadanes"
    assert result.params["array"] == [-2, 1, -3, 4, -1, 2, 1, -5, 4]


# ── output cleanup ───────────────────────────────────────────────────────────

def test_parse_strips_markdown_fences(mocker):
    """gpt-oss / llama sometimes wrap JSON in ```json fences despite prompt."""
    payload = "```json\n" + json.dumps({
        "title": "Two Sum",
        "scene": "hashmap_iteration",
        "params": {"array": [1, 2, 3], "algorithm": "two_sum_hashmap", "target": 5},
        "explanation": "ok",
        "why_this_pattern": "ok",
    }) + "\n```"
    _patch_model(mocker, payload)

    from agent.leetcode_parser import parse_problem
    result = parse_problem("Two sum [1,2,3] target 5")
    assert result.scene == "hashmap_iteration"


def test_parse_strips_harmony_channels(mocker):
    """gpt-oss-120b emits <|channel|>analysis|message|>... harmony tokens around output."""
    inner = json.dumps({
        "title": "Two Sum",
        "scene": "hashmap_iteration",
        "params": {"array": [1, 2], "algorithm": "two_sum_hashmap", "target": 3},
        "explanation": "ok",
        "why_this_pattern": "ok",
    })
    payload = (
        "<|channel|>analysis<|message|>"
        "Let me think about this — it's a two-sum so hashmap_iteration is right..."
        "<|channel|>final<|message|>"
        f"{inner}"
        "<|end|>"
    )
    _patch_model(mocker, payload)

    from agent.leetcode_parser import parse_problem
    result = parse_problem("Two sum [1,2] target 3")
    assert result.scene == "hashmap_iteration"
    assert result.params["target"] == 3


def test_parse_strips_trailing_commas(mocker):
    """Open-source models occasionally emit JSON-like text with trailing commas."""
    payload = '{"title": "X", "scene": "kadanes", "params": {"array": [1, 2, 3,],}, "explanation": "ok", "why_this_pattern": "ok"}'
    _patch_model(mocker, payload)

    from agent.leetcode_parser import parse_problem
    result = parse_problem("Max subarray of [1,2,3]")
    assert result.scene == "kadanes"


def test_parse_falls_back_to_balanced_braces(mocker):
    """If the model wraps JSON in prose, fall back to extracting the first balanced object."""
    inner = json.dumps({
        "title": "Two Sum",
        "scene": "hashmap_iteration",
        "params": {"array": [1, 2], "algorithm": "two_sum_hashmap", "target": 3},
        "explanation": "ok",
        "why_this_pattern": "ok",
    })
    payload = f"Here is the JSON you requested:\n\n{inner}\n\nLet me know if you need adjustments."
    _patch_model(mocker, payload)

    from agent.leetcode_parser import parse_problem
    result = parse_problem("anything")
    assert result.scene == "hashmap_iteration"


# ── retry behavior ───────────────────────────────────────────────────────────

def test_parse_retries_on_first_attempt_failure(mocker):
    """First call returns garbage, second call returns valid JSON — should succeed."""
    good = json.dumps({
        "title": "Two Sum",
        "scene": "hashmap_iteration",
        "params": {"array": [1, 2], "algorithm": "two_sum_hashmap", "target": 3},
        "explanation": "ok",
        "why_this_pattern": "ok",
    })
    mock = _patch_model_sequence(mocker, ["this is not json at all", good])

    from agent.leetcode_parser import parse_problem
    result = parse_problem("Two sum")
    assert result.scene == "hashmap_iteration"
    assert mock.call_count == 2


def test_parse_raises_after_all_retries_fail(mocker):
    _patch_model_sequence(mocker, ["garbage one", "garbage two"])

    from agent.leetcode_parser import parse_problem
    with pytest.raises(ValueError, match="parse failed after"):
        parse_problem("anything")


# ── validation ───────────────────────────────────────────────────────────────

def test_parse_unknown_scene_raises(mocker):
    payload = json.dumps({
        "title": "Mystery",
        "scene": "banana_split",
        "params": {},
        "explanation": "x",
        "why_this_pattern": "y",
    })
    # Same garbage on both attempts — should fail after retries
    _patch_model_sequence(mocker, [payload, payload])

    from agent.leetcode_parser import parse_problem
    with pytest.raises(ValueError, match="unknown scene"):
        parse_problem("anything")


def test_parse_invalid_params_raises(mocker):
    """binary_search_index requires array of ints + integer target."""
    payload = json.dumps({
        "title": "Binary Search",
        "scene": "binary_search_index",
        "params": {"array": ["not", "numbers"], "target": "also-bad"},
        "explanation": "x",
        "why_this_pattern": "y",
    })
    _patch_model_sequence(mocker, [payload, payload])

    from agent.leetcode_parser import parse_problem
    with pytest.raises(ValueError, match="invalid params"):
        parse_problem("binary search [1,2,3] target 2")


def test_parse_empty_response_raises(mocker):
    _patch_model_sequence(mocker, ["", ""])

    from agent.leetcode_parser import parse_problem
    with pytest.raises(ValueError):
        parse_problem("anything")


def test_parse_malformed_json_raises(mocker):
    _patch_model_sequence(mocker, ["{not valid json", "{still not valid"])

    from agent.leetcode_parser import parse_problem
    with pytest.raises(ValueError):
        parse_problem("anything")


def test_parse_empty_input_raises():
    from agent.leetcode_parser import parse_problem
    with pytest.raises(ValueError, match="raw_text"):
        parse_problem("   ")


# ── integration (real model) ─────────────────────────────────────────────────

@pytest.mark.integration
def test_parse_real_two_sum_routes_to_hashmap():
    """End-to-end: real LLM should route Two Sum to hashmap_iteration."""
    from agent.leetcode_parser import parse_problem
    result = parse_problem(
        "Given an array of integers nums = [2,7,11,15] and an integer target = 9, "
        "return the indices of the two numbers such that they add up to target."
    )
    assert result.scene in ("hashmap_iteration", "two_pointers_opposite")
    assert isinstance(result.params.get("array"), list)
    assert len(result.params["array"]) >= 2
