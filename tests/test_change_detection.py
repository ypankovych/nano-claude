"""Integration tests for change detection pipeline."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nano_claude.services.change_tracker import ChangeTracker, FileChange
from nano_claude.widgets.searchable_text_area import SearchableTextArea


# ---------------------------------------------------------------------------
# SearchableTextArea change highlight tests
# ---------------------------------------------------------------------------


class TestChangeHighlights:
    """Verify SearchableTextArea shows green/yellow highlights on changed lines."""

    def test_set_change_highlights_stores_lines(self):
        """set_change_highlights stores added and modified line sets."""
        sta = SearchableTextArea("")
        sta.set_change_highlights(added=[1, 3, 5], modified=[2, 4])
        assert sta._added_lines == {1, 3, 5}
        assert sta._modified_lines == {2, 4}
        assert sta._change_highlights_active is True

    def test_clear_change_highlights_resets(self):
        """clear_change_highlights clears all change state."""
        sta = SearchableTextArea("")
        sta.set_change_highlights(added=[1], modified=[2])
        sta.clear_change_highlights()
        assert sta._added_lines == set()
        assert sta._modified_lines == set()
        assert sta._change_highlights_active is False

    def test_has_added_and_modified_styles(self):
        """SearchableTextArea has _ADDED_LINE_STYLE and _MODIFIED_LINE_STYLE."""
        sta = SearchableTextArea("")
        assert sta._ADDED_LINE_STYLE is not None
        assert sta._MODIFIED_LINE_STYLE is not None
        assert sta._ADDED_LINE_STYLE.bgcolor is not None
        assert sta._MODIFIED_LINE_STYLE.bgcolor is not None


# ---------------------------------------------------------------------------
# EditorPanel change-related methods
# ---------------------------------------------------------------------------


class TestEditorPanelChangeMethods:
    """Verify EditorPanel has change detection methods."""

    def test_editor_has_set_change_highlights(self):
        """EditorPanel has set_change_highlights method."""
        from nano_claude.panels.editor import EditorPanel

        assert hasattr(EditorPanel, "set_change_highlights")
        assert callable(getattr(EditorPanel, "set_change_highlights"))

    def test_editor_has_clear_change_highlights_for_file(self):
        """EditorPanel has clear_change_highlights_for_file method."""
        from nano_claude.panels.editor import EditorPanel

        assert hasattr(EditorPanel, "clear_change_highlights_for_file")

    def test_editor_has_reload_from_disk(self):
        """EditorPanel has reload_from_disk method."""
        from nano_claude.panels.editor import EditorPanel

        assert hasattr(EditorPanel, "reload_from_disk")

    def test_editor_has_scroll_to_line(self):
        """EditorPanel has scroll_to_line method."""
        from nano_claude.panels.editor import EditorPanel

        assert hasattr(EditorPanel, "scroll_to_line")

    def test_editor_has_show_changed_files(self):
        """EditorPanel has show_changed_files method."""
        from nano_claude.panels.editor import EditorPanel

        assert hasattr(EditorPanel, "show_changed_files")


# ---------------------------------------------------------------------------
# App-level wiring
# ---------------------------------------------------------------------------


class TestAppChangeDetection:
    """Test NanoClaudeApp has change detection wiring."""

    def test_app_has_jump_to_change_action(self):
        """NanoClaudeApp has action_jump_to_change method."""
        from nano_claude.app import NanoClaudeApp

        assert hasattr(NanoClaudeApp, "action_jump_to_change")
        assert callable(getattr(NanoClaudeApp, "action_jump_to_change"))

    def test_ctrl_j_binding_exists(self):
        """App BINDINGS list contains ctrl+j binding."""
        from textual.binding import Binding

        from nano_claude.app import NanoClaudeApp

        app = NanoClaudeApp()
        j_bindings = [
            b
            for b in app.BINDINGS
            if isinstance(b, Binding) and b.key == "ctrl+j"
        ]
        assert len(j_bindings) >= 1, "Expected a ctrl+j binding"

    def test_app_has_change_tracker(self):
        """NanoClaudeApp references ChangeTracker in on_mount."""
        import inspect
        from nano_claude.app import NanoClaudeApp

        source = inspect.getsource(NanoClaudeApp.on_mount)
        assert "change_tracker" in source.lower() or "ChangeTracker" in source

    def test_app_has_conflict_screen(self):
        """ExternalChangeConflictScreen is defined in app module."""
        from nano_claude.app import ExternalChangeConflictScreen

        assert ExternalChangeConflictScreen is not None

    def test_app_computes_changes_in_handler(self):
        """on_file_system_changed calls compute_change."""
        import inspect
        from nano_claude.app import NanoClaudeApp

        source = inspect.getsource(NanoClaudeApp.on_file_system_changed)
        assert "compute_change" in source


# ---------------------------------------------------------------------------
# Auto-reload tests
# ---------------------------------------------------------------------------


class TestAutoReload:
    """Verify auto-reload logic in change tracker and editor."""

    def test_auto_reload_updates_buffer(self, tmp_path: Path):
        """After compute_change, snapshot reflects new content for auto-reload."""
        tracker = ChangeTracker()
        f = tmp_path / "test.py"
        f.write_text("original\n")
        tracker.ensure_snapshot(f)

        f.write_text("updated\n")
        change = tracker.compute_change(f)

        assert change is not None
        # Snapshot now reflects new content
        assert tracker._snapshots[f] == "updated\n"


# ---------------------------------------------------------------------------
# Conflict prompt tests
# ---------------------------------------------------------------------------


class TestConflictPrompt:
    """Verify ExternalChangeConflictScreen structure."""

    def test_conflict_screen_has_reload_action(self):
        """ExternalChangeConflictScreen has action_reload method."""
        from nano_claude.app import ExternalChangeConflictScreen

        assert hasattr(ExternalChangeConflictScreen, "action_reload")

    def test_conflict_screen_has_keep_action(self):
        """ExternalChangeConflictScreen has action_keep method."""
        from nano_claude.app import ExternalChangeConflictScreen

        assert hasattr(ExternalChangeConflictScreen, "action_keep")

    def test_conflict_screen_bindings(self):
        """ExternalChangeConflictScreen has R and K bindings."""
        from textual.binding import Binding

        from nano_claude.app import ExternalChangeConflictScreen

        binding_keys = {b.key for b in ExternalChangeConflictScreen.BINDINGS if isinstance(b, Binding)}
        assert "r" in binding_keys
        assert "k" in binding_keys


# ---------------------------------------------------------------------------
# ChangedFilesOverlay tests
# ---------------------------------------------------------------------------


class TestChangedFilesOverlay:
    """Verify ChangedFilesOverlay structure."""

    def test_overlay_exists(self):
        """ChangedFilesOverlay can be imported."""
        from nano_claude.widgets.changed_files_overlay import ChangedFilesOverlay

        assert ChangedFilesOverlay is not None

    def test_overlay_file_selected_message(self):
        """ChangedFilesOverlay.FileSelected stores path."""
        from nano_claude.widgets.changed_files_overlay import ChangedFilesOverlay

        msg = ChangedFilesOverlay.FileSelected(Path("/tmp/test.py"))
        assert msg.path == Path("/tmp/test.py")


# ---------------------------------------------------------------------------
# Highlights clear on edit
# ---------------------------------------------------------------------------


class TestHighlightsClearOnEdit:
    """Verify change highlights clear when user starts editing."""

    def test_on_text_area_changed_clears_highlights(self):
        """EditorPanel.on_text_area_changed clears change highlights for current file."""
        import inspect
        from nano_claude.panels.editor import EditorPanel

        source = inspect.getsource(EditorPanel.on_text_area_changed)
        assert "clear_change_highlights" in source


# ---------------------------------------------------------------------------
# Reserved keys
# ---------------------------------------------------------------------------


class TestReservedKeys:
    """Verify terminal reserved keys include change detection keys."""

    def test_ctrl_j_in_reserved_keys(self):
        """ctrl+j is in RESERVED_KEYS."""
        from nano_claude.terminal.widget import RESERVED_KEYS

        assert "ctrl+j" in RESERVED_KEYS

    def test_ctrl_d_in_reserved_keys(self):
        """ctrl+d is in RESERVED_KEYS."""
        from nano_claude.terminal.widget import RESERVED_KEYS

        assert "ctrl+d" in RESERVED_KEYS
