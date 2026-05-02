"""Integration tests for extended algebra scenes."""
import json, os, subprocess, sys
from pathlib import Path
import pytest

BACKEND = Path(__file__).parent.parent
SCENE_FILE = "scenes/algebra_scene.py"

def _render(tmp_path, scene_class, params):
    job_id = f"test-{scene_class.lower()}-{abs(hash(str(params))) % 9999}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / f"{job_id}.json").write_text(json.dumps(params))
    return subprocess.run(
        [sys.executable, "-m", "manim", "-ql",
         "--media_dir", str(tmp_path / "media"), "--disable_caching",
         SCENE_FILE, scene_class],
        capture_output=True, text=True, timeout=120, cwd=str(BACKEND),
        env={**os.environ, "MANIM_JOB_ID": job_id, "MANIM_TEMP_DIR": str(tmp_path)},
    )

def _ok(result, tmp_path, scene_class):
    assert result.returncode == 0, f"STDERR:\n{result.stderr[-600:]}"
    out = tmp_path / "media" / "videos" / Path(SCENE_FILE).stem / "480p15" / f"{scene_class}.mp4"
    assert out.exists()

@pytest.mark.integration
def test_inequality_linear(tmp_path):
    _ok(_render(tmp_path, "InequalityScene", {"expression": "x + 2 > 5", "domain": [-5, 10]}), tmp_path, "InequalityScene")

@pytest.mark.integration
def test_inequality_quadratic(tmp_path):
    _ok(_render(tmp_path, "InequalityScene", {"expression": "x**2 < 9", "domain": [-5, 5]}), tmp_path, "InequalityScene")

@pytest.mark.integration
def test_exponential_growth(tmp_path):
    _ok(_render(tmp_path, "ExponentialScene", {"expression": "2**x", "domain": [-3, 5]}), tmp_path, "ExponentialScene")

@pytest.mark.integration
def test_exponential_decay(tmp_path):
    _ok(_render(tmp_path, "ExponentialScene", {"expression": "exp(-0.5*x)", "domain": [-1, 8]}), tmp_path, "ExponentialScene")

@pytest.mark.integration
def test_transformation_shift(tmp_path):
    _ok(_render(tmp_path, "TransformationScene", {
        "base_expression": "x**2",
        "transformed_expression": "(x-2)**2 + 3",
        "domain": [-4, 6],
    }), tmp_path, "TransformationScene")

@pytest.mark.integration
def test_transformation_reflect(tmp_path):
    _ok(_render(tmp_path, "TransformationScene", {
        "base_expression": "sqrt(x)",
        "transformed_expression": "-sqrt(x)",
        "domain": [0, 6],
    }), tmp_path, "TransformationScene")
