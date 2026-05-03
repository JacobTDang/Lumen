"""Unit tests for DSA visual primitives. No Manim render needed."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

from manim import Scene
from scenes.dsa_primitives import (
    ArrayStrip, Pointer, HighlightZone, HashMapPanel, StatePanel,
    ComparisonMarker, StackWidget, DependencyArc,
    GridPanel, BinaryTreePanel, RecursionTree, IntervalBars,
    DoublyLinkedListPanel, GraphPanel,
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


# ---------------------------------------------------------------------------
# GridPanel
# ---------------------------------------------------------------------------

def test_grid_panel_basic():
    g = GridPanel([[1, 2, 3], [4, 5, 6]])
    assert len(g.cells) == 2
    assert len(g.cells[0]) == 3
    assert g.cells[0][0] is not None


def test_grid_panel_animations():
    g = GridPanel([[0, 0], [0, 0]])
    assert g.anim_set_fill(0, 1, "RED") is not None
    assert g.anim_set_value(1, 0, 99) is not None
    assert g.flash(0, 0) is not None


def test_grid_panel_cell_centers_distinct():
    g = GridPanel([[1, 2, 3]])
    p0 = g.cell_center(0, 0)
    p1 = g.cell_center(0, 1)
    p2 = g.cell_center(0, 2)
    assert p0[0] < p1[0] < p2[0]


# ---------------------------------------------------------------------------
# BinaryTreePanel
# ---------------------------------------------------------------------------

def test_binary_tree_panel_basic():
    bt = BinaryTreePanel([1, 2, 3, 4, 5])
    assert len(bt.nodes) == 5
    assert len(bt.edges) == 4   # 5 nodes → 4 parent-child links


def test_binary_tree_panel_empty():
    bt = BinaryTreePanel([])
    assert bt.nodes == []
    assert bt.edges == []


def test_binary_tree_panel_animations():
    bt = BinaryTreePanel([10, 20, 30])
    assert bt.anim_set_value(0, 99) is not None
    assert bt.anim_set_fill(1, "GREEN") is not None
    assert bt.flash(2) is not None


# ---------------------------------------------------------------------------
# RecursionTree
# ---------------------------------------------------------------------------

def test_recursion_tree_starts_with_root():
    rt = RecursionTree("root")
    assert 0 in rt.nodes
    assert rt.depth[0] == 0


def test_recursion_tree_spawn():
    rt = RecursionTree("[]")
    nid, anims = rt.anim_spawn_child(0, "[1]")
    assert nid == 1
    assert rt.parent[nid] == 0
    assert rt.depth[nid] == 1
    assert len(anims) > 0


def test_recursion_tree_fade_subtree():
    rt = RecursionTree("[]")
    a, _ = rt.anim_spawn_child(0, "A")
    b, _ = rt.anim_spawn_child(a, "B")
    anims = rt.anim_fade_subtree(a)
    assert len(anims) >= 2  # node A + node B


# ---------------------------------------------------------------------------
# IntervalBars
# ---------------------------------------------------------------------------

def test_interval_bars_basic():
    iv = IntervalBars([[1, 3], [2, 6], [8, 10]])
    assert len(iv.bars) == 3
    assert iv.x_min < iv.x_max


def test_interval_bars_animations():
    iv = IntervalBars([[1, 4], [3, 6]])
    assert iv.anim_set_color(0, "GREEN") is not None
    anims = iv.anim_merge(0, 1, new_end=6)
    assert len(anims) == 2


def test_interval_bars_empty_safe():
    iv = IntervalBars([])
    assert iv.bars == []


# ---------------------------------------------------------------------------
# DoublyLinkedListPanel
# ---------------------------------------------------------------------------

def test_dll_starts_empty():
    dll = DoublyLinkedListPanel()
    assert dll.order() == []


def test_dll_add_to_head():
    dll = DoublyLinkedListPanel()
    dll.anim_add_to_head("a", 1)
    dll.anim_add_to_head("b", 2)
    assert dll.order() == ["b", "a"]


def test_dll_remove():
    dll = DoublyLinkedListPanel()
    dll.anim_add_to_head("a", 1)
    dll.anim_add_to_head("b", 2)
    dll.anim_remove("a")
    assert dll.order() == ["b"]


def test_dll_move_to_head():
    dll = DoublyLinkedListPanel()
    dll.anim_add_to_head("a", 1)
    dll.anim_add_to_head("b", 2)
    dll.anim_add_to_head("c", 3)
    dll.anim_move_to_head("a")
    assert dll.order() == ["a", "c", "b"]


def test_dll_remove_missing_safe():
    dll = DoublyLinkedListPanel()
    anims = dll.anim_remove("ghost")
    assert anims == []


# ---------------------------------------------------------------------------
# GraphPanel
# ---------------------------------------------------------------------------

def test_graph_panel_basic():
    g = GraphPanel(4, [[0, 1, 5], [1, 2, 3], [0, 3, 2]])
    assert len(g.nodes) == 4
    assert (0, 1) in g.edges
    assert (1, 2) in g.edges


def test_graph_panel_unweighted():
    g = GraphPanel(3, [[0, 1], [1, 2]])
    assert len(g.nodes) == 3
    assert (0, 1) in g.edges
    assert g.weight_lbls == {}


def test_graph_panel_animations():
    g = GraphPanel(3, [[0, 1, 5], [1, 2, 3]])
    assert g.anim_set_node_color(0, "GREEN") is not None
    assert g.anim_flash_edge(0, 1) is not None
    assert g.anim_set_node_value(1, "X") is not None
