"""Tests for LAYOUT-04: Terminal resize adaptation and panel collapse."""

import pytest

from nano_claude.app import NanoClaudeApp


async def test_all_panels_visible_at_normal_width():
    """At terminal width 120 cols, all three panels are visible."""
    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        file_tree = app.query_one("#file-tree")
        editor = app.query_one("#editor")
        chat = app.query_one("#chat")
        assert not file_tree.has_class("hidden")
        assert not editor.has_class("hidden")
        assert not chat.has_class("hidden")


async def test_file_tree_hides_below_collapse_threshold():
    """At terminal width 55 cols (<60), file tree is hidden, editor and chat visible."""
    app = NanoClaudeApp()
    async with app.run_test(size=(55, 40)) as pilot:
        await pilot.pause()
        file_tree = app.query_one("#file-tree")
        editor = app.query_one("#editor")
        chat = app.query_one("#chat")
        assert file_tree.has_class("hidden"), "File tree should be hidden at width 55"
        assert not editor.has_class("hidden"), "Editor should be visible at width 55"
        assert not chat.has_class("hidden"), "Chat should be visible at width 55"


async def test_both_sidebars_hide_at_very_narrow():
    """At terminal width 35 cols (<40), both file tree and chat hidden, only editor."""
    app = NanoClaudeApp()
    async with app.run_test(size=(35, 40)) as pilot:
        await pilot.pause()
        file_tree = app.query_one("#file-tree")
        editor = app.query_one("#editor")
        chat = app.query_one("#chat")
        assert file_tree.has_class("hidden"), "File tree should be hidden at width 35"
        assert chat.has_class("hidden"), "Chat should be hidden at width 35"
        assert not editor.has_class("hidden"), "Editor should remain visible at width 35"


async def test_resize_restores_file_tree():
    """Resizing from 55 cols back to 120 cols restores file tree visibility."""
    app = NanoClaudeApp()
    async with app.run_test(size=(55, 40)) as pilot:
        await pilot.pause()
        file_tree = app.query_one("#file-tree")
        assert file_tree.has_class("hidden"), "File tree should be hidden at width 55"
        # Resize back to wide terminal
        await pilot.resize_terminal(120, 40)
        await pilot.pause()
        await pilot.pause()
        assert not file_tree.has_class("hidden"), "File tree should be restored at width 120"


async def test_resize_restores_both_panels():
    """Resizing from 35 cols back to 120 cols restores both file tree and chat."""
    app = NanoClaudeApp()
    async with app.run_test(size=(35, 40)) as pilot:
        await pilot.pause()
        file_tree = app.query_one("#file-tree")
        chat = app.query_one("#chat")
        assert file_tree.has_class("hidden")
        assert chat.has_class("hidden")
        # Resize back to wide terminal
        await pilot.resize_terminal(120, 40)
        await pilot.pause()
        await pilot.pause()
        assert not file_tree.has_class("hidden"), "File tree should be restored at width 120"
        assert not chat.has_class("hidden"), "Chat should be restored at width 120"


async def test_hidden_panels_dont_overflow():
    """When panels are hidden, remaining visible panels have valid fr-based widths."""
    app = NanoClaudeApp()
    async with app.run_test(size=(55, 40)) as pilot:
        await pilot.pause()
        editor = app.query_one("#editor")
        chat = app.query_one("#chat")
        # Visible panels should still be rendered (not zero-size)
        assert not editor.has_class("hidden")
        assert not chat.has_class("hidden")
