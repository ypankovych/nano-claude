"""Tests for file watcher service and tree auto-refresh integration."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nano_claude.services.file_watcher import FileSystemChanged, FileWatcherService


# ---------------------------------------------------------------------------
# FileWatcherService unit tests
# ---------------------------------------------------------------------------


class TestFileWatcherService:
    """Test FileWatcherService instantiation and attributes."""

    def test_init_stores_path(self, tmp_path: Path):
        """FileWatcherService stores the watch_path and app reference."""
        mock_app = MagicMock()
        watcher = FileWatcherService(app=mock_app, watch_path=tmp_path)
        assert watcher.watch_path == tmp_path
        assert watcher.app is mock_app

    def test_stop_event_initially_none(self, tmp_path: Path):
        """_stop_event is None before start() is called."""
        mock_app = MagicMock()
        watcher = FileWatcherService(app=mock_app, watch_path=tmp_path)
        assert watcher._stop_event is None


# ---------------------------------------------------------------------------
# FileSystemChanged message tests
# ---------------------------------------------------------------------------


class TestFileSystemChanged:
    """Test the FileSystemChanged message structure."""

    def test_message_stores_changes(self):
        """FileSystemChanged stores the set of changes."""
        from watchfiles import Change

        changes = {(Change.added, "/tmp/new.txt"), (Change.deleted, "/tmp/old.txt")}
        msg = FileSystemChanged(changes)
        assert msg.changes == changes

    def test_message_empty_changes(self):
        """FileSystemChanged works with an empty set."""
        msg = FileSystemChanged(set())
        assert msg.changes == set()


# ---------------------------------------------------------------------------
# FileTreePanel.reload_preserving_state tests
# ---------------------------------------------------------------------------


class TestTreeReloadPreservingState:
    """Test that FileTreePanel has reload_preserving_state method."""

    def test_method_exists(self):
        """FileTreePanel has async reload_preserving_state method."""
        from nano_claude.panels.file_tree import FileTreePanel

        assert hasattr(FileTreePanel, "reload_preserving_state")
        # Should be a coroutine function
        import asyncio

        assert asyncio.iscoroutinefunction(FileTreePanel.reload_preserving_state)


# ---------------------------------------------------------------------------
# App wiring tests
# ---------------------------------------------------------------------------


class TestAppWatcherWiring:
    """Test that App has file watcher integration."""

    def test_app_has_on_file_system_changed(self):
        """App has on_file_system_changed handler method."""
        from nano_claude.app import NanoClaudeApp

        assert hasattr(NanoClaudeApp, "on_file_system_changed")
        assert callable(getattr(NanoClaudeApp, "on_file_system_changed"))

    def test_file_tree_panel_does_not_own_handler(self):
        """FileTreePanel does NOT have on_file_system_changed handler.

        App.py is the sole owner of this coordination (per architecture).
        """
        from nano_claude.panels.file_tree import FileTreePanel

        assert not hasattr(FileTreePanel, "on_file_system_changed")

    def test_app_imports_file_watcher(self):
        """App module imports FileWatcherService."""
        import nano_claude.app as app_module

        assert hasattr(app_module, "FileWatcherService")

    def test_app_imports_file_system_changed(self):
        """App module imports FileSystemChanged."""
        import nano_claude.app as app_module

        assert hasattr(app_module, "FileSystemChanged")
