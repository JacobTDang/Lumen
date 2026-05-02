import json
import math
import os

import numpy as np
import sympy as sp
from manim import *


def _load_params() -> dict:
    job_id = os.environ.get("MANIM_JOB_ID")
    if job_id:
        temp_dir = os.environ.get("MANIM_TEMP_DIR", os.path.join("media", "temp"))
        path = os.path.join(temp_dir, f"{job_id}.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    return {}


def _safe_eval_2d(f, u: float, v: float) -> float:
    try:
        z = float(f(u, v))
        return z if math.isfinite(z) else 0.0
    except Exception:
        return 0.0


def _caption_3d(text: str) -> Text:
    return Text(text, font_size=20, color=GRAY, slant=ITALIC).to_corner(DR, buff=0.2)


# ---------------------------------------------------------------------------
# SurfacePlotScene — z = f(x, y) with rotating camera
# ---------------------------------------------------------------------------

class SurfacePlotScene(ThreeDScene):
    def construct(self):
        p          = _load_params()
        expression = p.get("expression", "x**2 + y**2")
        x_domain   = p.get("x_domain",  [-3, 3])
        y_domain   = p.get("y_domain",  [-3, 3])
        cap        = p.get("caption",   "")

        x_sym, y_sym = sp.symbols("x y")
        expr = sp.sympify(expression)
        f    = sp.lambdify((x_sym, y_sym), expr, modules=["numpy"])

        # Sample the surface to compute a sensible z-range
        xs = np.linspace(x_domain[0], x_domain[1], 20)
        ys = np.linspace(y_domain[0], y_domain[1], 20)
        zs = [_safe_eval_2d(f, float(u), float(v)) for u in xs for v in ys]
        zs = [z for z in zs if math.isfinite(z) and abs(z) < 1e4]
        z_min = min(zs) if zs else -5.0
        z_max = max(zs) if zs else  5.0
        z_pad = max((z_max - z_min) * 0.18, 0.5)

        x_step = max(1, round((x_domain[1] - x_domain[0]) / 6))
        y_step = max(1, round((y_domain[1] - y_domain[0]) / 6))
        z_step = max(1, round((z_max - z_min) / 4))

        axes = ThreeDAxes(
            x_range=[x_domain[0], x_domain[1], x_step],
            y_range=[y_domain[0], y_domain[1], y_step],
            z_range=[z_min - z_pad, z_max + z_pad, z_step],
            x_length=6, y_length=6, z_length=4,
            axis_config={"color": WHITE, "include_numbers": False},
            tips=True,
        )

        axis_labels = axes.get_axis_labels(
            x_label=Text("x", font_size=22),
            y_label=Text("y", font_size=22),
            z_label=Text("z", font_size=22),
        )

        surface = Surface(
            lambda u, v: axes.c2p(u, v, _safe_eval_2d(f, u, v)),
            u_range=x_domain,
            v_range=y_domain,
            resolution=(28, 28),
            fill_opacity=0.88,
            checkerboard_colors=False,
            stroke_width=0.3,
            stroke_color=WHITE,
        )
        surface.set_color_by_gradient(BLUE_E, TEAL, GREEN, YELLOW, RED)

        title = Text(f"z = {expression}", font_size=26, color=WHITE).to_corner(UL, buff=0.25)

        self.set_camera_orientation(phi=70 * DEGREES, theta=-60 * DEGREES)
        self.add(axes, axis_labels)

        if cap:
            self.add_fixed_in_frame_mobjects(_caption_3d(cap))

        self.add_fixed_in_frame_mobjects(title)
        self.play(Create(surface), run_time=2.5)
        self.begin_ambient_camera_rotation(rate=0.18)
        self.wait(6)
        self.stop_ambient_camera_rotation()

        # Tilt to a top-down view to show contours
        self.move_camera(phi=20 * DEGREES, theta=-90 * DEGREES, run_time=2)
        self.wait(1.5)
