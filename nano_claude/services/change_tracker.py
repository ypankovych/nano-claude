"""ChangeTracker service for computing line-level diffs when files change on disk.

Maintains before-snapshots of tracked files and computes added/modified/deleted
line ranges using difflib.SequenceMatcher opcodes. Provides unified diff output
for display in a diff view.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FileChange:
    """Result of computing a diff between a file's snapshot and its current content.

    Attributes:
        path: The file that changed.
        added_lines: 0-indexed line numbers in the NEW file that were inserted.
        modified_lines: 0-indexed line numbers in the NEW file that were replaced.
        deleted_count: Number of lines deleted from the old file.
        old_content: Content before the change (snapshot).
        new_content: Content after the change (current on disk).
    """

    path: Path
    added_lines: list[int] = field(default_factory=list)
    modified_lines: list[int] = field(default_factory=list)
    deleted_count: int = 0
    old_content: str = ""
    new_content: str = ""


class ChangeTracker:
    """Tracks file snapshots and computes line-level diffs.

    Usage:
        1. Call ensure_snapshot(path) when a file is opened or before Claude edits.
        2. When FileSystemChanged fires, call compute_change(path) to get the diff.
        3. Use get_unified_diff(path) to display standard diff output.
        4. Call clear_change(path) when the user starts editing a changed file.
    """

    def __init__(self) -> None:
        self._snapshots: dict[Path, str] = {}
        self._pending_changes: dict[Path, FileChange] = {}

    def ensure_snapshot(self, path: Path) -> None:
        """Read file content and store as snapshot if not already tracked.

        Silently ignores files that cannot be read (permission errors,
        missing files, etc.).
        """
        if path in self._snapshots:
            return
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            self._snapshots[path] = content
        except OSError:
            pass

    def compute_change(self, path: Path) -> FileChange | None:
        """Compare current file on disk against stored snapshot.

        Uses difflib.SequenceMatcher.get_opcodes() to classify changes:
        - "insert" opcodes -> added_lines (j1..j2 range in new file)
        - "replace" opcodes -> modified_lines (j1..j2 range in new file)
        - "delete" opcodes -> deleted_count (i2-i1 lines removed)

        Returns None if no snapshot exists or file content is unchanged.
        After computing, updates the snapshot to the new content so the
        next change diffs against the latest version.
        """
        if path not in self._snapshots:
            return None

        try:
            new_content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

        old_content = self._snapshots[path]

        if old_content == new_content:
            return None

        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        opcodes = matcher.get_opcodes()

        added_lines: list[int] = []
        modified_lines: list[int] = []
        deleted_count: int = 0

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "insert":
                added_lines.extend(range(j1, j2))
            elif tag == "replace":
                modified_lines.extend(range(j1, j2))
                # Also count any net deletions in the replace
                old_count = i2 - i1
                new_count = j2 - j1
                if old_count > new_count:
                    deleted_count += old_count - new_count
            elif tag == "delete":
                deleted_count += i2 - i1

        change = FileChange(
            path=path,
            added_lines=added_lines,
            modified_lines=modified_lines,
            deleted_count=deleted_count,
            old_content=old_content,
            new_content=new_content,
        )

        self._pending_changes[path] = change
        # Update snapshot to new content for next diff
        self._snapshots[path] = new_content

        return change

    def get_unified_diff(self, path: Path) -> str:
        """Return a standard unified diff string for a pending change.

        Uses difflib.unified_diff with fromfile="a/{name}" tofile="b/{name}"
        and n=3 context lines.

        Returns empty string if no pending change exists.
        """
        change = self._pending_changes.get(path)
        if change is None:
            return ""

        old_lines = change.old_content.splitlines(keepends=True)
        new_lines = change.new_content.splitlines(keepends=True)

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{path.name}",
            tofile=f"b/{path.name}",
            n=3,
        )

        return "".join(diff)

    def get_pending_change(self, path: Path) -> FileChange | None:
        """Return the pending change for a path, or None."""
        return self._pending_changes.get(path)

    def get_all_pending_paths(self) -> list[Path]:
        """Return all paths with pending changes."""
        return list(self._pending_changes.keys())

    def clear_change(self, path: Path) -> None:
        """Remove pending change for a path."""
        self._pending_changes.pop(path, None)

    def clear_all(self) -> None:
        """Clear all snapshots and pending changes."""
        self._snapshots.clear()
        self._pending_changes.clear()
