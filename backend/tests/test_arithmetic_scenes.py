"""Integration tests for arithmetic scenes."""
import json, os, subprocess, sys
from pathlib import Path
import pytest

BACKEND = Path(__file__).parent.parent

def _render(tmp_path, scene_class, params, scene_file="scenes/arithmetic_scene.py"):
    job_id = f"test-{scene_class.lower()}-{abs(hash(str(params))) % 9999}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / f"{job_id}.json").write_text(json.dumps(params))
    return subprocess.run(
        [sys.executable, "-m", "manim", "-ql",
         "--media_dir", str(tmp_path / "media"), "--disable_caching",
         scene_file, scene_class],
        capture_output=True, text=True, timeout=120, cwd=str(BACKEND),
        env={**os.environ, "MANIM_JOB_ID": job_id, "MANIM_TEMP_DIR": str(tmp_path)},
    )

def _ok(result, tmp_path, scene_class, scene_file="scenes/arithmetic_scene.py"):
    assert result.returncode == 0, f"STDERR:\n{result.stderr[-600:]}"
    stem = Path(scene_file).stem
    out  = tmp_path / "media" / "videos" / stem / "480p15" / f"{scene_class}.mp4"
    assert out.exists(), f"Missing: {out}"

# NumberLineScene
@pytest.mark.integration
def test_number_line_addition(tmp_path):
    _ok(_render(tmp_path, "NumberLineScene", {"mode": "addition", "values": [3, 4], "domain": [-1, 10]}), tmp_path, "NumberLineScene")

@pytest.mark.integration
def test_number_line_subtraction(tmp_path):
    _ok(_render(tmp_path, "NumberLineScene", {"mode": "subtraction", "values": [8, 3], "domain": [-1, 10]}), tmp_path, "NumberLineScene")

@pytest.mark.integration
def test_number_line_inequality(tmp_path):
    _ok(_render(tmp_path, "NumberLineScene", {"mode": "inequality", "values": [3], "inequality_sign": ">", "domain": [-5, 10]}), tmp_path, "NumberLineScene")

@pytest.mark.integration
def test_number_line_absolute_value(tmp_path):
    _ok(_render(tmp_path, "NumberLineScene", {"mode": "absolute_value", "values": [2, 3], "domain": [-5, 8]}), tmp_path, "NumberLineScene")

# FractionScene
@pytest.mark.integration
def test_fraction_represent(tmp_path):
    _ok(_render(tmp_path, "FractionScene", {"mode": "represent", "fractions": [[2, 3]]}), tmp_path, "FractionScene")

@pytest.mark.integration
def test_fraction_compare(tmp_path):
    _ok(_render(tmp_path, "FractionScene", {"mode": "compare", "fractions": [[1, 2], [1, 3]]}), tmp_path, "FractionScene")

@pytest.mark.integration
def test_fraction_add(tmp_path):
    _ok(_render(tmp_path, "FractionScene", {"mode": "add", "fractions": [[1, 2], [1, 3]]}), tmp_path, "FractionScene")

@pytest.mark.integration
def test_fraction_subtract(tmp_path):
    _ok(_render(tmp_path, "FractionScene", {"mode": "subtract", "fractions": [[3, 4], [1, 4]]}), tmp_path, "FractionScene")

# AreaModelScene
@pytest.mark.integration
def test_area_model_integer(tmp_path):
    _ok(_render(tmp_path, "AreaModelScene", {"mode": "integer", "a": "4", "b": "6"}), tmp_path, "AreaModelScene")

@pytest.mark.integration
def test_area_model_algebraic(tmp_path):
    _ok(_render(tmp_path, "AreaModelScene", {"mode": "algebraic", "a": "x+2", "b": "x+3"}), tmp_path, "AreaModelScene")
