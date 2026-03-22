"""Tests for LAYOUT-01: Three-panel layout structure and startup content."""

import os
from pathlib import Path

import pytest

from nano_claude.app import NanoClaudeApp
from nano_claude.panels.base import BasePanel


async def test_three_panels_exist_in_main_panels():
    """App composes with exactly 3 child panels inside #main-panels container."""
    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        main = app.query_one("#main-panels")
        file_tree = app.query_one("#file-tree")
        editor = app.query_one("#editor")
        chat = app.query_one("#chat")
        assert file_tree is not None
        assert editor is not None
        assert chat is not None
        # All three should be children of #main-panels
        panels = [child for child in main.children if isinstance(child, BasePanel)]
        assert len(panels) == 3


async def test_header_and_footer_exist():
    """App has a Header widget and a Footer widget."""
    from textual.widgets import Footer, Header

    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        header = app.query_one(Header)
        footer = app.query_one(Footer)
        assert header is not None
        assert footer is not None


async def test_panels_are_basepanel_subclasses():
    """FileTreePanel, EditorPanel, ChatPanel are all instances of BasePanel."""
    from nano_claude.panels.chat import ChatPanel
    from nano_claude.panels.editor import EditorPanel
    from nano_claude.panels.file_tree import FileTreePanel

    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        file_tree = app.query_one("#file-tree")
        editor = app.query_one("#editor")
        chat = app.query_one("#chat")
        assert isinstance(file_tree, BasePanel)
        assert isinstance(file_tree, FileTreePanel)
        assert isinstance(editor, BasePanel)
        assert isinstance(editor, EditorPanel)
        assert isinstance(chat, BasePanel)
        assert isinstance(chat, ChatPanel)


async def test_panels_have_focusable_children():
    """Each panel contains a focusable placeholder widget."""
    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        for panel_id in ("file-tree", "editor", "chat"):
            panel = app.query_one(f"#{panel_id}")
            focusable = [w for w in panel.walk_children() if w.can_focus]
            assert len(focusable) >= 1, f"Panel #{panel_id} has no focusable children"


async def test_app_title_is_nano_claude():
    """App title is 'nano-claude'."""
    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        assert app.title == "nano-claude"


async def test_cli_entry_point_exists():
    """CLI entry point parses optional path argument."""
    from nano_claude.cli import main

    assert callable(main)


async def test_editor_shows_readme_when_exists(tmp_path, monkeypatch):
    """When README.md exists in cwd, the editor placeholder contains 'README.md'."""
    readme = tmp_path / "README.md"
    readme.write_text("# Test Project")
    monkeypatch.chdir(tmp_path)
    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        placeholder = app.query_one("#editor-placeholder")
        assert "README.md" in placeholder.renderable


async def test_editor_shows_welcome_when_no_readme(tmp_path, monkeypatch):
    """When no README.md exists, editor shows welcome text with shortcut hints."""
    monkeypatch.chdir(tmp_path)
    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        placeholder = app.query_one("#editor-placeholder")
        text = str(placeholder.renderable)
        assert "Ctrl+b" in text
        assert "Ctrl+e" in text
        assert "Ctrl+r" in text
