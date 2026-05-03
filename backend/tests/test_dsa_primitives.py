"""Unit tests for DSA visual primitives. No Manim render needed."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

from manim import Scene
from scenes.dsa_primitives import (
    ArrayStrip, Pointer, HighlightZone, HashMapPanel, StatePanel,
    ComparisonMarker, StackWidget, DependencyArc,
    DEFAULT_CELL, HILITE, KEEP, REJECT, PTR_COLORS,
    caption_strip, result_box, action_text,
)


# ---------------------------------------------------------------------------
# ArrayStrip
# ---------------------------------------------------------------------------

def test_array_strip_basic():
    strip = ArrayStrip([1, 2, 3, 4])
    assert len(strip.cells) == 4
    assert strip.cell_size > 0
    assert len(strip.indices) == 4


def test_array_strip_adaptive_sizing():
    """Cell size should shrink as length increases."""
    s_small  = ArrayStrip([1, 2, 3])
    s_med    = ArrayStrip(list(range(8)))
    s_large  = ArrayStrip(list(range(15)))
    assert s_small.cell_size > s_med.cell_size
    assert s_med.cell_size > s_large.cell_size


def test_array_strip_no_indices():
    strip = ArrayStrip([1, 2, 3], with_indices=False)
    assert len(strip.indices) == 0


def test_array_strip_cell_positions_distinct():
    strip = ArrayStrip([1, 2, 3])
    p0 = strip.cell_center(0)
    p1 = strip.cell_center(1)
    p2 = strip.cell_center(2)
    assert p0[0] < p1[0] < p2[0]   # increasing x


def test_array_strip_animations_return_animatable():
    strip = ArrayStrip([1, 2, 3])
    # These should return mobjects/animations, not be None
    assert strip.anim_set_fill(0, "RED") is not None
    assert strip.anim_set_value(0, 99) is not None
    assert strip.flash(0) is not None


# ---------------------------------------------------------------------------
# Pointer
# ---------------------------------------------------------------------------

def test_pointer_basic():
    p = Pointer("L", color="GREEN")
    assert p.label == "L"
    assert p.vgroup is not None


def test_pointer_placed_below_cell():
    strip = ArrayStrip([1, 2, 3, 4])
    p = Pointer("M", color="YELLOW").place_below(strip, 2)
    # Pointer should be near the bottom of cell 2
    cell_bot = strip.cell_bottom(2)
    p_pos = p.vgroup.get_center()
    # Same x (within tolerance), pointer below cell
    assert abs(p_pos[0] - cell_bot[0]) < 0.1
    assert p_pos[1] < cell_bot[1]


# ---------------------------------------------------------------------------
# HighlightZone
# ---------------------------------------------------------------------------

def test_highlight_zone_wraps_cells():
    strip = ArrayStrip([1, 2, 3, 4, 5])
    zone = HighlightZone(strip, 1, 3)
    # Rect should span horizontally over cells 1..3
    assert zone.rect.width >= strip.cells[1].width  # at least one cell wide


def test_highlight_zone_anim_to_returns_transform():
    strip = ArrayStrip([1, 2, 3, 4, 5])
    zone = HighlightZone(strip, 0, 2)
    anim = zone.anim_to(1, 4)
    assert anim is not None


# ---------------------------------------------------------------------------
# HashMapPanel
# ---------------------------------------------------------------------------

def test_hashmap_panel_starts_empty():
    panel = HashMapPanel()
    assert len(panel._entries) == 0


def test_hashmap_panel_set_adds_entry():
    panel = HashMapPanel()
    anims = panel.anim_set("a", 3)
    assert "a" in panel._entries
    assert len(anims) > 0


def test_hashmap_panel_set_existing_updates():
    panel = HashMapPanel()
    panel.anim_set("a", 1)
    anims = panel.anim_set("a", 5)  # update existing
    assert "a" in panel._entries
    assert len(anims) > 0  # should produce a Transform animation


def test_hashmap_panel_delete():
    panel = HashMapPanel()
    panel.anim_set("a", 1)
    anims = panel.anim_delete("a")
    assert "a" not in panel._entries
    assert len(anims) > 0


def test_hashmap_panel_delete_missing_no_error():
    panel = HashMapPanel()
    anims = panel.anim_delete("ghost")
    assert anims == []


# ---------------------------------------------------------------------------
# StatePanel
# ---------------------------------------------------------------------------

def test_state_panel_starts_empty():
    panel = StatePanel()
    assert len(panel._entries) == 0


def test_state_panel_set_adds_var():
    panel = StatePanel()
    anims = panel.anim_set("count", 0)
    assert "count" in panel._entries
    assert len(anims) > 0


def test_state_panel_update_existing_var():
    panel = StatePanel()
    panel.anim_set("i", 0)
    anims = panel.anim_set("i", 5)
    assert len(anims) > 0


# ---------------------------------------------------------------------------
# ComparisonMarker
# ---------------------------------------------------------------------------

def test_comparison_marker_between():
    strip = ArrayStrip([1, 2, 3])
    m = ComparisonMarker.between(strip, 0, 2, "==")
    assert m.vgroup is not None
    # Should be positioned above the cells
    assert m.vgroup.get_center()[1] > strip.cell_center(0)[1]


def test_comparison_marker_translates_symbols():
    strip = ArrayStrip([1, 2, 3])
    # Should not raise
    ComparisonMarker.between(strip, 0, 1, "!=")
    ComparisonMarker.between(strip, 0, 1, "<")
    ComparisonMarker.between(strip, 0, 1, ">=")


# ---------------------------------------------------------------------------
# StackWidget
# ---------------------------------------------------------------------------

def test_stack_widget_basic():
    s = StackWidget()
    assert s.top_value() is None
    assert s._items == []


def test_stack_widget_push():
    s = StackWidget()
    item, anims = s.anim_push(5)
    assert s.top_value() == 5
    assert item is not None
    assert len(anims) > 0


def test_stack_widget_pop_returns_value():
    s = StackWidget()
    s.anim_push(7)
    s.anim_push(11)
    val, anims = s.anim_pop()
    assert val == 11
    assert s.top_value() == 7
    assert len(anims) > 0


def test_stack_widget_pop_empty():
    s = StackWidget()
    val, anims = s.anim_pop()
    assert val is None
    assert anims == []


# ---------------------------------------------------------------------------
# DependencyArc
# ---------------------------------------------------------------------------

def test_dependency_arc_above():
    strip = ArrayStrip(list(range(6)))
    arc = DependencyArc.above(strip, 1, 4)
    assert arc is not None


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def test_caption_strip():
    cap = caption_strip("Hello world")
    assert cap is not None


def test_result_box_text_mode():
    rb = result_box("Found!", use_text=True)
    assert rb is not None


def test_action_text():
    a = action_text("Step 1: i = 0")
    assert a is not None


# ---------------------------------------------------------------------------
# Constants exported
# ---------------------------------------------------------------------------

def test_constants_exist():
    assert DEFAULT_CELL == "#1a3a5c"
    assert "L" in PTR_COLORS
    assert "slow" in PTR_COLORS
    assert "fast" in PTR_COLORS
