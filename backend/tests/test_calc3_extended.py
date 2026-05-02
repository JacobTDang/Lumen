"""Integration tests for extended Calc 3 scenes."""
import json, os, subprocess, sys
from pathlib import Path
import pytest

BACKEND = Path(__file__).parent.parent
SCENE_FILE = "scenes/threed_scene.py"

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
def test_contour_paraboloid(tmp_path):
    _ok(_render(tmp_path, "ContourScene", {"expression": "x**2 + y**2", "x_domain": [-3, 3], "y_domain": [-3, 3], "num_levels": 6}), tmp_path, "ContourScene")

@pytest.mark.integration
def test_contour_saddle(tmp_path):
    _ok(_render(tmp_path, "ContourScene", {"expression": "x**2 - y**2", "x_domain": [-3, 3], "y_domain": [-3, 3], "num_levels": 8}), tmp_path, "ContourScene")

@pytest.mark.integration
def test_vector_field_rotation(tmp_path):
    _ok(_render(tmp_path, "VectorFieldScene", {"x_expression": "-y", "y_expression": "x", "domain": [-3, 3]}), tmp_path, "VectorFieldScene")

@pytest.mark.integration
def test_vector_field_gradient(tmp_path):
    _ok(_render(tmp_path, "VectorFieldScene", {"x_expression": "2*x", "y_expression": "2*y", "domain": [-2, 2]}), tmp_path, "VectorFieldScene")

@pytest.mark.integration
def test_partial_derivative_x(tmp_path):
    _ok(_render(tmp_path, "PartialDerivativeScene", {
        "expression": "x**2 + y**2", "variable": "x", "fixed_value": 1.0,
        "x_domain": [-3, 3], "y_domain": [-3, 3],
    }), tmp_path, "PartialDerivativeScene")

@pytest.mark.integration
def test_partial_derivative_y(tmp_path):
    _ok(_render(tmp_path, "PartialDerivativeScene", {
        "expression": "x**2 - y**2", "variable": "y", "fixed_value": 0.5,
        "x_domain": [-3, 3], "y_domain": [-3, 3],
    }), tmp_path, "PartialDerivativeScene")
