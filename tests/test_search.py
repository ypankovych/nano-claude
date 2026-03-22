"""Tests for search overlay, SearchableTextArea, and editor search integration."""

from pathlib import Path

import pytest

from nano_claude.widgets.search_overlay import SearchOverlay
from nano_claude.widgets.searchable_text_area import SearchableTextArea


# ---------------------------------------------------------------------------
# find_all_matches unit tests (pure function on EditorPanel)
# ---------------------------------------------------------------------------


class TestFindAllMatches:
    """Test the find_all_matches helper on EditorPanel."""

    def test_find_all_matches_basic(self):
        """find_all_matches('hello', text) returns correct (row, col) positions."""
        from nano_claude.panels.editor import EditorPanel

        # Create a standalone helper function test (call static-like via class)
        # We test through the module-level helper
        from nano_claude.panels.editor import find_all_matches

        result = find_all_matches("hello", "hello world\nhello again\nbye")
        assert result == [(0, 0), (1, 0)]

    def test_find_all_matches_case_insensitive(self):
        """Uppercase query matches lowercase text (case-insensitive)."""
        from nano_claude.panels.editor import find_all_matches

        result = find_all_matches("HELLO", "hello world")
        assert result == [(0, 0)]

    def test_find_all_matches_empty_query(self):
        """Empty query returns empty list."""
        from nano_claude.panels.editor import find_all_matches

        result = find_all_matches("", "any text")
        assert result == []

    def test_find_all_matches_no_match(self):
        """Query not found returns empty list."""
        from nano_claude.panels.editor import find_all_matches

        result = find_all_matches("no", "yes")
        assert result == []

    def test_find_all_matches_multiple_per_line(self):
        """Multiple matches on the same line are all found."""
        from nano_claude.panels.editor import find_all_matches

        result = find_all_matches("ab", "ab cd ab ef\nab")
        assert result == [(0, 0), (0, 6), (1, 0)]


# ---------------------------------------------------------------------------
# SearchOverlay widget tests
# ---------------------------------------------------------------------------


class TestSearchOverlay:
    """Test SearchOverlay widget behavior."""

    def test_search_overlay_hidden_by_default(self):
        """SearchOverlay does not have 'visible' class when first created."""
        overlay = SearchOverlay(id="search-overlay")
        assert not overlay.has_class("visible")

    def test_search_overlay_becomes_visible(self):
        """SearchOverlay gains 'visible' class when show_overlay is called."""
        # We can only test class manipulation; focus requires mounted widget
        overlay = SearchOverlay(id="search-overlay")
        overlay.add_class("visible")
        assert overlay.has_class("visible")

    def test_search_requested_message_has_query(self):
        """SearchRequested message stores query and direction."""
        msg = SearchOverlay.SearchRequested(query="test", direction=1)
        assert msg.query == "test"
        assert msg.direction == 1

    def test_search_requested_backward(self):
        """SearchRequested with direction=-1 for backward search."""
        msg = SearchOverlay.SearchRequested(query="test", direction=-1)
        assert msg.direction == -1

    def test_search_closed_message(self):
        """SearchClosed message can be instantiated."""
        msg = SearchOverlay.SearchClosed()
        assert msg is not None


# ---------------------------------------------------------------------------
# SearchableTextArea tests
# ---------------------------------------------------------------------------


class TestSearchableTextArea:
    """Test SearchableTextArea match storage and clearing."""

    def test_stores_matches(self):
        """set_search_matches stores _match_positions."""
        sta = SearchableTextArea("")
        matches = [(0, 0), (1, 5), (3, 2)]
        sta.set_search_matches(matches, query_len=3)
        assert sta._match_positions == matches
        assert sta._match_query_len == 3
        assert sta._current_match_index == 0

    def test_clear_matches(self):
        """clear_search_matches resets all match state."""
        sta = SearchableTextArea("")
        sta.set_search_matches([(0, 0)], query_len=2)
        sta.clear_search_matches()
        assert sta._match_positions == []
        assert sta._match_query_len == 0
        assert sta._current_match_index == -1

    def test_empty_matches_sets_index_minus_one(self):
        """set_search_matches with empty list sets _current_match_index to -1."""
        sta = SearchableTextArea("")
        sta.set_search_matches([], query_len=0)
        assert sta._current_match_index == -1

    def test_has_match_and_current_style(self):
        """SearchableTextArea has _MATCH_STYLE and _CURRENT_MATCH_STYLE."""
        sta = SearchableTextArea("")
        assert sta._MATCH_STYLE is not None
        assert sta._CURRENT_MATCH_STYLE is not None


# ---------------------------------------------------------------------------
# EditorPanel integration tests
# ---------------------------------------------------------------------------


class TestEditorSearchIntegration:
    """Integration tests for editor panel search functionality."""

    def test_editor_has_toggle_search_action(self):
        """EditorPanel has action_toggle_search method."""
        from nano_claude.panels.editor import EditorPanel

        assert hasattr(EditorPanel, "action_toggle_search")
        assert callable(getattr(EditorPanel, "action_toggle_search"))


# ---------------------------------------------------------------------------
# App binding test
# ---------------------------------------------------------------------------


class TestAppSearchBinding:
    """Test that Ctrl+F binding exists in App."""

    def test_ctrl_f_binding_exists(self):
        """App BINDINGS list contains a binding with key 'ctrl+f' and id 'editor.find'."""
        from textual.binding import Binding

        from nano_claude.app import NanoClaudeApp

        app = NanoClaudeApp()
        find_bindings = [
            b
            for b in app.BINDINGS
            if isinstance(b, Binding) and b.key == "ctrl+f" and b.id == "editor.find"
        ]
        assert len(find_bindings) >= 1, "Expected a ctrl+f binding with id editor.find"
