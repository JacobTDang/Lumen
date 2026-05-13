"""Tests for static tool-call validation (agent/tool_linter.py)."""

from agent.tool_linter import lint_tool_calls


def _c(tool, **args):
    return {"tool": tool, "args": args}


def test_clean_scene_returns_no_issues():
    calls = [
        _c("set_caption", text="hello"),
        _c("show_array", values=["1", "2"], element_id="arr"),
        _c("add_pointer", name="L", element_id="arr", index=0),
        _c("move_pointer", name="L", element_id="arr", to_index=1),
        _c("highlight_cells", element_id="arr", indices=[0]),
        _c("emphasize", element_id="arr"),
        _c("pause", beats=2),
        _c("show_result", value="ok"),
    ]
    assert lint_tool_calls(calls) == []


def test_flags_unknown_element_id_in_highlight():
    calls = [
        _c("show_array", values=["1"], element_id="arr"),
        _c("highlight_cells", element_id="wrong_id", indices=[0]),
    ]
    issues = lint_tool_calls(calls)
    assert any("wrong_id" in i for i in issues)


def test_flags_move_pointer_without_add():
    calls = [
        _c("show_array", values=["1"], element_id="arr"),
        _c("move_pointer", name="L", element_id="arr", to_index=0),
    ]
    issues = lint_tool_calls(calls)
    assert any("pointer name 'L'" in i for i in issues)


def test_flags_add_pointer_referencing_unknown_array():
    calls = [
        _c("add_pointer", name="L", element_id="missing", index=0),
    ]
    issues = lint_tool_calls(calls)
    assert any("'missing'" in i for i in issues)


def test_flags_hashmap_entry_on_missing_panel():
    calls = [
        _c("set_hashmap_entry", element_id="not_created", key="k", value="v"),
    ]
    issues = lint_tool_calls(calls)
    assert any("not_created" in i for i in issues)


def test_accepts_pointer_after_array_creation():
    calls = [
        _c("show_array", values=["1"], element_id="arr"),
        _c("add_pointer", name="L", element_id="arr", index=0),
        _c("move_pointer", name="L", element_id="arr", to_index=0),
    ]
    assert lint_tool_calls(calls) == []


def test_handles_toolcall_dataclass_shape():
    """The linter must accept ToolCall objects (from lesson_director) too."""
    from agent.lesson_director import ToolCall
    calls = [
        ToolCall(tool="show_array", args={"values": ["1"], "element_id": "arr"}),
        ToolCall(tool="emphasize", args={"element_id": "arr"}),
    ]
    assert lint_tool_calls(calls) == []


def test_flags_unknown_call_shape():
    issues = lint_tool_calls([12345])  # not a dict, not a ToolCall
    assert any("unrecognized shape" in i for i in issues)
