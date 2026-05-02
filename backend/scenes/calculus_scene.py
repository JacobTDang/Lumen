import json
import math
import os

import numpy as np
import sympy as sp
from manim import *

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
CURVE_COLOR    = BLUE
DERIV_COLOR    = GREEN
HIGHLIGHT_COLOR = YELLOW
CRITICAL_COLOR = RED
TANGENT_COLOR  = YELLOW

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
    finite = [_safe_eval(func, float(v)) for v in xs]
    finite = [y for y in finite if math.isfinite(y) and abs(y) < 1e5]
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
    return str(int(v)) if v == int(v) else str(round(v, 4))


def _clip_latex(expr, max_chars: int = 28) -> str:
    s = sp.latex(expr)
    if len(s) <= max_chars:
        return s
    simplified = sp.latex(expr.simplify())
    return simplified if len(simplified) <= max_chars else simplified[:max_chars] + r"\cdots"


def _result_box(tex: str, font_size: int = 28) -> VGroup:
    """MathTex label inside a dark background box for readability over graphs."""
    label = MathTex(tex, font_size=font_size)
    box = SurroundingRectangle(
        label, color=WHITE, fill_color=BLACK,
        fill_opacity=0.75, buff=0.15, corner_radius=0.1,
    )
    return VGroup(box, label)


def _caption(text: str) -> Text:
    """Italic caption pinned to very bottom — shows lesson-plan step description."""
    return Text(text, font_size=19, color=GRAY, slant=ITALIC).to_edge(DOWN, buff=0.12)


# ---------------------------------------------------------------------------
# Scene 1 — Function Plot
# ---------------------------------------------------------------------------

class FunctionPlotScene(Scene):
    def construct(self):
        p = _load_params()
        expression = p.get("expression", "x**2")
        domain     = p.get("domain",     [-4, 4])
        x_point    = p.get("x_point")
        cap        = p.get("caption", "")

        expr, f, _ = _parse(expression)
        yr = _y_range(f, domain)
        ax = _make_axes(domain, yr)
        labels = ax.get_axis_labels(x_label="x", y_label="y")
        graph = ax.plot(f, x_range=domain, color=CURVE_COLOR, use_smoothing=True)
        title = MathTex(r"f(x) = " + _clip_latex(expr), font_size=36).to_edge(UP, buff=0.3)

        if cap:
            self.play(Write(_caption(cap)))

        self.play(Create(ax), Write(labels))
        self.play(Write(title))
        self.play(Create(graph), run_time=2)

        if x_point is not None:
            xp = float(x_point)
            yp = _safe_eval(f, xp)
            dot = Dot(ax.c2p(xp, yp), color=HIGHLIGHT_COLOR, radius=0.1)
            direction = UR if yp >= 0 else DR
            coord = _result_box(
                r"\left(" + _num(xp) + r",\ " + f"{yp:.2f}" + r"\right)", 24,
            ).next_to(dot, direction, buff=0.18)
            self.play(FadeIn(dot))
            self.play(Indicate(dot, color=HIGHLIGHT_COLOR, scale_factor=1.4))
            self.play(FadeIn(coord))

        self.wait(1.0)


# ---------------------------------------------------------------------------
# Scene 2 — Limit
# ---------------------------------------------------------------------------

class LimitScene(Scene):
    def construct(self):
        p = _load_params()
        expression = p.get("expression", "sin(x)/x")
        limit_pt   = float(p.get("limit_point", 0))
        domain     = p.get("domain",     [-5, 5])
        cap        = p.get("caption", "")

        expr, f, x_sym = _parse(expression)

        try:
            lim_val   = sp.limit(expr, x_sym, limit_pt)
            lim_float = float(lim_val)
            lim_tex   = sp.latex(lim_val)
        except Exception:
            lim_val   = None
            lim_float = None
            lim_tex   = r"\text{DNE}"

        yr = _y_range(f, domain)
        ax = _make_axes(domain, yr)
        labels = ax.get_axis_labels(x_label="x", y_label="y")

        eps = 0.08
        left_graph  = ax.plot(f, x_range=[domain[0], limit_pt - eps], color=CURVE_COLOR)
        right_graph = ax.plot(f, x_range=[limit_pt + eps, domain[1]], color=CURVE_COLOR)

        pt_tex = _num(limit_pt)
        title = MathTex(
            r"\lim_{x \to " + pt_tex + r"} f(x)", font_size=36,
        ).to_edge(UP, buff=0.3)

        if cap:
            self.play(Write(_caption(cap)))

        self.play(Create(ax), Write(labels), Write(title))
        self.play(Create(left_graph), Create(right_graph), run_time=1.5)

        # Left approach
        lt = ValueTracker(domain[0])
        left_dot = always_redraw(lambda: Dot(
            ax.c2p(lt.get_value(), _safe_eval(f, lt.get_value())),
            color=HIGHLIGHT_COLOR, radius=0.1,
        ))
        left_tag = MathTex(
            r"x \to " + pt_tex + r"^-", font_size=24, color=HIGHLIGHT_COLOR,
        ).to_corner(UL, buff=0.3)
        self.add(left_dot)
        self.play(Write(left_tag))
        self.play(lt.animate.set_value(limit_pt - eps), run_time=2.5)
        self.wait(0.5)

        # Right approach
        rt = ValueTracker(domain[1])
        right_dot = always_redraw(lambda: Dot(
            ax.c2p(rt.get_value(), _safe_eval(f, rt.get_value())),
            color=CRITICAL_COLOR, radius=0.1,
        ))
        right_tag = MathTex(
            r"x \to " + pt_tex + r"^+", font_size=24, color=CRITICAL_COLOR,
        ).to_corner(UR, buff=0.3)
        self.add(right_dot)
        self.play(Write(right_tag))
        self.play(rt.animate.set_value(limit_pt + eps), run_time=2.5)
        self.wait(0.5)

        if lim_float is not None:
            limit_dot = Dot(ax.c2p(limit_pt, lim_float), color=WHITE, radius=0.12)
            self.play(FadeIn(limit_dot))
            self.play(Indicate(limit_dot, scale_factor=1.5))
            result = _result_box(
                r"\lim_{x \to " + pt_tex + r"} f(x) = " + lim_tex, 28,
            ).to_edge(DOWN, buff=0.55)
            self.play(FadeIn(result))

        self.wait(1.0)


# ---------------------------------------------------------------------------
# Scene 3 — Tangent Line
# ---------------------------------------------------------------------------

class TangentLineScene(Scene):
    def construct(self):
        p = _load_params()
        expression = p.get("expression", "x**2")
        x_pt       = float(p.get("x_point", 1.0))
        domain     = p.get("domain",     [-4, 4])
        cap        = p.get("caption", "")

        expr, f, x_sym = _parse(expression)
        d_expr     = sp.diff(expr, x_sym)
        y0         = _safe_eval(f, x_pt)
        slope_sym  = d_expr.subs(x_sym, x_pt)

        yr  = _y_range(f, domain)
        ax  = _make_axes(domain, yr)
        labels = ax.get_axis_labels(x_label="x", y_label="y")
        graph  = ax.plot(f, x_range=domain, color=CURVE_COLOR)
        title  = MathTex(
            r"f(x) = " + _clip_latex(expr), font_size=34,
        ).to_edge(UP, buff=0.3)
        dot = Dot(ax.c2p(x_pt, y0), color=HIGHLIGHT_COLOR, radius=0.1)

        h_max = min(2.0, (domain[1] - domain[0]) * 0.35)
        h = ValueTracker(h_max)

        def _secant():
            hv = max(h.get_value(), 1e-5)
            s  = (_safe_eval(f, x_pt + hv) - _safe_eval(f, x_pt - hv)) / (2 * hv)
            return ax.plot(
                lambda x: y0 + s * (x - x_pt),
                x_range=domain, color=TANGENT_COLOR, stroke_width=2.5,
            )

        line = always_redraw(_secant)
        line_label = always_redraw(lambda: Text(
            "secant" if h.get_value() > 0.05 else "tangent",
            font_size=22, color=TANGENT_COLOR,
        ).to_corner(UR, buff=0.3))

        if cap:
            self.play(Write(_caption(cap)))

        self.play(Create(ax), Write(labels))
        self.play(Write(title), Create(graph))
        self.play(FadeIn(dot), Create(line), Write(line_label))
        self.play(h.animate.set_value(0.01), run_time=4, rate_func=smooth)

        self.play(Indicate(dot, color=HIGHLIGHT_COLOR, scale_factor=1.5))

        slope_result = _result_box(
            r"f'\!\left(" + _num(x_pt) + r"\right) = " + _clip_latex(slope_sym), 28,
        ).to_edge(DOWN, buff=0.55)
        self.play(FadeIn(slope_result))
        self.wait(1.5)


# ---------------------------------------------------------------------------
# Scene 4 — Riemann Sum
# ---------------------------------------------------------------------------

class RiemannSumScene(Scene):
    def construct(self):
        p = _load_params()
        expression = p.get("expression", "x**2")
        domain     = p.get("domain",     [0, 3])
        n_start    = int(p.get("n",      5))
        method     = p.get("method",     "left")
        cap        = p.get("caption", "")

        sample_map   = {"left": "left", "right": "right", "midpoint": "center"}
        manim_method = sample_map.get(method, "left")

        expr, f, x_sym = _parse(expression)
        yr = _y_range(f, domain)
        yr[0] = min(yr[0], -0.3)
        ax     = _make_axes(domain, yr)
        labels = ax.get_axis_labels(x_label="x", y_label="y")
        graph  = ax.plot(f, x_range=domain, color=CURVE_COLOR)

        try:
            exact     = float(sp.integrate(expr, (x_sym, domain[0], domain[1])))
            exact_str = f"{exact:.4f}"
        except Exception:
            exact_str = r"\cdots"

        a_tex, b_tex = _num(domain[0]), _num(domain[1])
        title = MathTex(
            r"\int_{" + a_tex + r"}^{" + b_tex + r"} " + _clip_latex(expr) + r"\, dx",
            font_size=34,
        ).to_edge(UP, buff=0.3)

        if cap:
            self.play(Write(_caption(cap)))

        self.play(Create(ax), Write(labels), Write(title))
        self.play(Create(graph), run_time=1.5)

        dx0   = (domain[1] - domain[0]) / n_start
        rects = ax.get_riemann_rectangles(
            graph, x_range=domain, dx=dx0,
            input_sample_type=manim_method, color=BLUE_D, fill_opacity=0.55,
        )
        n_label = MathTex(f"n = {n_start}", font_size=26).to_corner(DR, buff=0.3)
        self.play(FadeIn(rects), Write(n_label))
        self.wait(0.4)

        for n_new in [n_start * 3, n_start * 8, n_start * 20]:
            dx_new    = (domain[1] - domain[0]) / n_new
            new_rects = ax.get_riemann_rectangles(
                graph, x_range=domain, dx=dx_new,
                input_sample_type=manim_method, color=BLUE_D, fill_opacity=0.55,
            )
            new_label = MathTex(f"n = {n_new}", font_size=26).to_corner(DR, buff=0.3)
            self.play(
                Transform(rects, new_rects),
                Transform(n_label, new_label),
                run_time=0.9,
            )
            self.wait(0.25)

        exact_label = _result_box(r"= " + exact_str, 28).to_edge(DOWN, buff=0.55)
        self.play(FadeIn(exact_label))
        self.wait(1.0)


# ---------------------------------------------------------------------------
# Scene 5 — Critical Points
# ---------------------------------------------------------------------------

class CriticalPointsScene(Scene):
    def construct(self):
        p = _load_params()
        expression = p.get("expression", "x**3 - 3*x")
        domain     = p.get("domain",     [-3, 3])
        cap        = p.get("caption", "")

        expr, f, x_sym = _parse(expression)
        d_expr  = sp.diff(expr, x_sym)
        d2_expr = sp.diff(d_expr, x_sym)
        f_prime = sp.lambdify(x_sym, d_expr, modules=["numpy"])

        try:
            raw      = sp.solve(d_expr, x_sym)
            crit_pts = sorted([
                float(cp.evalf()) for cp in raw
                if cp.is_real and domain[0] <= float(cp.evalf()) <= domain[1]
            ])
        except Exception:
            crit_pts = []

        yr_f  = _y_range(f,       domain)
        yr_fp = _y_range(f_prime, domain)
        x_step = max(1, round((domain[1] - domain[0]) / 8))

        ax_f = Axes(
            x_range=[domain[0], domain[1], x_step],
            y_range=yr_f, x_length=7.5, y_length=2.5,
            axis_config={"color": WHITE, "include_numbers": True, "font_size": 16},
            tips=False,
        ).shift(UP * 1.85)

        ax_fp = Axes(
            x_range=[domain[0], domain[1], x_step],
            y_range=yr_fp, x_length=7.5, y_length=2.5,
            axis_config={"color": WHITE, "include_numbers": True, "font_size": 16},
            tips=False,
        ).shift(DOWN * 1.85)

        graph_f  = ax_f.plot(f,       x_range=domain, color=CURVE_COLOR)
        graph_fp = ax_fp.plot(f_prime, x_range=domain, color=DERIV_COLOR)

        # Dashed zero line on f' axes to show where derivative crosses zero
        zero_line = DashedLine(
            ax_fp.c2p(domain[0], 0), ax_fp.c2p(domain[1], 0),
            color=GRAY, dash_length=0.12, stroke_width=1.5,
        )

        lbl_f  = MathTex(r"f(x)",   font_size=20, color=CURVE_COLOR).next_to(ax_f,  LEFT, buff=0.35)
        lbl_fp = MathTex(r"f'(x)",  font_size=20, color=DERIV_COLOR).next_to(ax_fp, LEFT, buff=0.35)

        if cap:
            self.play(Write(_caption(cap)))

        self.play(Create(ax_f), Create(ax_fp), Write(lbl_f), Write(lbl_fp))
        self.play(Create(graph_f), Create(graph_fp), Create(zero_line), run_time=2)

        for cp in crit_pts:
            y_f = _safe_eval(f, cp)

            # Smart label direction: avoid top overflow
            y_frac = (y_f - yr_f[0]) / max(yr_f[1] - yr_f[0], 1e-6)
            lbl_dir = DOWN if y_frac > 0.75 else UP

            dot_f  = Dot(ax_f.c2p(cp, y_f), color=CRITICAL_COLOR, radius=0.1)
            dot_fp = Dot(ax_fp.c2p(cp, 0),  color=CRITICAL_COLOR, radius=0.1)

            s2   = float(d2_expr.subs(x_sym, cp).evalf())
            kind = "inflection" if abs(s2) < 1e-8 else ("local max" if s2 < 0 else "local min")
            cp_label = Text(kind, font_size=17, color=CRITICAL_COLOR).next_to(
                dot_f, lbl_dir, buff=0.12,
            )

            self.play(FadeIn(dot_f), FadeIn(dot_fp))
            self.play(Indicate(dot_f, color=CRITICAL_COLOR, scale_factor=1.4))
            self.play(Write(cp_label))

        self.wait(1.0)
