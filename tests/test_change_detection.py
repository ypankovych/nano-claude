"""Integration tests for change detection pipeline -- stubs for Task 2."""

import pytest


def test_notification_on_change():
    """Verify toast notification appears when files change externally."""
    pytest.skip("Stub -- will be implemented in Task 2")


def test_change_highlights():
    """Verify SearchableTextArea shows green/yellow highlights on changed lines."""
    pytest.skip("Stub -- will be implemented in Task 2")


def test_jump_to_change():
    """Verify action_jump_to_change opens the changed file and scrolls."""
    pytest.skip("Stub -- will be implemented in Task 2")


def test_auto_reload():
    """Verify buffer content updated after external file change (no unsaved edits)."""
    pytest.skip("Stub -- will be implemented in Task 2")


def test_conflict_prompt():
    """Verify ExternalChangeConflictScreen pushed when file has unsaved edits + disk change."""
    pytest.skip("Stub -- will be implemented in Task 2")


def test_changed_files_overlay():
    """Verify overlay shown when multiple files change."""
    pytest.skip("Stub -- will be implemented in Task 2")


def test_highlights_clear_on_edit():
    """Verify change highlights cleared when user types in editor."""
    pytest.skip("Stub -- will be implemented in Task 2")
