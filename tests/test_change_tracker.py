"""Unit tests for ChangeTracker service -- diff computation, snapshots, and unified diff."""

from pathlib import Path

import pytest


class TestEnsureSnapshot:
    """Test ChangeTracker.ensure_snapshot stores file content."""

    def test_stores_file_content(self, tmp_path: Path):
        """ensure_snapshot reads and stores file content in _snapshots dict."""
        from nano_claude.services.change_tracker import ChangeTracker

        tracker = ChangeTracker()
        f = tmp_path / "hello.py"
        f.write_text("line1\nline2\n")

        tracker.ensure_snapshot(f)

        assert f in tracker._snapshots
        assert tracker._snapshots[f] == "line1\nline2\n"

    def test_does_not_overwrite_existing_snapshot(self, tmp_path: Path):
        """ensure_snapshot does not overwrite if path already tracked."""
        from nano_claude.services.change_tracker import ChangeTracker

        tracker = ChangeTracker()
        f = tmp_path / "hello.py"
        f.write_text("original")

        tracker.ensure_snapshot(f)
        f.write_text("changed")
        tracker.ensure_snapshot(f)

        assert tracker._snapshots[f] == "original"

    def test_handles_missing_file(self, tmp_path: Path):
        """ensure_snapshot gracefully handles non-existent file."""
        from nano_claude.services.change_tracker import ChangeTracker

        tracker = ChangeTracker()
        f = tmp_path / "does_not_exist.py"

        tracker.ensure_snapshot(f)  # Should not raise

        assert f not in tracker._snapshots


class TestComputeChange:
    """Test ChangeTracker.compute_change diff computation."""

    def test_reports_all_added_without_snapshot(self, tmp_path: Path):
        """compute_change reports all lines as added when no snapshot exists."""
        from nano_claude.services.change_tracker import ChangeTracker

        tracker = ChangeTracker()
        f = tmp_path / "hello.py"
        f.write_text("line1\nline2\nline3\n")

        result = tracker.compute_change(f)
        assert result is not None
        assert result.added_lines == [0, 1, 2]
        assert result.modified_lines == []

    def test_returns_none_when_content_unchanged(self, tmp_path: Path):
        """compute_change returns None when file content has not changed."""
        from nano_claude.services.change_tracker import ChangeTracker

        tracker = ChangeTracker()
        f = tmp_path / "hello.py"
        f.write_text("unchanged\n")

        tracker.ensure_snapshot(f)
        result = tracker.compute_change(f)
        assert result is None

    def test_added_lines_for_insertions(self, tmp_path: Path):
        """compute_change returns correct added_lines for pure insertions."""
        from nano_claude.services.change_tracker import ChangeTracker

        tracker = ChangeTracker()
        f = tmp_path / "hello.py"
        f.write_text("line1\nline2\n")
        tracker.ensure_snapshot(f)

        f.write_text("line1\nnew_line\nline2\n")
        change = tracker.compute_change(f)

        assert change is not None
        assert 1 in change.added_lines  # new_line is at index 1 in new file

    def test_modified_lines_for_replacements(self, tmp_path: Path):
        """compute_change returns correct modified_lines for replacements."""
        from nano_claude.services.change_tracker import ChangeTracker

        tracker = ChangeTracker()
        f = tmp_path / "hello.py"
        f.write_text("line1\nline2\nline3\n")
        tracker.ensure_snapshot(f)

        f.write_text("line1\nMODIFIED\nline3\n")
        change = tracker.compute_change(f)

        assert change is not None
        assert 1 in change.modified_lines  # MODIFIED is at index 1

    def test_deleted_count_for_deletions(self, tmp_path: Path):
        """compute_change returns correct deleted_count for deletions."""
        from nano_claude.services.change_tracker import ChangeTracker

        tracker = ChangeTracker()
        f = tmp_path / "hello.py"
        f.write_text("line1\nline2\nline3\n")
        tracker.ensure_snapshot(f)

        f.write_text("line1\nline3\n")
        change = tracker.compute_change(f)

        assert change is not None
        assert change.deleted_count == 1

    def test_mixed_operations(self, tmp_path: Path):
        """compute_change handles mixed insert + replace + delete."""
        from nano_claude.services.change_tracker import ChangeTracker

        tracker = ChangeTracker()
        f = tmp_path / "hello.py"
        f.write_text("aaa\nbbb\nccc\nddd\neee\n")
        tracker.ensure_snapshot(f)

        # Replace bbb -> BBB, delete ccc, insert NEW after ddd
        f.write_text("aaa\nBBB\nddd\nNEW\neee\n")
        change = tracker.compute_change(f)

        assert change is not None
        # BBB is a replacement (modified) and NEW is an insertion (added)
        # ccc was deleted (deleted_count >= 1)
        assert change.deleted_count >= 1
        assert len(change.added_lines) + len(change.modified_lines) >= 1

    def test_snapshot_preserved_after_compute(self, tmp_path: Path):
        """After compute_change, snapshot keeps original (pre-edit) content."""
        from nano_claude.services.change_tracker import ChangeTracker

        tracker = ChangeTracker()
        f = tmp_path / "hello.py"
        f.write_text("v1\n")
        tracker.ensure_snapshot(f)

        f.write_text("v2\n")
        tracker.compute_change(f)

        # Snapshot should still be v1 — NOT auto-updated
        assert tracker._snapshots[f] == "v1\n"

        # Explicit update changes it
        tracker.update_snapshot(f)
        assert tracker._snapshots[f] == "v2\n"

        # Second compute with same content should return None
        result = tracker.compute_change(f)
        assert result is None

    def test_file_change_stores_old_and_new_content(self, tmp_path: Path):
        """FileChange stores old_content and new_content."""
        from nano_claude.services.change_tracker import ChangeTracker

        tracker = ChangeTracker()
        f = tmp_path / "hello.py"
        f.write_text("old\n")
        tracker.ensure_snapshot(f)

        f.write_text("new\n")
        change = tracker.compute_change(f)

        assert change is not None
        assert change.old_content == "old\n"
        assert change.new_content == "new\n"


class TestGetUnifiedDiff:
    """Test ChangeTracker.get_unified_diff output."""

    def test_returns_unified_diff_format(self, tmp_path: Path):
        """get_unified_diff returns standard unified diff string."""
        from nano_claude.services.change_tracker import ChangeTracker

        tracker = ChangeTracker()
        f = tmp_path / "hello.py"
        f.write_text("line1\nline2\n")
        tracker.ensure_snapshot(f)

        f.write_text("line1\nMODIFIED\n")
        tracker.compute_change(f)

        diff = tracker.get_unified_diff(f)
        assert diff != ""
        assert "---" in diff
        assert "+++" in diff
        assert "-line2" in diff
        assert "+MODIFIED" in diff

    def test_returns_empty_string_when_no_pending(self, tmp_path: Path):
        """get_unified_diff returns '' when no pending change exists."""
        from nano_claude.services.change_tracker import ChangeTracker

        tracker = ChangeTracker()
        f = tmp_path / "hello.py"

        diff = tracker.get_unified_diff(f)
        assert diff == ""


class TestClearMethods:
    """Test ChangeTracker.clear_change and clear_all."""

    def test_clear_change_removes_pending(self, tmp_path: Path):
        """clear_change removes pending change for a path."""
        from nano_claude.services.change_tracker import ChangeTracker

        tracker = ChangeTracker()
        f = tmp_path / "hello.py"
        f.write_text("v1\n")
        tracker.ensure_snapshot(f)
        f.write_text("v2\n")
        tracker.compute_change(f)

        tracker.clear_change(f)
        assert tracker.get_pending_change(f) is None

    def test_clear_all_resets_everything(self, tmp_path: Path):
        """clear_all clears both snapshots and pending changes."""
        from nano_claude.services.change_tracker import ChangeTracker

        tracker = ChangeTracker()
        f = tmp_path / "hello.py"
        f.write_text("v1\n")
        tracker.ensure_snapshot(f)
        f.write_text("v2\n")
        tracker.compute_change(f)

        tracker.clear_all()
        assert len(tracker._snapshots) == 0
        assert len(tracker._pending_changes) == 0


class TestPendingQueries:
    """Test get_pending_change and get_all_pending_paths."""

    def test_get_pending_change(self, tmp_path: Path):
        """get_pending_change returns FileChange after compute."""
        from nano_claude.services.change_tracker import ChangeTracker

        tracker = ChangeTracker()
        f = tmp_path / "hello.py"
        f.write_text("v1\n")
        tracker.ensure_snapshot(f)
        f.write_text("v2\n")
        tracker.compute_change(f)

        pending = tracker.get_pending_change(f)
        assert pending is not None
        assert pending.path == f

    def test_get_all_pending_paths(self, tmp_path: Path):
        """get_all_pending_paths returns all paths with pending changes."""
        from nano_claude.services.change_tracker import ChangeTracker

        tracker = ChangeTracker()
        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_text("v1\n")
        f2.write_text("v1\n")
        tracker.ensure_snapshot(f1)
        tracker.ensure_snapshot(f2)
        f1.write_text("v2\n")
        f2.write_text("v2\n")
        tracker.compute_change(f1)
        tracker.compute_change(f2)

        paths = tracker.get_all_pending_paths()
        assert set(paths) == {f1, f2}
