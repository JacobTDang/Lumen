import hashlib
import json
import os
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
# 2D scenes use medium quality (720p30); 3D surface is kept at low (480p15)
# because surface renders are significantly slower.
# ---------------------------------------------------------------------------
_QUALITY_2D  = "-qm"
_QUALITY_DIR_2D = "720p30"
_QUALITY_3D  = "-ql"
_QUALITY_DIR_3D = "480p15"
_3D_SCENES   = {"surface_plot", "partial_derivative"}

SCENE_REGISTRY = {
    # Core
    "bubble_sort":        ("scenes/array_scene.py",       "BubbleSortScene"),
    # Calculus
    "function_plot":      ("scenes/calculus_scene.py",    "FunctionPlotScene"),
    "limit":              ("scenes/calculus_scene.py",    "LimitScene"),
    "tangent_line":       ("scenes/calculus_scene.py",    "TangentLineScene"),
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

    media/lessons/ and media/steps/ are intentionally left alone — those hold
    final stitched outputs that may be cached or still referenced by clients.
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


# ---------------------------------------------------------------------------
# Single-scene API
# ---------------------------------------------------------------------------

def submit_render(scene_type: str, params: dict) -> str:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending", "url": None, "error": None}
    threading.Thread(
        target=_run_render, args=(job_id, scene_type, params), daemon=True,
    ).start()
    return job_id


def get_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)


def _run_render(job_id: str, scene_type: str, params: dict):
    if scene_type not in SCENE_REGISTRY:
        _jobs[job_id] = {"status": "error", "url": None, "error": f"unknown scene type: {scene_type}"}
        return

    os.makedirs(_TEMP_DIR, exist_ok=True)
    params_path = os.path.join(_TEMP_DIR, f"{job_id}.json")

    # Each job gets its own media directory — enables parallel rendering
    # without output file collisions between jobs of the same scene class.
    is_3d         = scene_type in _3D_SCENES
    quality_flag  = _QUALITY_3D  if is_3d else _QUALITY_2D
    quality_dir   = _QUALITY_DIR_3D if is_3d else _QUALITY_DIR_2D
    job_media_dir = os.path.join(_MEDIA_DIR, "jobs", job_id)
    os.makedirs(job_media_dir, exist_ok=True)

    try:
        with open(params_path, "w") as f:
            json.dump(params, f)

        scene_file, scene_class = SCENE_REGISTRY[scene_type]

        result = subprocess.run(
            [sys.executable, "-m", "manim", quality_flag,
             "--media_dir", job_media_dir,
             "--disable_caching", scene_file, scene_class],
            capture_output=True, text=True, timeout=180,
            cwd=_BACKEND_DIR,
            env={**os.environ, "MANIM_JOB_ID": job_id, "MANIM_TEMP_DIR": _TEMP_DIR},
        )

        if result.returncode != 0:
            _jobs[job_id] = {"status": "error", "url": None, "error": result.stderr[-500:]}
            return

        scene_stem = os.path.splitext(os.path.basename(scene_file))[0]
        video_rel  = f"jobs/{job_id}/videos/{scene_stem}/{quality_dir}/{scene_class}.mp4"
        full_path  = os.path.join(_MEDIA_DIR, video_rel)

        if not os.path.exists(full_path):
            _jobs[job_id] = {"status": "error", "url": None, "error": "output file not found after render"}
            return

        _jobs[job_id] = {"status": "done", "url": f"/media/{video_rel}", "error": None}

    except subprocess.TimeoutExpired:
        _jobs[job_id] = {"status": "error", "url": None, "error": "render timed out after 180s"}
    except Exception as e:
        _jobs[job_id] = {"status": "error", "url": None, "error": str(e)}
    finally:
        if os.path.exists(params_path):
            os.remove(params_path)


# ---------------------------------------------------------------------------
# Multi-scene lesson API  (parallel rendering)
# ---------------------------------------------------------------------------

def submit_lesson(steps: list) -> str:
    lesson_id = str(uuid.uuid4())
    _jobs[lesson_id] = {"status": "pending", "url": None, "error": None}
    threading.Thread(
        target=_run_lesson, args=(lesson_id, steps), daemon=True,
    ).start()
    return lesson_id


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
    # Lazy housekeeping — drop old per-job render dirs so media/ doesn't grow
    # unboundedly during normal usage. Failures here must not block a render.
    try:
        cleanup_old_jobs()
    except Exception:
        pass

    # Cache check — identical (tool, params) sequence → reuse stitched video
    cache_key   = _lesson_cache_key(steps)
    cached_url  = _cache_lookup(cache_key)
    if cached_url is not None:
        _jobs[lesson_id] = {"status": "done", "url": cached_url, "error": None}
        return

    def _render_step(step):
        step_job_id = str(uuid.uuid4())
        _jobs[step_job_id] = {"status": "pending", "url": None, "error": None}
        _run_render(step_job_id, step.tool, {**step.params, "caption": step.caption})
        return step_job_id

    # Render all steps in parallel — isolated media dirs prevent collisions
    max_workers = min(len(steps), 4)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures        = [pool.submit(_render_step, step) for step in steps]
        step_job_ids   = [f.result() for f in futures]  # preserves submission order

    # Check for any render errors
    for jid in step_job_ids:
        if _jobs[jid]["status"] == "error":
            _jobs[lesson_id] = {
                "status": "error", "url": None,
                "error": f"Step failed: {_jobs[jid]['error']}",
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
        _jobs[lesson_id] = {"status": "done", "url": final_url, "error": None}
        if final_url.startswith("/media/lessons/"):
            _cache_store(cache_key, final_url)
        return

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
        _jobs[lesson_id] = {"status": "error", "url": None, "error": f"stitch failed: {e}"}
        return

    final_url = f"/media/lessons/{lesson_id}.mp4"
    _jobs[lesson_id] = {"status": "done", "url": final_url, "error": None}
    _cache_store(cache_key, final_url)
