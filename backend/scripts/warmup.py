"""Warm up the Lumen lesson cache by rendering every topic in TOPIC_SCENE_MAP.

Sequential. stdlib only. Backend dedupes via content-hash cache, so already-cached
entries return ~immediately.
"""
import json
import sys
import time
import urllib.request
import urllib.error

BACKEND = "http://localhost:5000"
POLL_INTERVAL_S = 2.0
TIMEOUT_S = 240.0
RETRIES = 2  # extra retries on top of first attempt
RETRY_SLEEP_S = 5.0

# Mirrored from frontend/src/App.tsx TOPIC_SCENE_MAP
TOPICS = {
    # Sorting
    "bubble-sort": {"scene": "bubble_sort", "params": {"array": [5, 3, 8, 1, 9, 2]}},
    "merge-sort": {"scene": "merge_sort", "params": {"array": [5, 2, 8, 1, 9, 3, 7, 4]}},
    "quick-sort": {"scene": "quick_sort", "params": {"array": [3, 7, 1, 5, 9, 2, 8, 4]}},

    # Searching
    "binary-search": {
        "scene": "binary_search_index",
        "params": {"array": [1, 3, 5, 7, 9, 11, 13, 15], "algorithm": "find_target", "target": 7},
    },
    "binary-search-answer": {
        "scene": "binary_search_answer",
        "params": {"min_value": 1, "max_value": 16, "true_at": 7, "predicate_label": "feasible(x)"},
    },

    # Two pointers
    "two-pointers": {
        "scene": "two_pointers_opposite",
        "params": {"array": [1, 3, 5, 7, 9, 11], "algorithm": "two_sum_sorted", "target": 12},
    },
    "two-pointers-fast-slow": {
        "scene": "two_pointers_same_dir",
        "params": {"array": [1, 1, 2, 3, 3, 4, 5], "algorithm": "remove_duplicates"},
    },
    "palindrome": {
        "scene": "two_pointers_opposite",
        "params": {"array": ["r", "a", "c", "e", "c", "a", "r"], "algorithm": "palindrome"},
    },
    "container-water": {
        "scene": "two_pointers_opposite",
        "params": {"array": [1, 8, 6, 2, 5, 4, 8, 3], "algorithm": "container_water"},
    },

    # Sliding window
    "sliding-window": {
        "scene": "sliding_window_variable",
        "params": {"array": ["a", "b", "c", "a", "b", "c", "b", "b"], "algorithm": "longest_no_repeat"},
    },

    # Hashing
    "two-sum": {
        "scene": "hashmap_iteration",
        "params": {"array": [2, 7, 11, 15], "algorithm": "two_sum_hashmap", "target": 9},
    },
    "frequency-count": {
        "scene": "hashmap_iteration",
        "params": {"array": [1, 2, 2, 3, 1, 2, 4], "algorithm": "frequency_count"},
    },
    "anagram-check": {
        "scene": "hashmap_iteration",
        "params": {"array": ["l", "i", "s", "t", "e", "n"], "algorithm": "anagram_check"},
    },

    # Stacks & queues
    "monotonic-stack": {
        "scene": "monotonic_stack",
        "params": {"array": [2, 1, 4, 3, 5], "algorithm": "next_greater", "monotone": "decreasing"},
    },
    "stack-queue": {
        "scene": "stack_queue",
        "params": {
            "operations": ["push 3", "push 7", "push 1", "pop", "push 5", "pop"],
            "structure": "stack",
        },
    },

    # Prefix / running sums
    "prefix-sum": {
        "scene": "prefix_sum",
        "params": {"array": [3, 1, 4, 1, 5, 9, 2, 6], "algorithm": "build_prefix"},
    },
    "kadanes": {
        "scene": "kadanes",
        "params": {"array": [-2, 1, -3, 4, -1, 2, 1, -5, 4]},
    },

    # Linked lists
    "reverse-linked-list": {
        "scene": "linked_list",
        "params": {"values": [1, 2, 3, 4, 5], "algorithm": "reverse"},
    },
    "linked-list-middle": {
        "scene": "linked_list",
        "params": {"values": [1, 2, 3, 4, 5, 6], "algorithm": "find_middle"},
    },
    "merge-sorted-lists": {
        "scene": "linked_list",
        "params": {"values": [1, 3, 5], "values2": [2, 4, 6], "algorithm": "merge_sorted"},
    },

    # Trees
    "tree-bfs": {
        "scene": "tree_traversal",
        "params": {"values": [1, 2, 3, 4, 5, 6, 7], "algorithm": "bfs"},
    },
    "tree-dfs": {
        "scene": "tree_traversal",
        "params": {"values": [1, 2, 3, 4, 5, 6, 7], "algorithm": "dfs"},
    },
    "tree-inorder": {
        "scene": "tree_traversal",
        "params": {"values": [1, 2, 3, 4, 5, 6, 7], "algorithm": "inorder"},
    },
    "trie": {
        "scene": "trie_ops",
        "params": {"words": ["cat", "car", "card", "care"], "queries": ["car", "cap"]},
    },

    # Graphs
    "graph-bfs": {
        "scene": "graph_traversal",
        "params": {
            "num_nodes": 6,
            "edges": [[0, 1], [0, 2], [1, 3], [2, 4], [3, 5], [4, 5]],
            "start_node": 0,
            "algorithm": "bfs",
            "directed": False,
        },
    },
    "graph-dfs": {
        "scene": "graph_traversal",
        "params": {
            "num_nodes": 6,
            "edges": [[0, 1], [0, 2], [1, 3], [2, 4], [3, 5], [4, 5]],
            "start_node": 0,
            "algorithm": "dfs",
            "directed": False,
        },
    },
    "dijkstra": {
        "scene": "dijkstra",
        "params": {
            "num_nodes": 5,
            "edges": [[0, 1, 4], [0, 2, 1], [2, 1, 2], [1, 3, 1], [2, 3, 5], [3, 4, 3]],
            "source": 0,
        },
    },
    "union-find": {
        "scene": "union_find",
        "params": {
            "n": 6,
            "operations": ["union 0 1", "union 2 3", "union 4 5", "union 1 3", "find 4"],
        },
    },

    # Grid
    "grid-bfs": {
        "scene": "grid_traversal",
        "params": {
            "grid": [[0, 0, 0, 1], [1, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 0]],
            "start": [0, 0],
            "target": [3, 3],
            "algorithm": "bfs",
        },
    },

    # Heaps
    "heap-ops": {
        "scene": "heap_ops",
        "params": {
            "operations": ["push 5", "push 3", "push 8", "push 1", "pop", "push 7", "pop"],
            "heap_type": "min",
        },
    },

    # Intervals
    "merge-intervals": {
        "scene": "interval_merging",
        "params": {"intervals": [[1, 3], [2, 6], [8, 10], [15, 18]]},
    },

    # DP (1D)
    "fibonacci-dp": {"scene": "dp_array", "params": {"algorithm": "fibonacci", "n": 8}},
    "climbing-stairs": {"scene": "dp_array", "params": {"algorithm": "climbing_stairs", "n": 8}},
    "house-robber": {"scene": "dp_array", "params": {"algorithm": "house_robber", "n": 8}},

    # DP (2D)
    "lcs": {
        "scene": "dp_2d",
        "params": {"algorithm": "lcs", "input1": "abcde", "input2": "ace"},
    },
    "edit-distance": {
        "scene": "dp_2d",
        "params": {"algorithm": "edit_distance", "input1": "kitten", "input2": "sitting"},
    },
    "unique-paths": {
        "scene": "dp_2d",
        "params": {"algorithm": "unique_paths", "input1": "3", "input2": "3"},
    },

    # Backtracking
    "subsets": {
        "scene": "backtracking_subsets",
        "params": {"array": [1, 2, 3], "algorithm": "subsets"},
    },
    "permutations": {
        "scene": "backtracking_subsets",
        "params": {"array": [1, 2, 3], "algorithm": "permutations"},
    },

    # Design
    "lru-cache": {
        "scene": "lru_cache",
        "params": {
            "operations": ["put 1 a", "put 2 b", "get 1", "put 3 c", "get 2"],
            "capacity": 2,
        },
    },
    "segment-tree": {
        "scene": "segment_tree",
        "params": {"array": [1, 3, 5, 7, 9, 11], "queries": [[1, 3], [0, 5], [2, 4]]},
    },

    # Calculus
    "chain-rule": {
        "scene": "tangent_line",
        "params": {"expression": "(2*x + 1)**2", "x_point": 1, "domain": [-2, 2]},
    },
    "derivative-power-rule": {
        "scene": "tangent_line",
        "params": {"expression": "x**3", "x_point": 1, "domain": [-2, 2]},
    },
    "limit": {
        "scene": "limit",
        "params": {"expression": "sin(x)/x", "limit_point": 0, "domain": [-3, 3]},
    },
    "critical-points": {
        "scene": "critical_points",
        "params": {"expression": "x**3 - 3*x", "domain": [-2.5, 2.5]},
    },
    "riemann-sum": {
        "scene": "riemann_sum",
        "params": {"expression": "x**2", "domain": [0, 2], "n": 6, "method": "left"},
    },
    "ftc": {
        "scene": "ftc",
        "params": {"expression": "x**2", "domain": [0, 3], "start": 0},
    },
    "area-between-curves": {
        "scene": "area_between_curves",
        "params": {"f_expression": "x", "g_expression": "x**2", "domain": [0, 1]},
    },
    "average-value": {
        "scene": "average_value",
        "params": {"expression": "sin(x)", "domain": [0, 3.14159]},
    },
    "arc-length": {
        "scene": "arc_length",
        "params": {"expression": "x**2", "domain": [0, 2], "n_segments": 8},
    },
    "u-substitution": {
        "scene": "u_substitution",
        "params": {"expression": "2*x*(x**2 + 1)**3", "u_expression": "x**2 + 1", "domain": [0, 2]},
    },
    "integration-by-parts": {
        "scene": "integration_by_parts",
        "params": {"u_expression": "x", "dv_expression": "exp(x)", "domain": [0, 2]},
    },
    "improper-integral": {
        "scene": "improper_integral",
        "params": {"expression": "1/(x**2)", "domain": [1, 10], "improper_bound": "right"},
    },
    "volume-revolution": {
        "scene": "volume_revolution",
        "params": {"expression": "x**2", "domain": [0, 2], "n_disks": 8},
    },
    "washer-method": {
        "scene": "washer_method",
        "params": {
            "f_expression": "x**2",
            "g_expression": "0",
            "domain": [0, 2],
            "n_washers": 8,
        },
    },
    "shell-method": {
        "scene": "shell_method",
        "params": {"expression": "x**2", "domain": [0, 2], "n_shells": 8},
    },
    "cross-section": {
        "scene": "cross_section",
        "params": {"expression": "sqrt(x)", "domain": [0, 4], "shape": "square"},
    },
    "taylor-series": {
        "scene": "taylor_series",
        "params": {"expression": "sin(x)", "center": 0, "max_terms": 5, "domain": [-3, 3]},
    },
    "sequence": {
        "scene": "sequence",
        "params": {"formula": "x/2 + 1", "a0": 0, "n_terms": 8},
    },
    "cobweb": {
        "scene": "cobweb",
        "params": {"formula": "0.7*x + 0.5", "a0": 0.1, "n_steps": 8, "domain": [0, 2]},
    },

    # Algebra
    "linear-function": {
        "scene": "linear_function",
        "params": {"expression": "2*x + 1", "domain": [-5, 5]},
    },
    "quadratic": {
        "scene": "quadratic",
        "params": {"expression": "x**2 - 4*x + 3", "domain": [-1, 5]},
    },
    "inequality": {
        "scene": "inequality",
        "params": {"expression": "x**2 - 4", "domain": [-5, 5]},
    },
    "exponential-function": {
        "scene": "exponential",
        "params": {"expression": "exp(x)", "domain": [-3, 3], "show_key_points": True},
    },
    "function-transformation": {
        "scene": "transformation",
        "params": {
            "base_expression": "x**2",
            "transformed_expression": "(x - 2)**2 + 1",
            "domain": [-3, 5],
        },
    },

    # Arithmetic
    "fraction": {
        "scene": "fraction",
        "params": {"mode": "compare", "fractions": [[1, 4], [2, 4], [3, 4]]},
    },

    # Trig
    "trig-unit-circle": {
        "scene": "trig_unit_circle",
        "params": {"angle": 0.785, "animate_rotation": True},
    },

    # 3D / Multivariable
    "surface-plot": {
        "scene": "surface_plot",
        "params": {"expression": "x**2 + y**2", "x_domain": [-2, 2], "y_domain": [-2, 2]},
    },
    "contour": {
        "scene": "contour",
        "params": {
            "expression": "x**2 + y**2",
            "x_domain": [-3, 3],
            "y_domain": [-3, 3],
            "num_levels": 8,
        },
    },
    "vector-field": {
        "scene": "vector_field",
        "params": {
            "x_expression": "-y",
            "y_expression": "x",
            "domain": [-2, 2],
            "show_streamlines": False,
        },
    },
    "partial-derivative": {
        "scene": "partial_derivative",
        "params": {
            "expression": "x**2 + y**2",
            "variable": "x",
            "fixed_value": 0,
            "x_domain": [-2, 2],
            "y_domain": [-2, 2],
        },
    },
}


def http_post_json(url, payload, timeout=15):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def http_get_json(url, timeout=15):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def render_topic(topic_id, scene, params):
    """Submit one render and poll until done. Returns (status, elapsed_s, detail)."""
    full_params = dict(params)
    full_params["caption"] = topic_id
    payload = {"scene": scene, "params": full_params}

    started = time.time()
    resp = http_post_json(f"{BACKEND}/render", payload)
    job_id = resp.get("job_id")
    if not job_id:
        return ("error", time.time() - started, f"no job_id: {resp!r}")

    deadline = started + TIMEOUT_S
    while time.time() < deadline:
        try:
            s = http_get_json(f"{BACKEND}/status/{job_id}")
        except urllib.error.URLError as e:
            return ("error", time.time() - started, f"status fetch failed: {e}")
        st = s.get("status")
        if st == "done":
            return ("ok", time.time() - started, s.get("video_url", ""))
        if st == "error":
            return ("error", time.time() - started, s.get("error", "unknown error"))
        time.sleep(POLL_INTERVAL_S)
    return ("timeout", time.time() - started, f"timed out after {TIMEOUT_S}s (job_id={job_id})")


def main():
    succeeded = []
    failed = []
    total = len(TOPICS)
    print(f"Warming up {total} topics against {BACKEND}", flush=True)
    print("=" * 60, flush=True)

    for i, (topic_id, entry) in enumerate(TOPICS.items(), 1):
        scene = entry["scene"]
        params = entry["params"]
        attempt = 0
        last_detail = ""
        last_status = ""
        last_elapsed = 0.0
        while attempt <= RETRIES:
            try:
                status, elapsed, detail = render_topic(topic_id, scene, params)
            except urllib.error.URLError as e:
                status, elapsed, detail = ("error", 0.0, f"connection error: {e}")
            except Exception as e:  # noqa: BLE001
                status, elapsed, detail = ("error", 0.0, f"exception: {e!r}")
            last_status, last_elapsed, last_detail = status, elapsed, detail
            if status == "ok":
                break
            attempt += 1
            if attempt <= RETRIES:
                time.sleep(RETRY_SLEEP_S)

        if last_status == "ok":
            mark = "OK "
            succeeded.append(topic_id)
        elif last_status == "timeout":
            mark = "TO "
            failed.append((topic_id, "timeout"))
        else:
            mark = "ERR"
            failed.append((topic_id, last_detail))

        print(
            f"[{i:>3}/{total}] {mark} {topic_id} ({last_elapsed:.1f}s)"
            + (f"  -- {last_detail}" if last_status != "ok" else ""),
            flush=True,
        )

    print("=" * 60, flush=True)
    print(f"Summary: {len(succeeded)} succeeded, {len(failed)} failed", flush=True)
    if failed:
        print("Failures:", flush=True)
        for tid, reason in failed:
            print(f"  - {tid}: {reason}", flush=True)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
