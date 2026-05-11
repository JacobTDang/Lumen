import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

_jobs: dict = {}

# ---------------------------------------------------------------------------
# Quality settings
#
# Set LUMEN_QUALITY=low|medium|high to override (defaults to "low" — 480p15,
# the fastest tier). Each tier is ~3-4x slower than the previous to render.
# 480p is comfortably legible for the educational scenes we ship; bump it up
# only if you're exporting for high-DPI screens or recording a final video.
# ---------------------------------------------------------------------------
_QUALITY_TIERS = {
    "low":    ("-ql", "480p15"),
    "medium": ("-qm", "720p30"),
    "high":   ("-qh", "1080p60"),
}
_QUALITY_2D = _QUALITY_TIERS.get(
    os.environ.get("LUMEN_QUALITY", "medium").lower(),
    _QUALITY_TIERS["medium"],
)
_QUALITY_FLAG_2D, _QUALITY_DIR_2D = _QUALITY_2D
# 3D scenes always render at low — surface plots are an order of magnitude
# slower than 2D scenes and benefit much less from a resolution bump.
_QUALITY_FLAG_3D, _QUALITY_DIR_3D = _QUALITY_TIERS["low"]
_3D_SCENES = {"surface_plot", "partial_derivative"}

SCENE_REGISTRY = {
    # Core
    "bubble_sort":        ("scenes/array_scene.py",       "BubbleSortScene"),
    "merge_sort":         ("scenes/array_scene.py",       "MergeSortScene"),
    "quick_sort":         ("scenes/array_scene.py",       "QuickSortScene"),
    # Calculus
    "function_plot":      ("scenes/calculus_scene.py",    "FunctionPlotScene"),
    "limit":              ("scenes/calculus_scene.py",    "LimitScene"),
    "tangent_line":       ("scenes/calculus_scene.py",    "TangentLineScene"),
    "secant_line":        ("scenes/calculus_scene.py",    "SecantLineScene"),
    "riemann_sum":        ("scenes/calculus_scene.py",    "RiemannSumScene"),
    "critical_points":    ("scenes/calculus_scene.py",    "CriticalPointsScene"),
    "volume_revolution":  ("scenes/calculus_scene.py",    "VolumeRevolutionScene"),
    "taylor_series":      ("scenes/calculus_scene.py",    "TaylorSeriesScene"),
    "ftc":                ("scenes/calculus_scene.py",    "FTCScene"),
    "sequence":           ("scenes/calculus_scene.py",    "SequenceScene"),
    "cobweb":             ("scenes/calculus_scene.py",    "CobwebScene"),
    "area_between_curves": ("scenes/calculus_scene.py",  "AreaBetweenCurvesScene"),
    "washer_method":       ("scenes/calculus_scene.py",  "WasherMethodScene"),
    "shell_method":        ("scenes/calculus_scene.py",  "ShellMethodScene"),
    "arc_length":          ("scenes/calculus_scene.py",  "ArcLengthScene"),
    "average_value":       ("scenes/calculus_scene.py",  "AverageValueScene"),
    "u_substitution":      ("scenes/calculus_scene.py",  "USubstitutionScene"),
    "integration_by_parts":("scenes/calculus_scene.py",  "IntegrationByPartsScene"),
    "improper_integral":   ("scenes/calculus_scene.py",  "ImproperIntegralScene"),
    "cross_section":       ("scenes/calculus_scene.py",  "CrossSectionScene"),
    # Algebra
    "linear_function":    ("scenes/algebra_scene.py",     "LinearFunctionScene"),
    "quadratic":          ("scenes/algebra_scene.py",     "QuadraticScene"),
    "inequality":         ("scenes/algebra_scene.py",     "InequalityScene"),
    "exponential":        ("scenes/algebra_scene.py",     "ExponentialScene"),
    "transformation":     ("scenes/algebra_scene.py",     "TransformationScene"),
    # DSA — legacy (monolithic, kept for backwards compatibility)
    "array_pointer":   ("scenes/dsa_scene.py", "ArrayPointerScene"),
    "sliding_window":  ("scenes/dsa_scene.py", "SlidingWindowScene"),
    "linked_list":     ("scenes/dsa_scene.py", "LinkedListScene"),
    "tree_traversal":  ("scenes/dsa_scene.py", "TreeTraversalScene"),
    "graph_traversal": ("scenes/dsa_scene.py", "GraphScene"),
    "dp_array":        ("scenes/dsa_scene.py", "DPArrayScene"),
    "stack_queue":     ("scenes/dsa_scene.py", "StackQueueScene"),
    # DSA — pattern-specific (primitive-based)
    "two_pointers_opposite":   ("scenes/dsa_pattern_scene.py", "TwoPointersOppositeScene"),
    "two_pointers_same_dir":   ("scenes/dsa_pattern_scene.py", "TwoPointersSameDirScene"),
    "sliding_window_variable": ("scenes/dsa_pattern_scene.py", "SlidingWindowVariableScene"),
    "binary_search_index":     ("scenes/dsa_pattern_scene.py", "BinarySearchIndexScene"),
    "binary_search_answer":    ("scenes/dsa_pattern_scene.py", "BinarySearchAnswerScene"),
    "monotonic_stack":         ("scenes/dsa_pattern_scene.py", "MonotonicStackScene"),
    "hashmap_iteration":       ("scenes/dsa_pattern_scene.py", "HashMapIterationScene"),
    "prefix_sum":              ("scenes/dsa_pattern_scene.py", "PrefixSumScene"),
    # DSA — extended pattern scenes (advanced LeetCode coverage)
    "kadanes":                 ("scenes/dsa_pattern_scene.py", "KadanesScene"),
    "interval_merging":        ("scenes/dsa_pattern_scene.py", "IntervalMergingScene"),
    "backtracking_subsets":    ("scenes/dsa_pattern_scene.py", "BacktrackingSubsetsScene"),
    "lru_cache":               ("scenes/dsa_pattern_scene.py", "LRUCacheScene"),
    "grid_traversal":          ("scenes/dsa_pattern_scene.py", "GridTraversalScene"),
    "heap_ops":                ("scenes/dsa_pattern_scene.py", "HeapOpsScene"),
    "dp_2d":                   ("scenes/dsa_pattern_scene.py", "DP2DScene"),
    "trie_ops":                ("scenes/dsa_pattern_scene.py", "TrieOpsScene"),
    "union_find":              ("scenes/dsa_pattern_scene.py", "UnionFindScene"),
    "dijkstra":                ("scenes/dsa_pattern_scene.py", "DijkstraScene"),
    "segment_tree":            ("scenes/dsa_pattern_scene.py", "SegmentTreeScene"),
    # DSA — Phase 7 (visual depth + 7 missing patterns)
    "floyd_cycle":             ("scenes/dsa_pattern_scene.py", "FloydCycleScene"),
    "trapping_rain_water":     ("scenes/dsa_pattern_scene.py", "TrappingRainWaterScene"),
    "greedy_interval":         ("scenes/dsa_pattern_scene.py", "GreedyIntervalScene"),
    "bit_manipulation":        ("scenes/dsa_pattern_scene.py", "BitManipulationScene"),
    "topological_sort":        ("scenes/dsa_pattern_scene.py", "TopologicalSortScene"),
    "matrix_rotation":         ("scenes/dsa_pattern_scene.py", "MatrixRotationScene"),
    "recursion_tree_dc":       ("scenes/dsa_pattern_scene.py", "RecursionTreeDCScene"),
    # Arithmetic
    "number_line":        ("scenes/arithmetic_scene.py",  "NumberLineScene"),
    "fraction":           ("scenes/arithmetic_scene.py",  "FractionScene"),
    "area_model":         ("scenes/arithmetic_scene.py",  "AreaModelScene"),
    # Trig
    "trig_unit_circle":   ("scenes/trig_scene.py",        "TrigUnitCircleScene"),
    # 3D / Calc 3
    "surface_plot":       ("scenes/threed_scene.py",      "SurfacePlotScene"),
    "contour":            ("scenes/threed_scene.py",      "ContourScene"),
    "vector_field":       ("scenes/threed_scene.py",      "VectorFieldScene"),
    "partial_derivative": ("scenes/threed_scene.py",      "PartialDerivativeScene"),
    # Dynamic tool-composed scenes (Lesson Director agent)
    "dynamic_lesson_step": ("scenes/tool_executor.py",    "DynamicScene"),
}

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MEDIA_DIR   = os.path.join(_BACKEND_DIR, "media")
_TEMP_DIR    = os.path.join(_MEDIA_DIR,   "temp")
_LESSONS_DIR = os.path.join(_MEDIA_DIR,   "lessons")
_CACHE_INDEX = os.path.join(_LESSONS_DIR, "cache_index.json")
_CACHE_LOCK  = threading.Lock()


# ---------------------------------------------------------------------------
# Lesson render cache
# ---------------------------------------------------------------------------

def _lesson_cache_key(steps: list) -> str:
    """Build a deterministic md5 hash from each step's tool + params.

    Captions are excluded — they only affect the on-screen text, not the
    rendered video bytes that we'd be reusing.
    """
    payload = [{"tool": s.tool, "params": s.params} for s in steps]
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.md5(serialized.encode("utf-8")).hexdigest()


def _load_cache_index() -> dict:
    if not os.path.exists(_CACHE_INDEX):
        return {}
    try:
        with open(_CACHE_INDEX) as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache_index(index: dict) -> None:
    os.makedirs(_LESSONS_DIR, exist_ok=True)
    with open(_CACHE_INDEX, "w") as fh:
        json.dump(index, fh, indent=2, sort_keys=True)


def _cache_lookup(cache_key: str) -> str | None:
    """Return cached URL if present AND the underlying file still exists."""
    with _CACHE_LOCK:
        index = _load_cache_index()
        url = index.get(cache_key)
        if url is None:
            return None
        full_path = os.path.join(_MEDIA_DIR, url.removeprefix("/media/"))
        if not os.path.exists(full_path):
            # Stale entry — drop it so future runs re-render
            index.pop(cache_key, None)
            _save_cache_index(index)
            return None
        return url


def _cache_store(cache_key: str, url: str) -> None:
    with _CACHE_LOCK:
        index = _load_cache_index()
        index[cache_key] = url
        _save_cache_index(index)


# ---------------------------------------------------------------------------
# Media cleanup
# ---------------------------------------------------------------------------

def cleanup_old_jobs(max_age_seconds: int = 3600) -> int:
    """Delete media/jobs/<dir>/ older than max_age_seconds (by mtime).

    media/lessons/ is handled separately by cleanup_old_lessons since those
    files are referenced from the cache index and may still be served.
    Returns the number of directories removed.
    """
    jobs_dir = os.path.join(_MEDIA_DIR, "jobs")
    if not os.path.isdir(jobs_dir):
        return 0

    now     = time.time()
    cutoff  = now - max_age_seconds
    removed = 0
    for entry in os.listdir(jobs_dir):
        path = os.path.join(jobs_dir, entry)
        if not os.path.isdir(path):
            continue
        try:
            if os.path.getmtime(path) < cutoff:
                shutil.rmtree(path, ignore_errors=True)
                removed += 1
        except OSError:
            continue
    return removed


def cleanup_old_lessons(max_count: int = 200, min_age_seconds: int = 120) -> int:
    """LRU eviction over media/lessons/*.mp4: keep at most max_count files
    (oldest first by mtime). Two protections:

    1. Files referenced in the cache index are NEVER deleted. Cached lessons
       represent intentional pre-renders (e.g., demo showcase prompts) — they
       trade disk for instant playback and shouldn't be evicted under
       routine cleanup.
    2. Files newer than min_age_seconds are also protected to avoid racing
       in-flight renders.

    Returns count removed.
    """
    if not os.path.isdir(_LESSONS_DIR):
        return 0

    # Collect cache-referenced file paths (these are sacred).
    with _CACHE_LOCK:
        index = _load_cache_index()
    pinned = {os.path.realpath(os.path.join(_MEDIA_DIR, url.removeprefix("/media/")))
              for url in index.values()}

    files = []
    for entry in os.listdir(_LESSONS_DIR):
        if not entry.endswith(".mp4"):
            continue
        path = os.path.join(_LESSONS_DIR, entry)
        if os.path.realpath(path) in pinned:
            continue
        try:
            files.append((os.path.getmtime(path), path))
        except OSError:
            continue

    if len(files) <= max_count:
        return 0

    files.sort()   # oldest first
    cutoff = time.time() - min_age_seconds
    excess = len(files) - max_count
    removed = 0
    for mtime, path in files:
        if removed >= excess:
            break
        if mtime > cutoff:
            continue   # too fresh — protect
        try:
            os.remove(path)
            removed += 1
        except OSError:
            continue
    return removed


# ---------------------------------------------------------------------------
# Single-scene API
# ---------------------------------------------------------------------------

def submit_render(scene_type: str, params: dict) -> str:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending", "url": None, "error": None,
                     "progress": 0.0, "stage": "queued"}
    threading.Thread(
        target=_run_render, args=(job_id, scene_type, params), daemon=True,
    ).start()
    return job_id


def get_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)


# Manim's tqdm progress bar emits lines like:
#   "Animation 0:  42%|████▏      | 10/24 [00:00<00:01, ...]"
# We track the most recent (animation_idx, frac_in_anim) and combine with the
# total animations seen so far to estimate overall job progress.
_TQDM_RE = re.compile(r"Animation\s+(\d+):\s*(\d+)%\|")


def _stream_progress(stderr, job_id: str, on_done: list):
    """Read stderr line-by-line; whenever a tqdm progress line shows up,
    update the job's `progress` field. Best-effort — manim's output format
    can change between versions, in which case progress just stays at 0."""
    last_anim   = -1
    max_anim    = 0
    err_buf: list[str] = []
    try:
        for raw in iter(stderr.readline, ""):
            line = raw.rstrip("\n")
            if not line:
                continue
            err_buf.append(line)
            if len(err_buf) > 200:
                err_buf = err_buf[-200:]   # cap memory
            m = _TQDM_RE.search(line)
            if m:
                anim_idx = int(m.group(1))
                pct      = int(m.group(2)) / 100.0
                if anim_idx > max_anim:
                    max_anim = anim_idx
                last_anim = anim_idx
                # Estimate overall progress: completed anims + current anim's
                # fraction, divided by max_anim+1 (the highest seen). Asymptotic
                # because we don't know total animations until the end.
                total = max(max_anim + 1, last_anim + 1)
                overall = (last_anim + pct) / total
                # Cap at 95% — leave the last 5% for the file-write phase
                _jobs[job_id]["progress"] = min(0.95, overall)
    except Exception:
        pass
    finally:
        on_done.append("\n".join(err_buf[-50:]))


def _run_render(job_id: str, scene_type: str, params: dict):
    if scene_type not in SCENE_REGISTRY:
        _jobs[job_id] = {"status": "error", "url": None,
                         "error": f"unknown scene type: {scene_type}",
                         "progress": 0.0, "stage": "error"}
        return

    # Mark this single-scene job as actively rendering.
    if job_id in _jobs:
        _jobs[job_id]["stage"] = "rendering"

    os.makedirs(_TEMP_DIR, exist_ok=True)
    params_path = os.path.join(_TEMP_DIR, f"{job_id}.json")

    is_3d         = scene_type in _3D_SCENES
    quality_flag  = _QUALITY_FLAG_3D if is_3d else _QUALITY_FLAG_2D
    quality_dir   = _QUALITY_DIR_3D  if is_3d else _QUALITY_DIR_2D
    job_media_dir = os.path.join(_MEDIA_DIR, "jobs", job_id)
    os.makedirs(job_media_dir, exist_ok=True)

    proc = None
    try:
        with open(params_path, "w") as f:
            json.dump(params, f)

        scene_file, scene_class = SCENE_REGISTRY[scene_type]

        # IMPORTANT: stdout MUST be DEVNULL (or actively read in a thread).
        # Manim writes occasional info to stdout; if we capture it via PIPE
        # but never drain it, the OS pipe buffer fills (~64KB) and manim
        # blocks on its next print, deadlocking the entire render.
        proc = subprocess.Popen(
            [sys.executable, "-u", "-m", "manim", quality_flag,
             "--media_dir", job_media_dir,
             "--disable_caching", scene_file, scene_class],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True, bufsize=1, cwd=_BACKEND_DIR,
            env={**os.environ, "MANIM_JOB_ID": job_id, "MANIM_TEMP_DIR": _TEMP_DIR},
        )

        err_capture: list = []
        stderr_thread = threading.Thread(
            target=_stream_progress, args=(proc.stderr, job_id, err_capture), daemon=True,
        )
        stderr_thread.start()

        try:
            proc.wait(timeout=180)
        except subprocess.TimeoutExpired:
            proc.kill()
            _jobs[job_id] = {"status": "error", "url": None,
                             "error": "render timed out after 180s",
                             "progress": _jobs[job_id].get("progress", 0.0),
                             "stage": "error"}
            return

        # Drain remaining stderr
        stderr_thread.join(timeout=2.0)
        err_tail = err_capture[0] if err_capture else ""

        if proc.returncode != 0:
            _jobs[job_id] = {"status": "error", "url": None,
                             "error": err_tail[-500:] or f"exit {proc.returncode}",
                             "progress": _jobs[job_id].get("progress", 0.0),
                             "stage": "error"}
            return

        scene_stem = os.path.splitext(os.path.basename(scene_file))[0]
        video_rel  = f"jobs/{job_id}/videos/{scene_stem}/{quality_dir}/{scene_class}.mp4"
        full_path  = os.path.join(_MEDIA_DIR, video_rel)

        if not os.path.exists(full_path):
            _jobs[job_id] = {"status": "error", "url": None,
                             "error": "output file not found after render",
                             "progress": _jobs[job_id].get("progress", 0.0),
                             "stage": "error"}
            return

        _jobs[job_id] = {"status": "done", "url": f"/media/{video_rel}",
                         "error": None, "progress": 1.0, "stage": "done"}

    except Exception as e:
        if proc is not None:
            try: proc.kill()
            except Exception: pass
        _jobs[job_id] = {"status": "error", "url": None, "error": str(e),
                         "progress": _jobs[job_id].get("progress", 0.0),
                         "stage": "error"}
    finally:
        if os.path.exists(params_path):
            os.remove(params_path)


# ---------------------------------------------------------------------------
# Multi-scene lesson API  (parallel rendering)
# ---------------------------------------------------------------------------

def submit_lesson(steps: list) -> str:
    lesson_id = str(uuid.uuid4())
    _jobs[lesson_id] = {"status": "pending", "url": None, "error": None,
                        "progress": 0.0, "stage": "queued"}
    threading.Thread(
        target=_run_lesson, args=(lesson_id, steps), daemon=True,
    ).start()
    return lesson_id


def _aggregate_progress(lesson_id: str, step_job_ids: list, stop_event: threading.Event):
    """Background ticker that averages step progress into the lesson job's
    progress field while the lesson is still rendering.

    Also updates the lesson's stage to ``rendering_X_of_N`` based on how many
    step jobs have completed so the frontend can show meaningful progress.
    """
    n = len(step_job_ids)
    while not stop_event.is_set():
        try:
            progresses = [
                _jobs.get(sid, {}).get("progress", 0.0) for sid in step_job_ids
            ]
            done_count = sum(
                1 for sid in step_job_ids
                if _jobs.get(sid, {}).get("status") == "done"
            )
            # "Currently rendering" is the (done_count+1)th, clamped to N.
            current_idx = min(done_count + 1, n)
            if progresses:
                avg = sum(progresses) / len(progresses)
                cur = _jobs.get(lesson_id, {})
                if cur.get("status") == "pending":
                    cur["progress"] = min(0.95, avg)
                    cur["stage"] = f"rendering_{current_idx}_of_{n}"
        except Exception:
            pass
        stop_event.wait(0.25)


def stitch_videos(paths: list[str], out: str):
    filelist_path = out + ".txt"
    with open(filelist_path, "w") as fh:
        fh.write("\n".join(f"file '{p}'" for p in paths))
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", filelist_path, "-c", "copy", out],
        check=True, capture_output=True, text=True, timeout=60,
    )
    os.remove(filelist_path)


def _run_lesson(lesson_id: str, steps: list):
    # Lazy housekeeping — drop old per-job render dirs and cap lessons/ size
    # so media/ doesn't grow unboundedly during normal usage. Failures here
    # must not block a render.
    try:
        cleanup_old_jobs()
        cleanup_old_lessons()
    except Exception:
        pass

    # Cache check — identical (tool, params) sequence → reuse stitched video
    cache_key   = _lesson_cache_key(steps)
    cached_url  = _cache_lookup(cache_key)
    if cached_url is not None:
        _jobs[lesson_id] = {"status": "done", "url": cached_url, "error": None,
                            "progress": 1.0, "stage": "done"}
        return

    # Pre-allocate step job IDs so the progress aggregator can track them
    # before each step actually starts running.
    step_job_ids = [str(uuid.uuid4()) for _ in steps]
    for sid in step_job_ids:
        _jobs[sid] = {"status": "pending", "url": None, "error": None,
                      "progress": 0.0, "stage": "queued"}

    progress_stop = threading.Event()
    progress_thread = threading.Thread(
        target=_aggregate_progress,
        args=(lesson_id, step_job_ids, progress_stop),
        daemon=True,
    )
    progress_thread.start()

    def _render_step(idx: int, step):
        _run_render(step_job_ids[idx], step.tool, {**step.params, "caption": step.caption})

    # Render all steps in parallel — isolated media dirs prevent collisions
    max_workers = min(len(steps), 4)
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(_render_step, i, step) for i, step in enumerate(steps)]
            for f in futures:
                f.result()
    finally:
        progress_stop.set()

    # Check for any render errors
    for jid in step_job_ids:
        if _jobs[jid]["status"] == "error":
            _jobs[lesson_id] = {
                "status": "error", "url": None,
                "error": f"Step failed: {_jobs[jid]['error']}",
                "progress": _jobs[lesson_id].get("progress", 0.0),
                "stage": "error",
            }
            return

    # Single step — copy into lessons/ so the cache has a stable path that
    # survives cleanup_old_jobs() removing the original per-job dir.
    if len(step_job_ids) == 1:
        src_url  = _jobs[step_job_ids[0]]["url"]
        src_path = os.path.join(_MEDIA_DIR, src_url.removeprefix("/media/"))
        os.makedirs(_LESSONS_DIR, exist_ok=True)
        dst_path = os.path.join(_LESSONS_DIR, f"{lesson_id}.mp4")
        try:
            shutil.copyfile(src_path, dst_path)
            final_url = f"/media/lessons/{lesson_id}.mp4"
        except OSError:
            # Fall back to the original URL if copy fails — caching skipped.
            final_url = src_url
        _jobs[lesson_id] = {"status": "done", "url": final_url, "error": None,
                            "progress": 1.0, "stage": "done"}
        if final_url.startswith("/media/lessons/"):
            _cache_store(cache_key, final_url)
        return

    # Multi-step: announce stitching stage before invoking ffmpeg
    _jobs[lesson_id]["stage"] = "stitching"

    # Collect video paths in submission order then stitch
    video_paths = [
        os.path.join(_MEDIA_DIR, _jobs[jid]["url"].removeprefix("/media/"))
        for jid in step_job_ids
    ]
    os.makedirs(_LESSONS_DIR, exist_ok=True)
    output_path = os.path.join(_LESSONS_DIR, f"{lesson_id}.mp4")

    try:
        stitch_videos(video_paths, output_path)
    except Exception as e:
        _jobs[lesson_id] = {"status": "error", "url": None,
                            "error": f"stitch failed: {e}",
                            "progress": _jobs[lesson_id].get("progress", 0.95),
                            "stage": "error"}
        return

    final_url = f"/media/lessons/{lesson_id}.mp4"
    _jobs[lesson_id] = {"status": "done", "url": final_url, "error": None,
                        "progress": 1.0, "stage": "done"}
    _cache_store(cache_key, final_url)
