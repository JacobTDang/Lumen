"""Integration tests for the 9 new area/volume/integral scenes."""
import json, os, subprocess, sys
from pathlib import Path
import pytest

BACKEND    = Path(__file__).parent.parent
SCENE_FILE = "scenes/calculus_scene.py"


def _render(tmp_path, scene_class, params):
    job_id = f"test-{scene_class.lower()[:16]}-{abs(hash(str(params))) % 9999}"
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
    assert result.returncode == 0, f"STDERR:\n{result.stderr[-600:]}"
    out = tmp_path / "media" / "videos" / Path(SCENE_FILE).stem / "480p15" / f"{scene_class}.mp4"
    assert out.exists(), f"Missing: {out}"


@pytest.mark.integration
def test_area_between_curves(tmp_path):
    _ok(_render(tmp_path, "AreaBetweenCurvesScene",
                {"f_expression": "x", "g_expression": "x**2", "domain": [0, 1]}), tmp_path, "AreaBetweenCurvesScene")


@pytest.mark.integration
def test_washer_method(tmp_path):
    _ok(_render(tmp_path, "WasherMethodScene",
                {"f_expression": "sqrt(x)", "g_expression": "x**2", "domain": [0, 1], "n_washers": 6}),
        tmp_path, "WasherMethodScene")


@pytest.mark.integration
def test_shell_method(tmp_path):
    _ok(_render(tmp_path, "ShellMethodScene",
                {"expression": "sqrt(x)", "domain": [0, 4], "n_shells": 8}), tmp_path, "ShellMethodScene")


@pytest.mark.integration
def test_arc_length_sin(tmp_path):
    _ok(_render(tmp_path, "ArcLengthScene",
                {"expression": "sin(x)", "domain": [0, 3.14], "n_segments": 8}), tmp_path, "ArcLengthScene")


@pytest.mark.integration
def test_average_value(tmp_path):
    _ok(_render(tmp_path, "AverageValueScene",
                {"expression": "sin(x)", "domain": [0, 3.14]}), tmp_path, "AverageValueScene")


@pytest.mark.integration
def test_u_substitution(tmp_path):
    _ok(_render(tmp_path, "USubstitutionScene",
                {"expression": "cos(2*x)", "u_expression": "2*x", "domain": [0, 1.57]}),
        tmp_path, "USubstitutionScene")


@pytest.mark.integration
def test_integration_by_parts(tmp_path):
    _ok(_render(tmp_path, "IntegrationByPartsScene",
                {"u_expression": "x", "dv_expression": "exp(x)", "domain": [0, 2]}),
        tmp_path, "IntegrationByPartsScene")


@pytest.mark.integration
def test_improper_integral_converges(tmp_path):
    _ok(_render(tmp_path, "ImproperIntegralScene",
                {"expression": "1/x**2", "domain": [1, 12], "improper_bound": "right"}),
        tmp_path, "ImproperIntegralScene")


@pytest.mark.integration
def test_cross_section_square(tmp_path):
    _ok(_render(tmp_path, "CrossSectionScene",
                {"expression": "sin(x)", "domain": [0, 3.14], "shape": "square"}),
        tmp_path, "CrossSectionScene")


@pytest.mark.integration
def test_cross_section_semicircle(tmp_path):
    _ok(_render(tmp_path, "CrossSectionScene",
                {"expression": "sqrt(1 - x**2)", "domain": [-1, 1], "shape": "semicircle"}),
        tmp_path, "CrossSectionScene")
