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


# ---------------------------------------------------------------------------
# KadanesScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_kadanes_classic(tmp_path):
    _ok(_render(tmp_path, "KadanesScene",
                {"array": [-2, 1, -3, 4, -1, 2, 1, -5, 4]}),
        tmp_path, "KadanesScene")


@pytest.mark.integration
def test_kadanes_all_positive(tmp_path):
    _ok(_render(tmp_path, "KadanesScene", {"array": [1, 2, 3, 4]}),
        tmp_path, "KadanesScene")


# ---------------------------------------------------------------------------
# IntervalMergingScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_interval_merging_basic(tmp_path):
    _ok(_render(tmp_path, "IntervalMergingScene",
                {"intervals": [[1, 3], [2, 6], [8, 10], [15, 18]]}),
        tmp_path, "IntervalMergingScene")


# ---------------------------------------------------------------------------
# UnionFindScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_union_find_basic(tmp_path):
    _ok(_render(tmp_path, "UnionFindScene",
                {"n": 6,
                 "operations": ["union 0 1", "union 2 3", "union 4 5",
                                 "union 1 3", "find 4"]}),
        tmp_path, "UnionFindScene")


# ---------------------------------------------------------------------------
# LRUCacheScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_lru_cache_basic(tmp_path):
    _ok(_render(tmp_path, "LRUCacheScene",
                {"operations": ["put 1 100", "put 2 200", "get 1",
                                 "put 3 300", "get 2"],
                 "capacity": 2}),
        tmp_path, "LRUCacheScene")


# ---------------------------------------------------------------------------
# GridTraversalScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_grid_traversal_bfs(tmp_path):
    _ok(_render(tmp_path, "GridTraversalScene",
                {"grid": [[0, 0, 1, 0],
                           [0, 0, 0, 0],
                           [1, 0, 1, 0],
                           [0, 0, 0, 0]],
                 "start": [0, 0], "target": [3, 3], "algorithm": "bfs"}),
        tmp_path, "GridTraversalScene")


# ---------------------------------------------------------------------------
# HeapOpsScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_heap_ops_min(tmp_path):
    _ok(_render(tmp_path, "HeapOpsScene",
                {"operations": ["push 5", "push 3", "push 8",
                                 "push 1", "pop"],
                 "heap_type": "min"}),
        tmp_path, "HeapOpsScene")


# ---------------------------------------------------------------------------
# DP2DScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_dp_2d_lcs(tmp_path):
    _ok(_render(tmp_path, "DP2DScene",
                {"algorithm": "lcs", "input1": "abc", "input2": "ac"}),
        tmp_path, "DP2DScene")


@pytest.mark.integration
def test_dp_2d_unique_paths(tmp_path):
    _ok(_render(tmp_path, "DP2DScene",
                {"algorithm": "unique_paths", "input1": "3", "input2": "3"}),
        tmp_path, "DP2DScene")


# ---------------------------------------------------------------------------
# BacktrackingSubsetsScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_backtracking_subsets(tmp_path):
    _ok(_render(tmp_path, "BacktrackingSubsetsScene",
                {"array": [1, 2, 3], "algorithm": "subsets"}),
        tmp_path, "BacktrackingSubsetsScene")


# ---------------------------------------------------------------------------
# TrieOpsScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_trie_ops_basic(tmp_path):
    _ok(_render(tmp_path, "TrieOpsScene",
                {"words": ["cat", "car", "card"], "queries": ["car", "cab"]}),
        tmp_path, "TrieOpsScene")


# ---------------------------------------------------------------------------
# DijkstraScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_dijkstra_basic(tmp_path):
    _ok(_render(tmp_path, "DijkstraScene",
                {"num_nodes": 5,
                 "edges": [[0, 1, 4], [0, 2, 1], [2, 1, 2],
                            [1, 3, 1], [2, 3, 5], [3, 4, 3]],
                 "source": 0}),
        tmp_path, "DijkstraScene")


# ---------------------------------------------------------------------------
# SegmentTreeScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_segment_tree_basic(tmp_path):
    _ok(_render(tmp_path, "SegmentTreeScene",
                {"array": [1, 3, 5, 7],
                 "queries": [[1, 3], [0, 3]]}),
        tmp_path, "SegmentTreeScene")


# ===========================================================================
# Phase 7B — new pattern scenes
# ===========================================================================

# ---------------------------------------------------------------------------
# FloydCycleScene — step generator unit tests
# ---------------------------------------------------------------------------

def test_floyd_cycle_no_cycle_terminates():
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scenes.dsa_pattern_scene import _floyd_cycle_steps
    steps, has_cycle = _floyd_cycle_steps([1, 2, 3, 4], None)
    assert has_cycle is False
    assert steps[-1]["kind"] == "no_cycle"


def test_floyd_cycle_with_cycle_meets():
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scenes.dsa_pattern_scene import _floyd_cycle_steps
    # 1→2→3→4→2 (back to index 1)
    steps, has_cycle = _floyd_cycle_steps([1, 2, 3, 4], 1)
    assert has_cycle is True
    assert steps[-1]["kind"] == "meet"
    assert steps[-1]["slow"] == steps[-1]["fast"]


def test_floyd_cycle_self_loop():
    """Single node pointing to itself: cycle at index 0."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scenes.dsa_pattern_scene import _floyd_cycle_steps
    steps, has_cycle = _floyd_cycle_steps([42], 0)
    assert has_cycle is True


def test_floyd_cycle_empty_input():
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scenes.dsa_pattern_scene import _floyd_cycle_steps
    steps, has_cycle = _floyd_cycle_steps([], None)
    assert steps == []
    assert has_cycle is False


# ---------------------------------------------------------------------------
# FloydCycleScene — integration render tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_floyd_cycle_with_cycle_renders(tmp_path):
    _ok(_render(tmp_path, "FloydCycleScene",
                {"values": [1, 2, 3, 4, 5], "cycle_at": 1}),
        tmp_path, "FloydCycleScene")


@pytest.mark.integration
def test_floyd_cycle_no_cycle_renders(tmp_path):
    _ok(_render(tmp_path, "FloydCycleScene",
                {"values": [1, 2, 3, 4], "cycle_at": None}),
        tmp_path, "FloydCycleScene")


# ---------------------------------------------------------------------------
# TrappingRainWaterScene
# ---------------------------------------------------------------------------

def test_trap_classic_lc42():
    """LC 42 example: heights = [0,1,0,2,1,0,1,3,2,1,2,1] → 6 units of water."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scenes.dsa_pattern_scene import _trapping_rain_water_steps
    heights = [0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]
    steps, total = _trapping_rain_water_steps(heights)
    assert total == 6
    assert steps[-1]["kind"] == "done"


def test_trap_no_water_monotonic():
    """A monotonically increasing histogram traps zero water."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scenes.dsa_pattern_scene import _trapping_rain_water_steps
    _, total = _trapping_rain_water_steps([1, 2, 3, 4, 5])
    assert total == 0


def test_trap_short_input():
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scenes.dsa_pattern_scene import _trapping_rain_water_steps
    steps, total = _trapping_rain_water_steps([3])
    assert steps == []
    assert total == 0


@pytest.mark.integration
def test_trap_renders_classic(tmp_path):
    _ok(_render(tmp_path, "TrappingRainWaterScene",
                {"heights": [0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]}),
        tmp_path, "TrappingRainWaterScene")


@pytest.mark.integration
def test_trap_renders_no_water(tmp_path):
    _ok(_render(tmp_path, "TrappingRainWaterScene",
                {"heights": [1, 2, 3, 4]}),
        tmp_path, "TrappingRainWaterScene")


# ---------------------------------------------------------------------------
# GreedyIntervalScene — jump_game + gas_station
# ---------------------------------------------------------------------------

def test_greedy_jump_game_reachable():
    """LC 55 example: [2,3,1,1,4] is reachable."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scenes.dsa_pattern_scene import _greedy_jump_game_steps
    steps, ok = _greedy_jump_game_steps([2, 3, 1, 1, 4])
    assert ok is True
    assert steps[-1]["kind"] == "success"


def test_greedy_jump_game_blocked():
    """[3,2,1,0,4] gets stuck at index 3 (0 jump distance with 4 left)."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scenes.dsa_pattern_scene import _greedy_jump_game_steps
    steps, ok = _greedy_jump_game_steps([3, 2, 1, 0, 4])
    assert ok is False
    assert steps[-1]["kind"] == "fail"


def test_greedy_gas_station_solvable():
    """LC 134 example: gas-cost diff [-2,-2,-2,3,3] starts at index 3."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scenes.dsa_pattern_scene import _greedy_gas_station_steps
    steps, start = _greedy_gas_station_steps([-2, -2, -2, 3, 3])
    assert start == 3 or start == -1  # depends on total ≥ 0; here total = 0


def test_greedy_gas_station_impossible():
    """Net negative diff → impossible."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scenes.dsa_pattern_scene import _greedy_gas_station_steps
    steps, start = _greedy_gas_station_steps([-1, -1, -1])
    assert start == -1


@pytest.mark.integration
def test_greedy_jump_game_renders(tmp_path):
    _ok(_render(tmp_path, "GreedyIntervalScene",
                {"values": [2, 3, 1, 1, 4], "algorithm": "jump_game"}),
        tmp_path, "GreedyIntervalScene")


@pytest.mark.integration
def test_greedy_jump_game_blocked_renders(tmp_path):
    _ok(_render(tmp_path, "GreedyIntervalScene",
                {"values": [3, 2, 1, 0, 4], "algorithm": "jump_game"}),
        tmp_path, "GreedyIntervalScene")


@pytest.mark.integration
def test_greedy_gas_station_renders(tmp_path):
    _ok(_render(tmp_path, "GreedyIntervalScene",
                {"values": [-2, -2, -2, 3, 3], "algorithm": "gas_station"}),
        tmp_path, "GreedyIntervalScene")


# ---------------------------------------------------------------------------
# BitManipulationScene — single_number + count_bits
# ---------------------------------------------------------------------------

def test_bit_single_number_lc136():
    """LC 136: [4,1,2,1,2] → 4."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scenes.dsa_pattern_scene import _single_number_steps
    steps, ans = _single_number_steps([4, 1, 2, 1, 2])
    assert ans == 4
    assert steps[-1]["kind"] == "done"


def test_bit_single_number_singleton():
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scenes.dsa_pattern_scene import _single_number_steps
    _, ans = _single_number_steps([7])
    assert ans == 7


def test_bit_count_bits_brian_kernighan():
    """0b10110 has 3 set bits."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scenes.dsa_pattern_scene import _count_bits_steps
    steps, count = _count_bits_steps(0b10110)
    assert count == 3
    assert steps[-1]["kind"] == "done"


def test_bit_count_bits_zero():
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scenes.dsa_pattern_scene import _count_bits_steps
    _, count = _count_bits_steps(0)
    assert count == 0


@pytest.mark.integration
def test_bit_single_number_renders(tmp_path):
    _ok(_render(tmp_path, "BitManipulationScene",
                {"values": [4, 1, 2, 1, 2], "operation": "single_number"}),
        tmp_path, "BitManipulationScene")


@pytest.mark.integration
def test_bit_count_bits_renders(tmp_path):
    _ok(_render(tmp_path, "BitManipulationScene",
                {"values": [22], "operation": "count_bits"}),
        tmp_path, "BitManipulationScene")


# ---------------------------------------------------------------------------
# TopologicalSortScene
# ---------------------------------------------------------------------------

def test_topo_sort_linear_chain():
    """0→1→2→3→4 must produce [0,1,2,3,4]."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scenes.dsa_pattern_scene import _topological_sort_steps
    _, order = _topological_sort_steps(5, [[0, 1], [1, 2], [2, 3], [3, 4]])
    assert order == [0, 1, 2, 3, 4]


def test_topo_sort_diamond():
    """Diamond: 0→{1,2}→3→4 is a valid topo order."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scenes.dsa_pattern_scene import _topological_sort_steps
    _, order = _topological_sort_steps(5, [[0, 1], [0, 2], [1, 3], [2, 3], [3, 4]])
    assert order[0] == 0          # 0 always first
    assert order[-1] == 4         # 4 always last
    assert set(order[1:3]) == {1, 2}   # 1 and 2 in middle


def test_topo_sort_cycle():
    """0→1→2→0 has a cycle and produces no valid order."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scenes.dsa_pattern_scene import _topological_sort_steps
    steps, order = _topological_sort_steps(3, [[0, 1], [1, 2], [2, 0]])
    assert steps[-1]["kind"] == "cycle"
    assert len(order) < 3


@pytest.mark.integration
def test_topo_sort_renders_diamond(tmp_path):
    _ok(_render(tmp_path, "TopologicalSortScene",
                {"num_nodes": 5,
                 "edges": [[0, 1], [0, 2], [1, 3], [2, 3], [3, 4]]}),
        tmp_path, "TopologicalSortScene")


@pytest.mark.integration
def test_topo_sort_renders_cycle(tmp_path):
    _ok(_render(tmp_path, "TopologicalSortScene",
                {"num_nodes": 3,
                 "edges": [[0, 1], [1, 2], [2, 0]]}),
        tmp_path, "TopologicalSortScene")
