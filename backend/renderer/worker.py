import json
import os
import subprocess
import sys
import threading
import uuid

_jobs: dict = {}

SCENE_REGISTRY = {
    "bubble_sort": ("scenes/array_scene.py", "BubbleSortScene"),
}

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MEDIA_DIR = os.path.join(_BACKEND_DIR, "media")
_TEMP_DIR = os.path.join(_MEDIA_DIR, "temp")


def submit_render(scene_type: str, params: dict) -> str:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending", "url": None, "error": None}
    thread = threading.Thread(target=_run_render, args=(job_id, scene_type, params), daemon=True)
    thread.start()
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
            capture_output=True,
            text=True,
            timeout=120,
            cwd=_BACKEND_DIR,
            env={**os.environ, "MANIM_JOB_ID": job_id},
        )

        if result.returncode != 0:
            _jobs[job_id] = {"status": "error", "url": None, "error": result.stderr[-500:]}
            return

        scene_stem = os.path.splitext(os.path.basename(scene_file))[0]
        video_path = f"videos/{scene_stem}/480p15/{scene_class}.mp4"
        full_path = os.path.join(_MEDIA_DIR, video_path)

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
