"""Tests for LAYOUT-03: Panel resizing and file tree toggle."""

import pytest

from nano_claude.app import NanoClaudeApp
from nano_claude.config.settings import DEFAULT_EDITOR_WIDTH, DEFAULT_TREE_WIDTH


def get_focused_panel_id(app) -> str | None:
    """Walk from app.focused up the parent chain to find the nearest BasePanel ancestor."""
    from nano_claude.panels.base import BasePanel

    focused = app.focused
    if focused is None:
        return None
    node = focused
    while node is not None:
        if isinstance(node, BasePanel) and node.id is not None:
            return node.id
        node = node.parent
    return None


async def test_ctrl_equal_grows_editor():
    """Pressing Ctrl+= while editor is focused increases editor_width by 0.5."""
    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("ctrl+e")
        original = app.editor_width
        await pilot.press("ctrl+equal")
        assert app.editor_width == pytest.approx(original + 0.5)


async def test_ctrl_minus_shrinks_editor():
    """Pressing Ctrl+- while editor is focused decreases editor_width by 0.5."""
    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("ctrl+e")
        original = app.editor_width
        await pilot.press("ctrl+minus")
        assert app.editor_width == pytest.approx(original - 0.5)


async def test_panel_width_minimum_enforced():
    """Panel width cannot go below 0.5 fr (pressing Ctrl+- many times stops at 0.5)."""
    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("ctrl+b")
        # Press minus many times to try to go below minimum
        for _ in range(20):
            await pilot.press("ctrl+minus")
        assert app.tree_width >= 0.5


async def test_ctrl_backslash_toggles_file_tree_hidden():
    """Pressing Ctrl+backslash adds 'hidden' class to file tree."""
    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        file_tree = app.query_one("#file-tree")
        assert not file_tree.has_class("hidden")
        await pilot.press("ctrl+backslash")
        assert file_tree.has_class("hidden")


async def test_ctrl_backslash_toggles_file_tree_visible():
    """Pressing Ctrl+backslash twice restores file tree visibility."""
    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        file_tree = app.query_one("#file-tree")
        # Hide
        await pilot.press("ctrl+backslash")
        assert file_tree.has_class("hidden")
        # Show
        await pilot.press("ctrl+backslash")
        assert not file_tree.has_class("hidden")


async def test_toggle_moves_focus_to_editor_when_tree_focused():
    """When file tree is focused and toggled hidden, focus moves to editor."""
    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        # Focus file tree
        await pilot.press("ctrl+b")
        assert get_focused_panel_id(app) == "file-tree"
        # Toggle hide -- focus should move to editor
        await pilot.press("ctrl+backslash")
        assert get_focused_panel_id(app) == "editor"
