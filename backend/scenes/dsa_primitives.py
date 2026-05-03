"""
Reusable visual primitives for DSA scenes.

Each primitive is a small self-contained class that builds Manim mobjects.
Primitives DO NOT call `self.play(...)` — they return mobjects that the
calling scene composes into animations. This makes them reusable, testable,
and easy to combine.

Shared color palette (use these consistently across all DSA scenes):
    DEFAULT_CELL = "#1a3a5c"    deep blue, unexamined cells
    HILITE       = YELLOW        currently being examined
    KEEP         = GREEN         matched / kept / answer
    REJECT       = RED           briefly, then faded back to default
    PTR_L        = GREEN
    PTR_R        = RED
    PTR_M        = YELLOW
    PTR_SLOW     = BLUE
    PTR_FAST     = ORANGE
"""
import json
import math
import os

from manim import *

# ---------------------------------------------------------------------------
# Shared palette
# ---------------------------------------------------------------------------
DEFAULT_CELL = "#1a3a5c"
HILITE       = YELLOW
KEEP         = GREEN
REJECT       = RED
PANEL_BG     = "#0d1117"

PTR_COLORS = {
    "L":     GREEN,
    "R":     RED,
    "M":     YELLOW,
    "slow":  BLUE,
    "fast":  ORANGE,
    "i":     YELLOW,
    "j":     "#8b5cf6",  # purple
}


# ---------------------------------------------------------------------------
# Shared helpers (parameter loading / title card / caption / result box)
# Re-implemented here so primitives module is self-contained.
# ---------------------------------------------------------------------------

def load_params() -> dict:
    job_id = os.environ.get("MANIM_JOB_ID")
    if job_id:
        temp_dir = os.environ.get("MANIM_TEMP_DIR", os.path.join("media", "temp"))
        path = os.path.join(temp_dir, f"{job_id}.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    return {}


def show_title_card(scene, text: str):
    import textwrap as _tw
    wrapped = _tw.fill(text, width=52)
    n = len(text)
    size = 28 if n < 45 else (24 if n < 70 else 20)
    card = Text(wrapped, font_size=size, color=WHITE, line_spacing=1.2)
    if card.width > 12.5:
        card.scale(12.5 / card.width)
    card.center()
    scene.play(FadeIn(card), run_time=0.35)
    scene.wait(1.4)
    scene.play(FadeOut(card), run_time=0.35)


def caption_strip(text: str) -> VGroup:
    """White-on-dark subtitle strip pinned at the bottom."""
    import textwrap as _tw
    wrapped = _tw.fill(text, width=72)
    bg  = Rectangle(width=14.5, height=0.65, fill_color=BLACK,
                    fill_opacity=0.82, stroke_width=0).to_edge(DOWN, buff=0)
    txt = Text(wrapped, font_size=21, color=WHITE).to_edge(DOWN, buff=0.13)
    if txt.width > 13.5:
        txt.scale(13.5 / txt.width)
    return VGroup(bg, txt)


def result_box(text: str, font_size: int = 28, use_text: bool = True) -> VGroup:
    """Boxed result label. Pass use_text=False for MathTex content."""
    if use_text:
        label = Text(text, font_size=font_size, color=WHITE)
    else:
        label = MathTex(text, font_size=font_size)
    box = SurroundingRectangle(
        label, color=WHITE, fill_color=BLACK,
        fill_opacity=0.75, buff=0.18, corner_radius=0.1,
    )
    return VGroup(box, label)


def action_text(msg: str, font_size: int = 22) -> VGroup:
    """Bottom-anchored action log line on a thin dark strip."""
    txt = Text(msg, font_size=font_size, color=WHITE)
    if txt.width > 13.0:
        txt.scale(13.0 / txt.width)
    bg = Rectangle(
        width=max(txt.width + 0.6, 4),
        height=txt.height + 0.25,
        fill_color=BLACK, fill_opacity=0.7, stroke_width=0,
    )
    grp = VGroup(bg, txt).to_edge(DOWN, buff=0.45)
    return grp


# ---------------------------------------------------------------------------
# Primitive 1 — ArrayStrip
# ---------------------------------------------------------------------------

class ArrayStrip:
    """
    A horizontal row of cells (Square + Text). Adaptive size based on length.

    Construction:
        strip = ArrayStrip([1, 3, 5, 7], position=UP*0.5)

    Properties:
        .cells       — list[VGroup(square, text)]
        .vgroup      — the whole row as a VGroup
        .indices     — VGroup of small index labels below cells

    Methods (all return mobjects suitable for self.play(...)):
        .anim_set_fill(i, color, opacity=0.7)
        .anim_set_value(i, new_value)
        .flash(i, color=YELLOW, scale=1.2)
        .cell_top(i)    -> point
        .cell_bottom(i) -> point
        .cell_center(i) -> point
    """

    def __init__(self, values: list, position=ORIGIN,
                 cell_size: float = None, with_indices: bool = True):
        self.values = list(values)
        n = len(values)

        if cell_size is None:
            cell_size = (1.0 if n <= 4 else
                         0.85 if n <= 7 else
                         0.70 if n <= 10 else
                         max(0.50, 9.0 / n))
        self.cell_size = cell_size
        font = max(16, int(24 * cell_size))

        self.cells = []
        for v in values:
            sq = Square(side_length=cell_size,
                        fill_color=DEFAULT_CELL, fill_opacity=0.70,
                        stroke_color=WHITE, stroke_width=2)
            lbl = Text(str(v), font_size=font, color=WHITE)
            cell = VGroup(sq, lbl)
            self.cells.append(cell)

        self.vgroup = VGroup(*self.cells).arrange(RIGHT, buff=0.10).move_to(position)

        self.indices = VGroup()
        if with_indices:
            for i, c in enumerate(self.cells):
                ix = Text(str(i), font_size=max(13, int(15 * cell_size)),
                          color=GRAY).next_to(c, DOWN, buff=0.05)
                self.indices.add(ix)

    def anim_set_fill(self, i: int, color, opacity: float = 0.75):
        return self.cells[i][0].animate.set_fill(color, opacity=opacity)

    def anim_set_value(self, i: int, new_value):
        new_lbl = Text(str(new_value),
                       font_size=max(16, int(24 * self.cell_size)),
                       color=WHITE).move_to(self.cells[i][1].get_center())
        return Transform(self.cells[i][1], new_lbl)

    def flash(self, i: int, color=YELLOW, scale: float = 1.2):
        return Indicate(self.cells[i][0], color=color, scale_factor=scale)

    def cell_top(self, i: int):
        return self.cells[i].get_top()

    def cell_bottom(self, i: int):
        return self.cells[i].get_bottom()

    def cell_center(self, i: int):
        return self.cells[i].get_center()

    def set_default(self, i: int):
        """Synchronously reset a cell's fill (no animation)."""
        self.cells[i][0].set_fill(DEFAULT_CELL, opacity=0.70)


# ---------------------------------------------------------------------------
# Primitive 2 — Pointer
# ---------------------------------------------------------------------------

class Pointer:
    """
    A labeled colored arrow pointing UP at cells (placed below).

    Pointer("L", color=GREEN, role="below")  -> arrow points up at cell from below
    Pointer("M", color=YELLOW, role="below_lower")  -> placed lower (for L/M/R stacks)

    Methods:
        .place_below(strip, idx, extra_down=0)
        .anim_move_to(strip, idx, extra_down=0)
        .vgroup       -> the mobject
    """

    def __init__(self, label: str, color=YELLOW, label_size: int = 16):
        self.label = label
        self.color = color
        self._arrow = Arrow(DOWN * 0.45, ORIGIN, color=color, buff=0,
                            max_tip_length_to_length_ratio=0.40, stroke_width=2.5)
        self._lbl = Text(label, font_size=label_size, color=color, weight=BOLD)
        self._lbl.next_to(self._arrow.get_start(), DOWN, buff=0.04)
        self.vgroup = VGroup(self._arrow, self._lbl)

    def place_below(self, strip: ArrayStrip, idx: int, extra_down: float = 0.0):
        target = strip.cell_bottom(idx) + DOWN * (0.30 + extra_down)
        self.vgroup.move_to(target)
        return self

    def anim_move_to(self, strip: ArrayStrip, idx: int, extra_down: float = 0.0):
        target = strip.cell_bottom(idx) + DOWN * (0.30 + extra_down)
        return self.vgroup.animate.move_to(target)


# ---------------------------------------------------------------------------
# Primitive 3 — HighlightZone
# ---------------------------------------------------------------------------

class HighlightZone:
    """
    A SurroundingRectangle around contiguous cells of an ArrayStrip.
    Used for sliding windows.

    Methods:
        .wrap(strip, start, end, color=YELLOW)  -> the rectangle
        .anim_to(strip, start, end)             -> transform animation
    """

    def __init__(self, strip: ArrayStrip, start: int, end: int,
                 color=YELLOW, stroke_width: float = 2.5):
        self.strip = strip
        self.color = color
        self.stroke_width = stroke_width
        self._rect = self._build(start, end)

    @property
    def rect(self):
        return self._rect

    def _build(self, start: int, end: int):
        return SurroundingRectangle(
            VGroup(*self.strip.cells[start:end + 1]),
            color=self.color, buff=0.08, corner_radius=0.06,
            stroke_width=self.stroke_width,
        )

    def anim_to(self, start: int, end: int):
        new_rect = self._build(start, end)
        return Transform(self._rect, new_rect)


# ---------------------------------------------------------------------------
# Primitive 4 — HashMapPanel
# ---------------------------------------------------------------------------

class HashMapPanel:
    """
    Sidebar showing key:value entries that update over time.

    Constructor pins it to a corner; entries appear as rows.
    Auto-clamps width to avoid screen overflow.

    Methods (return list of animations to play together):
        .anim_set(k, v) -> list of Animations to update display
        .anim_delete(k) -> list of Animations
        .anim_flash(k)  -> Indicate animation on a key
        .vgroup         -> the whole panel
    """

    def __init__(self, anchor=UR, title: str = "HashMap",
                 max_rows: int = 8):
        self.anchor = anchor
        self.title_text = title
        self.max_rows = max_rows
        self._entries = {}      # key -> VGroup(key_text, sep, val_text)
        self._title = Text(title, font_size=20, color=YELLOW, weight=BOLD)
        self._bg    = Rectangle(width=2.6, height=0.7,
                                 fill_color=PANEL_BG, fill_opacity=0.92,
                                 stroke_color=GRAY, stroke_width=1.2)
        self._bg.surround(self._title, buff=0.18)
        self.vgroup = VGroup(self._bg, self._title)
        self.vgroup.to_corner(anchor, buff=0.3)

    def _make_row(self, k, v):
        k_txt = Text(str(k), font_size=18, color=WHITE)
        sep   = Text(":", font_size=18, color=GRAY)
        v_txt = Text(str(v), font_size=18, color=GREEN)
        row = VGroup(k_txt, sep, v_txt).arrange(RIGHT, buff=0.12)
        return row, k_txt, v_txt

    def _rebuild_layout(self):
        """Recompute panel layout: title on top, rows beneath."""
        rows = list(self._entries.values())
        if not rows:
            content = self._title
        else:
            stacked = VGroup(self._title, *rows).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
            content = stacked
        # Build new bg around content
        new_bg = Rectangle(
            width=max(content.width + 0.4, 2.6),
            height=content.height + 0.4,
            fill_color=PANEL_BG, fill_opacity=0.92,
            stroke_color=GRAY, stroke_width=1.2,
        ).move_to(content.get_center())
        return new_bg, content

    def anim_set(self, key, value):
        """Add or update key. Returns animations."""
        anims = []
        if key in self._entries:
            row = self._entries[key]
            new_v = Text(str(value), font_size=18, color=GREEN).move_to(row[2].get_center())
            anims.append(Transform(row[2], new_v))
        else:
            row, _, _ = self._make_row(key, value)
            self._entries[key] = row
            anims.append(FadeIn(row, shift=LEFT * 0.2))
        # Re-anchor entire panel after changes
        self._reanchor()
        return anims

    def _reanchor(self):
        """Rebuild background to fit new content and pin to corner."""
        rows = list(self._entries.values())
        if rows:
            content = VGroup(self._title, *rows).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        else:
            content = self._title

        new_bg = Rectangle(
            width=max(content.width + 0.4, 2.6),
            height=content.height + 0.4,
            fill_color=PANEL_BG, fill_opacity=0.92,
            stroke_color=GRAY, stroke_width=1.2,
        )
        # Position: corner-anchored
        new_grp = VGroup(new_bg, content)
        new_grp.to_corner(self.anchor, buff=0.3)

        # Mutate existing bg & vgroup to match
        self._bg.become(new_bg)
        self.vgroup.move_to(new_grp.get_center())

    def anim_delete(self, key):
        if key not in self._entries:
            return []
        row = self._entries.pop(key)
        anim = FadeOut(row, shift=RIGHT * 0.2)
        self._reanchor()
        return [anim]

    def anim_flash(self, key, color=YELLOW):
        if key not in self._entries:
            return []
        return [Indicate(self._entries[key], color=color, scale_factor=1.15)]


# ---------------------------------------------------------------------------
# Primitive 5 — StatePanel
# ---------------------------------------------------------------------------

class StatePanel:
    """
    Sidebar for variable values (like a debugger watch).

    Methods:
        .anim_set(name, val, color=WHITE)  -> animations
        .vgroup                              -> the panel
    """

    def __init__(self, anchor=UL, title: str = "State"):
        self.anchor = anchor
        self.title_text = title
        self._entries = {}
        self._title = Text(title, font_size=20, color=YELLOW, weight=BOLD)
        self._bg = Rectangle(width=2.4, height=0.7,
                              fill_color=PANEL_BG, fill_opacity=0.92,
                              stroke_color=GRAY, stroke_width=1.2)
        self._bg.surround(self._title, buff=0.18)
        self.vgroup = VGroup(self._bg, self._title)
        self.vgroup.to_corner(anchor, buff=0.3)

    def _make_row(self, name, val, color):
        n_txt = Text(f"{name} =", font_size=18, color=GRAY)
        v_txt = Text(str(val), font_size=18, color=color, weight=BOLD)
        row = VGroup(n_txt, v_txt).arrange(RIGHT, buff=0.10)
        return row, v_txt

    def _reanchor(self):
        rows = list(self._entries.values())
        if rows:
            content = VGroup(self._title, *[r[0] for r in rows]).arrange(
                DOWN, aligned_edge=LEFT, buff=0.10)
        else:
            content = self._title
        new_bg = Rectangle(
            width=max(content.width + 0.4, 2.4),
            height=content.height + 0.4,
            fill_color=PANEL_BG, fill_opacity=0.92,
            stroke_color=GRAY, stroke_width=1.2,
        )
        new_grp = VGroup(new_bg, content)
        new_grp.to_corner(self.anchor, buff=0.3)
        self._bg.become(new_bg)
        self.vgroup.move_to(new_grp.get_center())

    def anim_set(self, name: str, val, color=WHITE):
        anims = []
        if name in self._entries:
            old_row, old_v = self._entries[name]
            new_v = Text(str(val), font_size=18, color=color, weight=BOLD)
            new_v.move_to(old_v.get_center())
            anims.append(Transform(old_v, new_v))
        else:
            row, v_txt = self._make_row(name, val, color)
            self._entries[name] = (row, v_txt)
            anims.append(FadeIn(row, shift=LEFT * 0.2))
        self._reanchor()
        return anims


# ---------------------------------------------------------------------------
# Primitive 6 — ComparisonMarker
# ---------------------------------------------------------------------------

class ComparisonMarker:
    """
    A symbol shown between two cells indicating a comparison result.
    Usage:
        marker = ComparisonMarker.between(strip, i, j, "==", color=GREEN)
        scene.play(FadeIn(marker.vgroup))

    Symbols supported: "==", "!=", "<", ">", "<=", ">=", "+", "->"
    """

    def __init__(self, vgroup):
        self.vgroup = vgroup

    @classmethod
    def between(cls, strip: ArrayStrip, i: int, j: int,
                symbol: str = "==", color=YELLOW):
        center_i = strip.cell_center(i)
        center_j = strip.cell_center(j)
        midpoint = (center_i + center_j) / 2 + UP * (strip.cell_size + 0.3)

        sym_text = symbol.replace("==", "=").replace("!=", "≠").replace(
            "<=", "≤").replace(">=", "≥").replace("->", "→")
        txt = Text(sym_text, font_size=28, color=color, weight=BOLD)
        bg = Circle(radius=0.25, color=color, fill_color=BLACK,
                     fill_opacity=0.9, stroke_width=2)
        grp = VGroup(bg, txt).move_to(midpoint)
        return cls(grp)


# ---------------------------------------------------------------------------
# Primitive 7 — StackWidget
# ---------------------------------------------------------------------------

class StackWidget:
    """
    Vertical stack of values. Items pushed at the top.

    Methods:
        .anim_push(val, color=BLUE_D)  -> tuple (item_mob, animations_list)
        .anim_pop()                    -> animations list (item flies up + fades)
        .top_value()
        .vgroup                        -> container + items
    """

    def __init__(self, position=ORIGIN, max_visible: int = 7,
                 cell_w: float = 1.4, cell_h: float = 0.55,
                 title: str = "Stack"):
        self.position = position
        self.max_visible = max_visible
        self.cell_w = cell_w
        self.cell_h = cell_h
        self._items = []  # list of (value, vgroup)
        self._container = Rectangle(
            width=cell_w + 0.18, height=max_visible * cell_h + 0.18,
            color=WHITE, stroke_width=2, fill_opacity=0,
        ).move_to(position)
        self._title = Text(title, font_size=18, color=GRAY).next_to(
            self._container, UP, buff=0.15)
        self.vgroup = VGroup(self._container, self._title)

    def _slot_y(self, idx: int) -> float:
        """Y-coord for stack slot idx (0 = bottom)."""
        return self._container.get_bottom()[1] + self.cell_h / 2 + 0.08 + idx * self.cell_h

    def _make_item(self, val, color=BLUE_D):
        rect = Rectangle(width=self.cell_w - 0.08, height=self.cell_h - 0.06,
                          fill_color=color, fill_opacity=0.78,
                          stroke_color=WHITE, stroke_width=1.3)
        lbl = Text(str(val), font_size=18, color=WHITE)
        return VGroup(rect, lbl)

    def anim_push(self, val, color=BLUE_D):
        item = self._make_item(val, color)
        target_y = self._slot_y(len(self._items))
        target_x = self._container.get_center()[0]
        # Item starts above the container, slides into slot
        item.move_to(np.array([target_x, target_y + 2.5, 0]))
        anim = item.animate.move_to(np.array([target_x, target_y, 0]))
        self._items.append((val, item))
        return item, [anim]

    def anim_pop(self):
        if not self._items:
            return None, []
        val, item = self._items.pop()
        # Item flies up and fades
        return val, [
            item.animate.shift(UP * 1.5 + RIGHT * 1.0),
            FadeOut(item),
        ]

    def top_value(self):
        return self._items[-1][0] if self._items else None


# ---------------------------------------------------------------------------
# Primitive 8 — DependencyArc
# ---------------------------------------------------------------------------

class DependencyArc:
    """
    Curved arrow between two cells (used for DP scenes to show dp[i] depends on dp[j]).
    """

    @staticmethod
    def above(strip: ArrayStrip, dep_idx: int, target_idx: int,
              color=TEAL, angle=-PI / 3, stroke_width: float = 2):
        return CurvedArrow(
            strip.cell_top(dep_idx) + UP * 0.05,
            strip.cell_top(target_idx) + UP * 0.05,
            color=color, angle=angle, stroke_width=stroke_width,
        )
