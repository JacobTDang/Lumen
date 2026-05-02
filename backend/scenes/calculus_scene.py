import json
import math
import os

import numpy as np
import sympy as sp
from manim import *


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _load_params() -> dict:
    job_id = os.environ.get("MANIM_JOB_ID")
    if job_id:
        temp_dir = os.environ.get("MANIM_TEMP_DIR", os.path.join("media", "temp"))
        path = os.path.join(temp_dir, f"{job_id}.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    return {}


def _parse(expression: str):
    x = sp.Symbol("x")
    expr = sp.sympify(expression)
    func = sp.lambdify(x, expr, modules=["numpy"])
    return expr, func, x


def _safe_eval(func, val: float) -> float:
    try:
        y = float(func(val))
        return y if math.isfinite(y) else 0.0
    except Exception:
        return 0.0


def _y_range(func, domain: list) -> list:
    xs = np.linspace(domain[0], domain[1], 400)
    finite = []
    for v in xs:
        y = _safe_eval(func, float(v))
        if math.isfinite(y) and abs(y) < 1e5:
            finite.append(y)
    if not finite:
        return [-5.0, 5.0, 1.0]
    lo, hi = min(finite), max(finite)
    pad = max((hi - lo) * 0.2, 0.5)
    lo, hi = lo - pad, hi + pad
    step = max(1.0, round((hi - lo) / 6))
    return [lo, hi, step]


def _make_axes(domain: list, yr: list, x_len: float = 9.0, y_len: float = 5.5) -> Axes:
    x_step = max(1, round((domain[1] - domain[0]) / 8))
    return Axes(
        x_range=[domain[0], domain[1], x_step],
        y_range=yr,
        x_length=x_len,
        y_length=y_len,
        axis_config={"color": WHITE, "include_numbers": True, "font_size": 20},
        tips=False,
    )


def _num(v: float) -> str:
    """Format a float for use inside a MathTex string."""
    return str(int(v)) if v == int(v) else str(round(v, 4))


# ---------------------------------------------------------------------------
# Scene 1 — Function Plot
# ---------------------------------------------------------------------------

class FunctionPlotScene(Scene):
    def construct(self):
        p = _load_params()
        expression = p.get("expression", "x**2")
        domain = p.get("domain", [-4, 4])
        x_point = p.get("x_point")

        expr, f, _ = _parse(expression)
        yr = _y_range(f, domain)
        ax = _make_axes(domain, yr)
        labels = ax.get_axis_labels(x_label="x", y_label="y")
        graph = ax.plot(f, x_range=domain, color=BLUE, use_smoothing=True)
        title = MathTex(r"f(x) = " + sp.latex(expr), font_size=36).to_edge(UP)

        self.play(Create(ax), Write(labels))
        self.play(Write(title))
        self.play(Create(graph), run_time=2)

        if x_point is not None:
            xp = float(x_point)
            yp = _safe_eval(f, xp)
            dot = Dot(ax.c2p(xp, yp), color=YELLOW, radius=0.1)
            coord = MathTex(
                r"\left(" + _num(xp) + r",\ " + f"{yp:.2f}" + r"\right)",
                font_size=24,
            ).next_to(dot, UR, buff=0.1)
            self.play(FadeIn(dot), Write(coord))

        self.wait(1)


# ---------------------------------------------------------------------------
# Scene 2 — Limit
# ---------------------------------------------------------------------------

class LimitScene(Scene):
    def construct(self):
        p = _load_params()
        expression = p.get("expression", "sin(x)/x")
        limit_pt = float(p.get("limit_point", 0))
        domain = p.get("domain", [-5, 5])

        expr, f, x_sym = _parse(expression)

        try:
            lim_val = sp.limit(expr, x_sym, limit_pt)
            lim_float = float(lim_val)
            lim_tex = sp.latex(lim_val)
        except Exception:
            lim_val = None
            lim_float = None
            lim_tex = r"\text{DNE}"

        yr = _y_range(f, domain)
        ax = _make_axes(domain, yr)
        labels = ax.get_axis_labels(x_label="x", y_label="y")

        eps = 0.08
        left_graph = ax.plot(f, x_range=[domain[0], limit_pt - eps], color=BLUE)
        right_graph = ax.plot(f, x_range=[limit_pt + eps, domain[1]], color=BLUE)

        pt_tex = _num(limit_pt)
        title = MathTex(
            r"\lim_{x \to " + pt_tex + r"} f(x)",
            font_size=36,
        ).to_edge(UP)

        self.play(Create(ax), Write(labels), Write(title))
        self.play(Create(left_graph), Create(right_graph), run_time=1.5)

        lt = ValueTracker(domain[0])
        left_dot = always_redraw(lambda: Dot(
            ax.c2p(lt.get_value(), _safe_eval(f, lt.get_value())),
            color=YELLOW, radius=0.1,
        ))
        left_tag = MathTex(r"x \to " + pt_tex + r"^-", font_size=24, color=YELLOW).to_corner(UL)
        self.add(left_dot)
        self.play(Write(left_tag))
        self.play(lt.animate.set_value(limit_pt - eps), run_time=2.5)
        self.wait(0.4)

        rt = ValueTracker(domain[1])
        right_dot = always_redraw(lambda: Dot(
            ax.c2p(rt.get_value(), _safe_eval(f, rt.get_value())),
            color=RED, radius=0.1,
        ))
        right_tag = MathTex(r"x \to " + pt_tex + r"^+", font_size=24, color=RED).to_corner(UR)
        self.add(right_dot)
        self.play(Write(right_tag))
        self.play(rt.animate.set_value(limit_pt + eps), run_time=2.5)
        self.wait(0.4)

        if lim_float is not None:
            limit_dot = Dot(ax.c2p(limit_pt, lim_float), color=WHITE, radius=0.12)
            result = MathTex(
                r"\lim_{x \to " + pt_tex + r"} f(x) = " + lim_tex,
                font_size=30,
            ).to_edge(DOWN)
            self.play(FadeIn(limit_dot), Write(result))

        self.wait(1)


# ---------------------------------------------------------------------------
# Scene 3 — Tangent Line (secant → tangent)
# ---------------------------------------------------------------------------

class TangentLineScene(Scene):
    def construct(self):
        p = _load_params()
        expression = p.get("expression", "x**2")
        x_pt = float(p.get("x_point", 1.0))
        domain = p.get("domain", [-4, 4])

        expr, f, x_sym = _parse(expression)
        d_expr = sp.diff(expr, x_sym)
        y0 = _safe_eval(f, x_pt)
        slope_sym = d_expr.subs(x_sym, x_pt)

        yr = _y_range(f, domain)
        ax = _make_axes(domain, yr)
        labels = ax.get_axis_labels(x_label="x", y_label="y")
        graph = ax.plot(f, x_range=domain, color=BLUE)
        title = MathTex(r"f(x) = " + sp.latex(expr), font_size=34).to_edge(UP)
        dot = Dot(ax.c2p(x_pt, y0), color=YELLOW, radius=0.1)

        h_max = min(2.0, (domain[1] - domain[0]) * 0.35)
        h = ValueTracker(h_max)

        def secant_line():
            hv = max(h.get_value(), 1e-5)
            s = (_safe_eval(f, x_pt + hv) - _safe_eval(f, x_pt - hv)) / (2 * hv)
            return ax.plot(
                lambda x: y0 + s * (x - x_pt),
                x_range=domain, color=YELLOW, stroke_width=2,
            )

        line = always_redraw(secant_line)
        line_label = always_redraw(lambda: Text(
            "secant" if h.get_value() > 0.05 else "tangent",
            font_size=22, color=YELLOW,
        ).to_corner(UR))

        self.play(Create(ax), Write(labels))
        self.play(Write(title), Create(graph))
        self.play(FadeIn(dot), Create(line), Write(line_label))
        self.play(h.animate.set_value(0.01), run_time=4, rate_func=smooth)

        slope_label = MathTex(
            r"f'\!\left(" + _num(x_pt) + r"\right) = " + sp.latex(slope_sym),
            font_size=28,
        ).to_edge(DOWN)
        self.play(Write(slope_label))
        self.wait(1.5)


# ---------------------------------------------------------------------------
# Scene 4 — Riemann Sum
# ---------------------------------------------------------------------------

class RiemannSumScene(Scene):
    def construct(self):
        p = _load_params()
        expression = p.get("expression", "x**2")
        domain = p.get("domain", [0, 3])
        n_start = int(p.get("n", 5))
        method = p.get("method", "left")

        sample_map = {"left": "left", "right": "right", "midpoint": "center"}
        manim_method = sample_map.get(method, "left")

        expr, f, x_sym = _parse(expression)
        yr = _y_range(f, domain)
        yr[0] = min(yr[0], -0.3)
        ax = _make_axes(domain, yr)
        labels = ax.get_axis_labels(x_label="x", y_label="y")
        graph = ax.plot(f, x_range=domain, color=BLUE)

        try:
            exact = float(sp.integrate(expr, (x_sym, domain[0], domain[1])))
            exact_str = f"{exact:.4f}"
        except Exception:
            exact_str = r"\cdots"

        a_tex, b_tex = _num(domain[0]), _num(domain[1])
        title = MathTex(
            r"\int_{" + a_tex + r"}^{" + b_tex + r"} " + sp.latex(expr) + r"\, dx",
            font_size=34,
        ).to_edge(UP)

        self.play(Create(ax), Write(labels), Write(title))
        self.play(Create(graph), run_time=1.5)

        dx0 = (domain[1] - domain[0]) / n_start
        rects = ax.get_riemann_rectangles(
            graph, x_range=domain, dx=dx0,
            input_sample_type=manim_method,
            color=BLUE, fill_opacity=0.5,
        )
        n_label = MathTex(f"n = {n_start}", font_size=26).to_corner(DR)
        self.play(FadeIn(rects), Write(n_label))
        self.wait(0.5)

        for n_new in [n_start * 3, n_start * 8, n_start * 20]:
            dx_new = (domain[1] - domain[0]) / n_new
            new_rects = ax.get_riemann_rectangles(
                graph, x_range=domain, dx=dx_new,
                input_sample_type=manim_method,
                color=BLUE, fill_opacity=0.5,
            )
            new_label = MathTex(f"n = {n_new}", font_size=26).to_corner(DR)
            self.play(
                Transform(rects, new_rects),
                Transform(n_label, new_label),
                run_time=0.9,
            )
            self.wait(0.3)

        exact_label = MathTex(r"= " + exact_str, font_size=28).next_to(title, DOWN)
        self.play(Write(exact_label))
        self.wait(1)


# ---------------------------------------------------------------------------
# Scene 5 — Critical Points
# ---------------------------------------------------------------------------

class CriticalPointsScene(Scene):
    def construct(self):
        p = _load_params()
        expression = p.get("expression", "x**3 - 3*x")
        domain = p.get("domain", [-3, 3])

        expr, f, x_sym = _parse(expression)
        d_expr = sp.diff(expr, x_sym)
        d2_expr = sp.diff(d_expr, x_sym)
        f_prime = sp.lambdify(x_sym, d_expr, modules=["numpy"])

        try:
            raw = sp.solve(d_expr, x_sym)
            crit_pts = sorted([
                float(cp.evalf()) for cp in raw
                if cp.is_real and domain[0] <= float(cp.evalf()) <= domain[1]
            ])
        except Exception:
            crit_pts = []

        yr_f = _y_range(f, domain)
        yr_fp = _y_range(f_prime, domain)
        x_step = max(1, round((domain[1] - domain[0]) / 8))

        ax_f = Axes(
            x_range=[domain[0], domain[1], x_step],
            y_range=yr_f, x_length=8, y_length=2.6,
            axis_config={"color": WHITE, "include_numbers": True, "font_size": 16},
            tips=False,
        ).shift(UP * 1.9)

        ax_fp = Axes(
            x_range=[domain[0], domain[1], x_step],
            y_range=yr_fp, x_length=8, y_length=2.6,
            axis_config={"color": WHITE, "include_numbers": True, "font_size": 16},
            tips=False,
        ).shift(DOWN * 1.9)

        graph_f = ax_f.plot(f, x_range=domain, color=BLUE)
        graph_fp = ax_fp.plot(f_prime, x_range=domain, color=GREEN)

        lbl_f = MathTex(r"f(x)", font_size=22, color=BLUE).next_to(ax_f, LEFT)
        lbl_fp = MathTex(r"f'(x)", font_size=22, color=GREEN).next_to(ax_fp, LEFT)

        self.play(Create(ax_f), Create(ax_fp), Write(lbl_f), Write(lbl_fp))
        self.play(Create(graph_f), Create(graph_fp), run_time=2)

        for cp in crit_pts:
            y_f = _safe_eval(f, cp)
            dot_f = Dot(ax_f.c2p(cp, y_f), color=RED, radius=0.1)
            dot_fp = Dot(ax_fp.c2p(cp, 0), color=RED, radius=0.1)

            s2 = float(d2_expr.subs(x_sym, cp).evalf())
            kind = "inflection" if abs(s2) < 1e-8 else ("local max" if s2 < 0 else "local min")

            cp_label = Text(kind, font_size=18, color=RED).next_to(dot_f, UP, buff=0.1)
            self.play(FadeIn(dot_f), FadeIn(dot_fp))
            self.play(Write(cp_label))

        self.wait(1)
