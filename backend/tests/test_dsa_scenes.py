"""
Integration tests for DSA scenes — actually runs Manim and checks output exists.
Run with: pytest backend/tests/test_dsa_scenes.py -v -m integration
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND    = Path(__file__).parent.parent
SCENE_FILE = "scenes/dsa_scene.py"


def _render(tmp_path: Path, scene_class: str, params: dict):
    job_id = f"test-{scene_class.lower()}-{abs(hash(str(params))) % 9999}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / f"{job_id}.json").write_text(json.dumps(params))
    return subprocess.run(
        [sys.executable, "-m", "manim", "-ql",
         "--media_dir", str(tmp_path / "media"), "--disable_caching",
         SCENE_FILE, scene_class],
        capture_output=True, text=True, timeout=120,
        cwd=str(BACKEND),
        env={**os.environ, "MANIM_JOB_ID": job_id, "MANIM_TEMP_DIR": str(tmp_path)},
    )


def _ok(result, tmp_path, scene_class):
    assert result.returncode == 0, f"STDERR:\n{result.stderr[-800:]}"
    stem   = Path(SCENE_FILE).stem
    output = tmp_path / "media" / "videos" / stem / "480p15" / f"{scene_class}.mp4"
    assert output.exists(), f"Output not found: {output}"


# ---------------------------------------------------------------------------
# ArrayPointerScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_array_pointer_binary_search(tmp_path):
    _ok(_render(tmp_path, "ArrayPointerScene", {
        "array": [1, 3, 5, 7, 9, 11, 13], "algorithm": "binary_search", "target": 7,
    }), tmp_path, "ArrayPointerScene")


@pytest.mark.integration
def test_array_pointer_two_pointers(tmp_path):
    _ok(_render(tmp_path, "ArrayPointerScene", {
        "array": [1, 2, 3, 4, 5, 6], "algorithm": "two_pointers", "target": 7,
    }), tmp_path, "ArrayPointerScene")


@pytest.mark.integration
def test_array_pointer_palindrome(tmp_path):
    _ok(_render(tmp_path, "ArrayPointerScene", {
        "array": ["r", "a", "c", "e", "c", "a", "r"], "algorithm": "palindrome",
    }), tmp_path, "ArrayPointerScene")


# ---------------------------------------------------------------------------
# SlidingWindowScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_sliding_window_fixed(tmp_path):
    _ok(_render(tmp_path, "SlidingWindowScene", {
        "array": [2, 1, 5, 1, 3, 2], "algorithm": "max_subarray_fixed", "k": 3,
    }), tmp_path, "SlidingWindowScene")


@pytest.mark.integration
def test_sliding_window_unique(tmp_path):
    _ok(_render(tmp_path, "SlidingWindowScene", {
        "array": ["a", "b", "c", "a", "b", "c", "b", "b"],
        "algorithm": "longest_unique_substring",
    }), tmp_path, "SlidingWindowScene")


# ---------------------------------------------------------------------------
# LinkedListScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_linked_list_reverse(tmp_path):
    _ok(_render(tmp_path, "LinkedListScene", {
        "values": [1, 2, 3, 4, 5], "algorithm": "reverse",
    }), tmp_path, "LinkedListScene")


@pytest.mark.integration
def test_linked_list_find_middle(tmp_path):
    _ok(_render(tmp_path, "LinkedListScene", {
        "values": [1, 2, 3, 4, 5], "algorithm": "find_middle",
    }), tmp_path, "LinkedListScene")


@pytest.mark.integration
def test_linked_list_merge(tmp_path):
    _ok(_render(tmp_path, "LinkedListScene", {
        "values": [1, 3, 5], "algorithm": "merge_sorted", "values2": [2, 4, 6],
    }), tmp_path, "LinkedListScene")


# ---------------------------------------------------------------------------
# TreeTraversalScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_tree_bfs(tmp_path):
    _ok(_render(tmp_path, "TreeTraversalScene", {
        "values": [1, 2, 3, 4, 5, 6, 7], "algorithm": "bfs",
    }), tmp_path, "TreeTraversalScene")


@pytest.mark.integration
def test_tree_inorder(tmp_path):
    _ok(_render(tmp_path, "TreeTraversalScene", {
        "values": [4, 2, 6, 1, 3, 5, 7], "algorithm": "inorder",
    }), tmp_path, "TreeTraversalScene")


@pytest.mark.integration
def test_tree_with_nulls(tmp_path):
    _ok(_render(tmp_path, "TreeTraversalScene", {
        "values": [1, 2, 3, None, None, 4, 5], "algorithm": "preorder",
    }), tmp_path, "TreeTraversalScene")


# ---------------------------------------------------------------------------
# GraphScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_graph_bfs(tmp_path):
    _ok(_render(tmp_path, "GraphScene", {
        "num_nodes": 6, "edges": [[0,1],[0,2],[1,3],[1,4],[2,5]],
        "start_node": 0, "algorithm": "bfs",
    }), tmp_path, "GraphScene")


@pytest.mark.integration
def test_graph_dfs(tmp_path):
    _ok(_render(tmp_path, "GraphScene", {
        "num_nodes": 5, "edges": [[0,1],[0,2],[1,3],[2,4]],
        "start_node": 0, "algorithm": "dfs",
    }), tmp_path, "GraphScene")


# ---------------------------------------------------------------------------
# DPArrayScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_dp_fibonacci(tmp_path):
    _ok(_render(tmp_path, "DPArrayScene", {
        "algorithm": "fibonacci", "n": 8,
    }), tmp_path, "DPArrayScene")


@pytest.mark.integration
def test_dp_climbing_stairs(tmp_path):
    _ok(_render(tmp_path, "DPArrayScene", {
        "algorithm": "climbing_stairs", "n": 7,
    }), tmp_path, "DPArrayScene")


@pytest.mark.integration
def test_dp_house_robber(tmp_path):
    _ok(_render(tmp_path, "DPArrayScene", {
        "algorithm": "house_robber", "n": 6,
    }), tmp_path, "DPArrayScene")


# ---------------------------------------------------------------------------
# StackQueueScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_stack_operations(tmp_path):
    _ok(_render(tmp_path, "StackQueueScene", {
        "operations": ["push 3", "push 1", "push 4", "pop", "push 1", "push 5"],
        "structure": "stack",
    }), tmp_path, "StackQueueScene")


@pytest.mark.integration
def test_queue_operations(tmp_path):
    _ok(_render(tmp_path, "StackQueueScene", {
        "operations": ["push 1", "push 2", "push 3", "pop", "push 4", "pop"],
        "structure": "queue",
    }), tmp_path, "StackQueueScene")
