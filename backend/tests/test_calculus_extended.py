"""Integration tests for extended calculus scenes."""
import json, os, subprocess, sys
from pathlib import Path
import pytest

BACKEND = Path(__file__).parent.parent
SCENE_FILE = "scenes/calculus_scene.py"

def _render(tmp_path, scene_class, params):
    job_id = f"test-{scene_class.lower()}-{abs(hash(str(params))) % 9999}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / f"{job_id}.json").write_text(json.dumps(params))
    return subprocess.run(
        [sys.executable, "-m", "manim", "-ql",
         "--media_dir", str(tmp_path / "media"), "--disable_caching",
         SCENE_FILE, scene_class],
        capture_output=True, text=True, timeout=180, cwd=str(BACKEND),
        env={**os.environ, "MANIM_JOB_ID": job_id, "MANIM_TEMP_DIR": str(tmp_path)},
    )

def _ok(result, tmp_path, scene_class):
    assert result.returncode == 0, f"STDERR:\n{result.stderr[-800:]}"
    out = tmp_path / "media" / "videos" / Path(SCENE_FILE).stem / "480p15" / f"{scene_class}.mp4"
    assert out.exists()

@pytest.mark.integration
def test_volume_revolution_sqrt(tmp_path):
    _ok(_render(tmp_path, "VolumeRevolutionScene", {"expression": "sqrt(x)", "domain": [0, 4], "n_disks": 8}), tmp_path, "VolumeRevolutionScene")

@pytest.mark.integration
def test_volume_revolution_parabola(tmp_path):
    _ok(_render(tmp_path, "VolumeRevolutionScene", {"expression": "x**2", "domain": [0, 2], "n_disks": 6}), tmp_path, "VolumeRevolutionScene")

@pytest.mark.integration
def test_taylor_series_sin(tmp_path):
    _ok(_render(tmp_path, "TaylorSeriesScene", {"expression": "sin(x)", "center": 0, "max_terms": 4, "domain": [-5, 5]}), tmp_path, "TaylorSeriesScene")

@pytest.mark.integration
def test_taylor_series_exp(tmp_path):
    _ok(_render(tmp_path, "TaylorSeriesScene", {"expression": "exp(x)", "center": 0, "max_terms": 4, "domain": [-3, 3]}), tmp_path, "TaylorSeriesScene")

@pytest.mark.integration
def test_ftc_quadratic(tmp_path):
    _ok(_render(tmp_path, "FTCScene", {"expression": "x**2 - 2*x + 2", "domain": [-0.5, 4], "start": 0}), tmp_path, "FTCScene")

@pytest.mark.integration
def test_ftc_sin(tmp_path):
    _ok(_render(tmp_path, "FTCScene", {"expression": "sin(x)", "domain": [-1, 5], "start": 0}), tmp_path, "FTCScene")
