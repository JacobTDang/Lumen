"""
Static linter for tool-call sequences.

Walks the calls in order tracking which element_ids and pointer names were
created, then flags any tool that references something not-yet-created. This
catches the most common LLM mistakes:

- Forward references ("move_pointer L" before "add_pointer L")
- Typos in element_id ("arr_0" vs "arr0")
- Pointers used without being added
- Hashmap entries set on non-existent panels

If lint returns issues, the agent can retry build_scene once with the issues
as guidance. The runtime executor already silently skips bad calls — this is
a planning-time signal so a retry can avoid the issue entirely.
"""
from __future__ import annotations

from typing import Iterable


# Tools that CREATE an element_id (the LLM is supposed to invent the id)
_CREATING = frozenset({
    "show_array", "show_hashmap", "show_stack", "show_grid",
    "show_code", "show_text", "show_equation",
})

# Tools that REFERENCE an element_id that should already exist
_REFERENCING_ELEMENT_ID = frozenset({
    "highlight_cells", "swap_cells", "set_cell_value",
    "push_stack", "pop_stack",
    "set_hashmap_entry", "delete_hashmap_entry",
    "highlight_code_line",
    "add_annotation", "emphasize", "fade_out_element",
})

# Pointer tools: add_pointer creates a name; move_pointer references it
_POINTER_CREATING  = "add_pointer"
_POINTER_REFERENCING = "move_pointer"


def lint_tool_calls(tool_calls: Iterable) -> list[str]:
    """Return a list of issue strings. Empty list means clean."""
    issues: list[str] = []
    seen_element_ids: set[str] = set()
    seen_pointer_names: set[str] = set()

    # add_pointer also needs an element_id (the array it attaches to). Track both.
    for i, call in enumerate(tool_calls):
        # Normalize from either ToolCall or plain dict
        if hasattr(call, "tool"):
            tool = call.tool
            args = call.args or {}
        elif isinstance(call, dict):
            tool = call.get("tool", "")
            args = call.get("args", {}) or {}
        else:
            issues.append(f"Call {i}: unrecognized shape ({type(call).__name__})")
            continue

        if tool in _CREATING:
            eid = args.get("element_id")
            if isinstance(eid, str) and eid:
                seen_element_ids.add(eid)

        elif tool == _POINTER_CREATING:
            name = args.get("name")
            eid = args.get("element_id")
            if isinstance(name, str) and name:
                seen_pointer_names.add(name)
            if isinstance(eid, str) and eid and eid not in seen_element_ids:
                issues.append(
                    f"Call {i} (add_pointer '{name}'): element_id "
                    f"'{eid}' was never created before."
                )

        elif tool == _POINTER_REFERENCING:
            name = args.get("name")
            eid = args.get("element_id")
            if isinstance(name, str) and name and name not in seen_pointer_names:
                issues.append(
                    f"Call {i} (move_pointer): pointer name "
                    f"'{name}' was never added before."
                )
            if isinstance(eid, str) and eid and eid not in seen_element_ids:
                issues.append(
                    f"Call {i} (move_pointer '{name}'): element_id "
                    f"'{eid}' was never created."
                )

        elif tool in _REFERENCING_ELEMENT_ID:
            eid = args.get("element_id")
            if isinstance(eid, str) and eid and eid not in seen_element_ids:
                issues.append(
                    f"Call {i} ({tool}): element_id '{eid}' "
                    f"was never created."
                )

        # set_caption, pause, show_result — no references to validate

    return issues
