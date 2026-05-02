"""
Integration tests for new algebra and trig scene types.
Run with: pytest backend/tests/test_new_scenes.py -v -m integration
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).parent.parent


def _render(tmp_path: Path, scene_file: str, scene_class: str, params: dict):
    job_id = f"test-{scene_class.lower()}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / f"{job_id}.json").write_text(json.dumps(params))
    media_dir = tmp_path / "media"
    return subprocess.run(
        [sys.executable, "-m", "manim", "-ql",
         "--media_dir", str(media_dir), "--disable_caching",
         scene_file, scene_class],
        capture_output=True, text=True, timeout=120, cwd=str(BACKEND),
        env={**os.environ, "MANIM_JOB_ID": job_id, "MANIM_TEMP_DIR": str(tmp_path)},
    )


def _assert_ok(result, tmp_path, scene_file, scene_class):
    assert result.returncode == 0, f"STDERR:\n{result.stderr[-800:]}"
    stem   = Path(scene_file).stem
    output = tmp_path / "media" / "videos" / stem / "480p15" / f"{scene_class}.mp4"
    assert output.exists(), f"Output not found: {output}"


# ---------------------------------------------------------------------------
# LinearFunctionScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_linear_function_basic(tmp_path):
    r = _render(tmp_path, "scenes/algebra_scene.py", "LinearFunctionScene",
                {"expression": "2*x + 1", "domain": [-5, 5]})
    _assert_ok(r, tmp_path, "scenes/algebra_scene.py", "LinearFunctionScene")


@pytest.mark.integration
def test_linear_function_two_lines(tmp_path):
    r = _render(tmp_path, "scenes/algebra_scene.py", "LinearFunctionScene",
                {"expression": "2*x + 1", "domain": [-5, 5], "second_expression": "-x + 4"})
    _assert_ok(r, tmp_path, "scenes/algebra_scene.py", "LinearFunctionScene")


@pytest.mark.integration
def test_linear_function_with_caption(tmp_path):
    r = _render(tmp_path, "scenes/algebra_scene.py", "LinearFunctionScene",
                {"expression": "3*x - 2", "domain": [-4, 4], "caption": "Slope = 3, y-intercept = -2"})
    _assert_ok(r, tmp_path, "scenes/algebra_scene.py", "LinearFunctionScene")


# ---------------------------------------------------------------------------
# QuadraticScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_quadratic_basic(tmp_path):
    r = _render(tmp_path, "scenes/algebra_scene.py", "QuadraticScene",
                {"expression": "x**2 - 4", "domain": [-4, 4]})
    _assert_ok(r, tmp_path, "scenes/algebra_scene.py", "QuadraticScene")


@pytest.mark.integration
def test_quadratic_no_real_roots(tmp_path):
    r = _render(tmp_path, "scenes/algebra_scene.py", "QuadraticScene",
                {"expression": "x**2 + 4", "domain": [-4, 4]})
    _assert_ok(r, tmp_path, "scenes/algebra_scene.py", "QuadraticScene")


@pytest.mark.integration
def test_quadratic_with_caption(tmp_path):
    r = _render(tmp_path, "scenes/algebra_scene.py", "QuadraticScene",
                {"expression": "x**2 - 2*x - 3", "domain": [-3, 5],
                 "caption": "Roots at x = -1 and x = 3"})
    _assert_ok(r, tmp_path, "scenes/algebra_scene.py", "QuadraticScene")


# ---------------------------------------------------------------------------
# TrigUnitCircleScene
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_trig_unit_circle_animated(tmp_path):
    r = _render(tmp_path, "scenes/trig_scene.py", "TrigUnitCircleScene",
                {"angle": 0.785, "animate_rotation": True})
    _assert_ok(r, tmp_path, "scenes/trig_scene.py", "TrigUnitCircleScene")


@pytest.mark.integration
def test_trig_unit_circle_static(tmp_path):
    r = _render(tmp_path, "scenes/trig_scene.py", "TrigUnitCircleScene",
                {"angle": 1.57, "animate_rotation": False})
    _assert_ok(r, tmp_path, "scenes/trig_scene.py", "TrigUnitCircleScene")
