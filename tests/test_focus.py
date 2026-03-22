"""Tests for LAYOUT-02: Keyboard focus switching between panels."""

import pytest

from nano_claude.app import NanoClaudeApp
from nano_claude.panels.base import BasePanel


def get_focused_panel_id(app) -> str | None:
    """Walk from app.focused up the parent chain to find the nearest BasePanel ancestor."""
    focused = app.focused
    if focused is None:
        return None
    node = focused
    while node is not None:
        if isinstance(node, BasePanel) and node.id is not None:
            return node.id
        node = node.parent
    return None


async def test_ctrl_b_focuses_file_tree():
    """Pressing Ctrl+b moves focus to a widget inside the #file-tree panel."""
    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("ctrl+b")
        assert get_focused_panel_id(app) == "file-tree"


async def test_ctrl_e_focuses_editor():
    """Pressing Ctrl+e moves focus to a widget inside the #editor panel."""
    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("ctrl+e")
        assert get_focused_panel_id(app) == "editor"


async def test_ctrl_r_focuses_chat():
    """Pressing Ctrl+r moves focus to a widget inside the #chat panel."""
    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("ctrl+r")
        assert get_focused_panel_id(app) == "chat"


async def test_tab_cycles_focus_through_panels():
    """Pressing Tab cycles focus forward through panels.

    Note: TextArea (code editor) consumes Tab for indentation when focused,
    so Tab cycling works from tree->editor but not out of editor. This is
    correct code-editor behavior. Use Ctrl+letter shortcuts for reliable
    panel switching (tested separately). This test verifies Tab works from
    panels that don't consume it (tree, chat).
    """
    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        # Start at file tree
        await pilot.press("ctrl+b")
        assert get_focused_panel_id(app) == "file-tree"
        # Tab from tree to editor works (DirectoryTree doesn't consume Tab)
        await pilot.press("tab")
        assert get_focused_panel_id(app) == "editor"
        # From editor, use Ctrl+r to move to chat (Tab consumed by TextArea for indent)
        await pilot.press("ctrl+r")
        assert get_focused_panel_id(app) == "chat"
        # Tab from chat cycles back to file tree
        await pilot.press("tab")
        assert get_focused_panel_id(app) == "file-tree"


async def test_focused_panel_has_focus_within():
    """After Ctrl+b, the file-tree panel has a focused child (triggers :focus-within)."""
    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("ctrl+b")
        panel = app.query_one("#file-tree")
        # The focused widget should be a descendant of the file-tree panel
        focused = app.focused
        assert focused is not None
        # Walk up from focused to verify it's inside the panel
        node = focused
        found = False
        while node is not None:
            if node is panel:
                found = True
                break
            node = node.parent
        assert found, "Focused widget is not inside #file-tree panel"


async def test_focus_on_hidden_panel_does_nothing():
    """Pressing Ctrl+b when file tree has class 'hidden' does not move focus there."""
    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        # First focus editor
        await pilot.press("ctrl+e")
        assert get_focused_panel_id(app) == "editor"
        # Hide file tree
        file_tree = app.query_one("#file-tree")
        file_tree.add_class("hidden")
        # Try to focus file tree -- should be ignored
        await pilot.press("ctrl+b")
        assert get_focused_panel_id(app) == "editor", "Focus should stay on editor when tree is hidden"


async def test_all_bindings_have_priority_and_id():
    """All BINDINGS entries have priority=True and an id parameter."""
    from textual.binding import Binding

    app = NanoClaudeApp()
    for binding in app.BINDINGS:
        if isinstance(binding, Binding):
            assert binding.priority is True, f"Binding {binding.key} missing priority=True"
            assert binding.id is not None and binding.id != "", f"Binding {binding.key} missing id"
