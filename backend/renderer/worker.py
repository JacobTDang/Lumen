import json
import os
import shutil
import subprocess
import sys
import threading
import uuid

_jobs: dict = {}

SCENE_REGISTRY = {
    "bubble_sort":      ("scenes/array_scene.py",   "BubbleSortScene"),
    "function_plot":    ("scenes/calculus_scene.py", "FunctionPlotScene"),
    "limit":            ("scenes/calculus_scene.py", "LimitScene"),
    "tangent_line":     ("scenes/calculus_scene.py", "TangentLineScene"),
    "riemann_sum":      ("scenes/calculus_scene.py", "RiemannSumScene"),
    "critical_points":  ("scenes/calculus_scene.py", "CriticalPointsScene"),
    "linear_function":  ("scenes/algebra_scene.py",  "LinearFunctionScene"),
    "quadratic":        ("scenes/algebra_scene.py",  "QuadraticScene"),
    "trig_unit_circle": ("scenes/trig_scene.py",     "TrigUnitCircleScene"),
}

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MEDIA_DIR   = os.path.join(_BACKEND_DIR, "media")
_TEMP_DIR    = os.path.join(_MEDIA_DIR,   "temp")


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

    try:
        with open(params_path, "w") as f:
            json.dump(params, f)

        scene_file, scene_class = SCENE_REGISTRY[scene_type]

        result = subprocess.run(
            [sys.executable, "-m", "manim", "-ql", "--media_dir", "media",
             "--disable_caching", scene_file, scene_class],
            capture_output=True, text=True, timeout=120,
            cwd=_BACKEND_DIR,
            env={**os.environ, "MANIM_JOB_ID": job_id, "MANIM_TEMP_DIR": _TEMP_DIR},
        )

        if result.returncode != 0:
            _jobs[job_id] = {"status": "error", "url": None, "error": result.stderr[-500:]}
            return

        scene_stem = os.path.splitext(os.path.basename(scene_file))[0]
        video_path = f"videos/{scene_stem}/480p15/{scene_class}.mp4"
        full_path  = os.path.join(_MEDIA_DIR, video_path)

        if not os.path.exists(full_path):
            _jobs[job_id] = {"status": "error", "url": None, "error": "output file not found after render"}
            return

        _jobs[job_id] = {"status": "done", "url": f"/media/{video_path}", "error": None}

    except subprocess.TimeoutExpired:
        _jobs[job_id] = {"status": "error", "url": None, "error": "render timed out after 120s"}
    except Exception as e:
        _jobs[job_id] = {"status": "error", "url": None, "error": str(e)}
    finally:
        if os.path.exists(params_path):
            os.remove(params_path)


# ---------------------------------------------------------------------------
# Multi-scene lesson API
# ---------------------------------------------------------------------------

def submit_lesson(steps: list) -> str:
    """Submit a multi-step lesson plan. Returns a lesson job_id."""
    lesson_id = str(uuid.uuid4())
    _jobs[lesson_id] = {"status": "pending", "url": None, "error": None}
    threading.Thread(
        target=_run_lesson, args=(lesson_id, steps), daemon=True,
    ).start()
    return lesson_id


def stitch_videos(paths: list[str], out: str):
    """Concatenate video files using FFmpeg concat demuxer."""
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
    steps_dir = os.path.join(_MEDIA_DIR, "steps")
    os.makedirs(steps_dir, exist_ok=True)

    video_paths = []

    for step in steps:
        step_job_id = str(uuid.uuid4())
        _jobs[step_job_id] = {"status": "pending", "url": None, "error": None}

        # Pass caption into params so scenes can display it
        params_with_caption = {**step.params, "caption": step.caption}
        _run_render(step_job_id, step.tool, params_with_caption)

        if _jobs[step_job_id]["status"] == "error":
            _jobs[lesson_id] = {
                "status": "error", "url": None,
                "error": f"Step '{step.tool}' failed: {_jobs[step_job_id]['error']}",
            }
            return

        # Copy to a step-specific path before the next render can overwrite
        original_url  = _jobs[step_job_id]["url"]
        original_path = os.path.join(_MEDIA_DIR, original_url.removeprefix("/media/"))
        permanent     = os.path.join(steps_dir, f"{step_job_id}.mp4")
        shutil.copy2(original_path, permanent)
        video_paths.append(permanent)

    # Single step — no stitching needed
    if len(video_paths) == 1:
        _jobs[lesson_id] = {"status": "done", "url": f"/media/steps/{os.path.basename(video_paths[0])}", "error": None}
        return

    # Stitch
    lessons_dir  = os.path.join(_MEDIA_DIR, "lessons")
    os.makedirs(lessons_dir, exist_ok=True)
    output_path  = os.path.join(lessons_dir, f"{lesson_id}.mp4")

    try:
        stitch_videos(video_paths, output_path)
    except Exception as e:
        _jobs[lesson_id] = {"status": "error", "url": None, "error": f"stitch failed: {e}"}
        return

    _jobs[lesson_id] = {"status": "done", "url": f"/media/lessons/{lesson_id}.mp4", "error": None}
