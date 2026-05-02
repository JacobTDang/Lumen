"""
Integration tests for 3D surface scene.
Run with: pytest backend/tests/test_3d_scenes.py -v -m integration

3D renders are slower (~45-90s each).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND    = Path(__file__).parent.parent
SCENE_FILE = "scenes/threed_scene.py"
SCENE_CLS  = "SurfacePlotScene"


def _render_3d(tmp_path: Path, params: dict) -> subprocess.CompletedProcess:
    job_id = f"test-surface-{abs(hash(str(params))) % 10000}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / f"{job_id}.json").write_text(json.dumps(params))
    media_dir = tmp_path / "media"
    return subprocess.run(
        [sys.executable, "-m", "manim", "-ql",
         "--media_dir", str(media_dir), "--disable_caching",
         SCENE_FILE, SCENE_CLS],
        capture_output=True, text=True, timeout=180,
        cwd=str(BACKEND),
        env={**os.environ, "MANIM_JOB_ID": job_id, "MANIM_TEMP_DIR": str(tmp_path)},
    )


def _assert_ok(result: subprocess.CompletedProcess, tmp_path: Path):
    assert result.returncode == 0, f"STDERR:\n{result.stderr[-800:]}"
    output = tmp_path / "media" / "videos" / "threed_scene" / "480p15" / f"{SCENE_CLS}.mp4"
    assert output.exists(), f"Output not found: {output}"
    assert output.stat().st_size > 5000


@pytest.mark.integration
def test_surface_paraboloid(tmp_path):
    _assert_ok(_render_3d(tmp_path, {
        "expression": "x**2 + y**2",
        "x_domain": [-3, 3],
        "y_domain": [-3, 3],
    }), tmp_path)


@pytest.mark.integration
def test_surface_saddle(tmp_path):
    _assert_ok(_render_3d(tmp_path, {
        "expression": "x**2 - y**2",
        "x_domain": [-3, 3],
        "y_domain": [-3, 3],
        "caption": "Saddle point at the origin",
    }), tmp_path)


@pytest.mark.integration
def test_surface_wave(tmp_path):
    _assert_ok(_render_3d(tmp_path, {
        "expression": "sin(x)*cos(y)",
        "x_domain": [-4, 4],
        "y_domain": [-4, 4],
    }), tmp_path)


@pytest.mark.integration
def test_surface_gaussian(tmp_path):
    _assert_ok(_render_3d(tmp_path, {
        "expression": "exp(-(x**2 + y**2))",
        "x_domain": [-3, 3],
        "y_domain": [-3, 3],
    }), tmp_path)
