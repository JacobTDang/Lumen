"""
Integration tests for calculus Manim scenes.
Each test writes real params, fires a subprocess render, and asserts the output file exists.

Run with:  pytest backend/tests/test_calculus_scenes.py -v -m integration
Skip with: pytest backend/tests/ -v -m "not integration"
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).parent.parent
SCENES_FILE = "scenes/calculus_scene.py"


def _render(tmp_path: Path, scene_class: str, params: dict) -> subprocess.CompletedProcess:
    job_id = f"test-{scene_class.lower()}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / f"{job_id}.json").write_text(json.dumps(params))

    media_dir = tmp_path / "media"
    return subprocess.run(
        [
            sys.executable, "-m", "manim",
            "-ql", "--media_dir", str(media_dir),
            "--disable_caching",
            SCENES_FILE, scene_class,
        ],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(BACKEND),
        env={
            **os.environ,
            "MANIM_JOB_ID": job_id,
            "MANIM_TEMP_DIR": str(tmp_path),
        },
    )


def _assert_rendered(result: subprocess.CompletedProcess, tmp_path: Path, scene_class: str):
    assert result.returncode == 0, (
        f"{scene_class} render failed.\nSTDERR:\n{result.stderr[-1000:]}"
    )
    scene_stem = Path(SCENES_FILE).stem
    output = tmp_path / "media" / "videos" / scene_stem / "480p15" / f"{scene_class}.mp4"
    assert output.exists(), f"Expected output at {output} but file not found."


@pytest.mark.integration
def test_function_plot_renders(tmp_path):
    params = {"expression": "x**2", "domain": [-3, 3]}
    result = _render(tmp_path, "FunctionPlotScene", params)
    _assert_rendered(result, tmp_path, "FunctionPlotScene")


@pytest.mark.integration
def test_function_plot_with_point(tmp_path):
    params = {"expression": "sin(x)", "domain": [-4, 4], "x_point": 1.5}
    result = _render(tmp_path, "FunctionPlotScene", params)
    _assert_rendered(result, tmp_path, "FunctionPlotScene")


@pytest.mark.integration
def test_limit_renders(tmp_path):
    params = {"expression": "sin(x)/x", "limit_point": 0, "domain": [-5, 5]}
    result = _render(tmp_path, "LimitScene", params)
    _assert_rendered(result, tmp_path, "LimitScene")


@pytest.mark.integration
def test_tangent_line_renders(tmp_path):
    params = {"expression": "x**3 - x", "x_point": 1.0, "domain": [-3, 3]}
    result = _render(tmp_path, "TangentLineScene", params)
    _assert_rendered(result, tmp_path, "TangentLineScene")


@pytest.mark.integration
def test_riemann_sum_renders(tmp_path):
    params = {"expression": "x**2", "domain": [0, 2], "n": 6, "method": "left"}
    result = _render(tmp_path, "RiemannSumScene", params)
    _assert_rendered(result, tmp_path, "RiemannSumScene")


@pytest.mark.integration
def test_riemann_sum_midpoint(tmp_path):
    params = {"expression": "sin(x)", "domain": [0, 3], "n": 8, "method": "midpoint"}
    result = _render(tmp_path, "RiemannSumScene", params)
    _assert_rendered(result, tmp_path, "RiemannSumScene")


@pytest.mark.integration
def test_critical_points_renders(tmp_path):
    params = {"expression": "x**3 - 3*x", "domain": [-3, 3]}
    result = _render(tmp_path, "CriticalPointsScene", params)
    _assert_rendered(result, tmp_path, "CriticalPointsScene")


@pytest.mark.integration
def test_critical_points_no_crits_in_domain(tmp_path):
    # e^x has no critical points — scene should still render cleanly
    params = {"expression": "exp(x)", "domain": [-2, 2]}
    result = _render(tmp_path, "CriticalPointsScene", params)
    _assert_rendered(result, tmp_path, "CriticalPointsScene")
