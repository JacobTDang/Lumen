"""Integration tests for DSA pattern scenes (composes primitives + actually renders)."""
import json, os, subprocess, sys
from pathlib import Path
import pytest

BACKEND    = Path(__file__).parent.parent
SCENE_FILE = "scenes/dsa_pattern_scene.py"


def _render(tmp_path, scene_class, params):
    job_id = f"test-{scene_class.lower()[:18]}-{abs(hash(str(params))) % 9999}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / f"{job_id}.json").write_text(json.dumps(params))
    return subprocess.run(
        [sys.executable, "-m", "manim", "-ql",
         "--media_dir", str(tmp_path / "media"), "--disable_caching",
         SCENE_FILE, scene_class],
        capture_output=True, text=True, timeout=180,
        cwd=str(BACKEND),
        env={**os.environ, "MANIM_JOB_ID": job_id, "MANIM_TEMP_DIR": str(tmp_path)},
    )


def _ok(result, tmp_path, scene_class):
    assert result.returncode == 0, f"STDERR:\n{result.stderr[-700:]}"
    out = tmp_path / "media" / "videos" / Path(SCENE_FILE).stem / "480p15" / f"{scene_class}.mp4"
    assert out.exists(), f"Missing: {out}"


# ---------------------------------------------------------------------------
# TwoPointersOppositeScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_tpo_palindrome_pass(tmp_path):
    _ok(_render(tmp_path, "TwoPointersOppositeScene",
                {"array": ["r","a","c","e","c","a","r"], "algorithm": "palindrome"}),
        tmp_path, "TwoPointersOppositeScene")


@pytest.mark.integration
def test_tpo_palindrome_fail(tmp_path):
    _ok(_render(tmp_path, "TwoPointersOppositeScene",
                {"array": ["h","e","l","l","o"], "algorithm": "palindrome"}),
        tmp_path, "TwoPointersOppositeScene")


@pytest.mark.integration
def test_tpo_two_sum_sorted(tmp_path):
    _ok(_render(tmp_path, "TwoPointersOppositeScene",
                {"array": [1, 2, 4, 7, 11, 15], "algorithm": "two_sum_sorted", "target": 9}),
        tmp_path, "TwoPointersOppositeScene")


@pytest.mark.integration
def test_tpo_container_water(tmp_path):
    _ok(_render(tmp_path, "TwoPointersOppositeScene",
                {"array": [1, 8, 6, 2, 5, 4, 8, 3, 7], "algorithm": "container_water"}),
        tmp_path, "TwoPointersOppositeScene")


# ---------------------------------------------------------------------------
# HashMapIterationScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_hmi_frequency_count(tmp_path):
    _ok(_render(tmp_path, "HashMapIterationScene",
                {"array": ["a","b","a","c","b","a"], "algorithm": "frequency_count"}),
        tmp_path, "HashMapIterationScene")


@pytest.mark.integration
def test_hmi_two_sum_found(tmp_path):
    _ok(_render(tmp_path, "HashMapIterationScene",
                {"array": [2, 7, 11, 15], "algorithm": "two_sum_hashmap", "target": 9}),
        tmp_path, "HashMapIterationScene")


@pytest.mark.integration
def test_hmi_two_sum_not_found(tmp_path):
    _ok(_render(tmp_path, "HashMapIterationScene",
                {"array": [1, 2, 3, 4], "algorithm": "two_sum_hashmap", "target": 100}),
        tmp_path, "HashMapIterationScene")


# ---------------------------------------------------------------------------
# TwoPointersSameDirScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_tpsd_remove_duplicates(tmp_path):
    _ok(_render(tmp_path, "TwoPointersSameDirScene",
                {"array": [1, 1, 2, 2, 3, 4], "algorithm": "remove_duplicates"}),
        tmp_path, "TwoPointersSameDirScene")


@pytest.mark.integration
def test_tpsd_move_zeros(tmp_path):
    _ok(_render(tmp_path, "TwoPointersSameDirScene",
                {"array": [0, 1, 0, 3, 12], "algorithm": "move_zeros"}),
        tmp_path, "TwoPointersSameDirScene")


# ---------------------------------------------------------------------------
# SlidingWindowVariableScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_swv_longest_no_repeat(tmp_path):
    _ok(_render(tmp_path, "SlidingWindowVariableScene",
                {"array": ["a", "b", "c", "a", "b", "c"],
                 "algorithm": "longest_no_repeat"}),
        tmp_path, "SlidingWindowVariableScene")


@pytest.mark.integration
def test_swv_at_most_k_distinct(tmp_path):
    _ok(_render(tmp_path, "SlidingWindowVariableScene",
                {"array": ["a", "b", "a", "c", "b", "c"],
                 "algorithm": "longest_at_most_k_distinct", "k": 2}),
        tmp_path, "SlidingWindowVariableScene")


# ---------------------------------------------------------------------------
# BinarySearchIndexScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_bsi_find_target(tmp_path):
    _ok(_render(tmp_path, "BinarySearchIndexScene",
                {"array": [1, 3, 5, 7, 9, 11, 13, 15],
                 "algorithm": "find_target", "target": 7}),
        tmp_path, "BinarySearchIndexScene")


@pytest.mark.integration
def test_bsi_first_occurrence(tmp_path):
    _ok(_render(tmp_path, "BinarySearchIndexScene",
                {"array": [1, 2, 2, 2, 3, 4, 5],
                 "algorithm": "first_occurrence", "target": 2}),
        tmp_path, "BinarySearchIndexScene")


# ---------------------------------------------------------------------------
# BinarySearchAnswerScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_bsa_basic(tmp_path):
    _ok(_render(tmp_path, "BinarySearchAnswerScene",
                {"min_value": 1, "max_value": 16, "true_at": 7,
                 "predicate_label": "feasible(x)"}),
        tmp_path, "BinarySearchAnswerScene")


# ---------------------------------------------------------------------------
# MonotonicStackScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_mstk_next_greater(tmp_path):
    _ok(_render(tmp_path, "MonotonicStackScene",
                {"array": [2, 1, 5, 6, 2, 3],
                 "algorithm": "next_greater", "monotone": "decreasing"}),
        tmp_path, "MonotonicStackScene")


# ---------------------------------------------------------------------------
# PrefixSumScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_psum_build(tmp_path):
    _ok(_render(tmp_path, "PrefixSumScene",
                {"array": [3, 1, 4, 1, 5, 9, 2], "algorithm": "build_prefix"}),
        tmp_path, "PrefixSumScene")


@pytest.mark.integration
def test_psum_range_query(tmp_path):
    _ok(_render(tmp_path, "PrefixSumScene",
                {"array": [3, 1, 4, 1, 5, 9, 2],
                 "algorithm": "range_sum_query", "query_range": [1, 4]}),
        tmp_path, "PrefixSumScene")
