"""ChangeTracker service for computing line-level diffs when files change on disk.

All paths are resolved to absolute form for consistent comparison.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FileChange:
    """Result of computing a diff between before/after content."""

    path: Path
    added_lines: list[int] = field(default_factory=list)
    modified_lines: list[int] = field(default_factory=list)
    deleted_count: int = 0
    old_content: str = ""
    new_content: str = ""


class ChangeTracker:
    """Tracks file snapshots and computes line-level diffs.

    Snapshots come from two sources:
    1. ensure_snapshot() — called when user opens a file
    2. set_snapshot() — called with BufferManager content for open files
    """

    def __init__(self) -> None:
        self._snapshots: dict[Path, str] = {}
        self._pending_changes: dict[Path, FileChange] = {}
        self._user_saved: set[Path] = set()

    def ensure_snapshot(self, path: Path) -> None:
        """Read file from disk and store as snapshot if not already tracked."""
        path = path.resolve()
        if path in self._snapshots:
            return
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            self._snapshots[path] = content
        except OSError:
            pass

    def set_snapshot(self, path: Path, content: str) -> None:
        """Set snapshot content directly (e.g., from BufferManager)."""
        path = path.resolve()
        self._snapshots[path] = content

    def mark_user_saved(self, path: Path) -> None:
        """Mark a file as just saved by the user — ignore next filesystem event."""
        path = path.resolve()
        self._user_saved.add(path)
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            self._snapshots[path] = content
        except OSError:
            pass

    def compute_change(
        self, path: Path, before_content: str | None = None
    ) -> FileChange | None:
        """Compare current file on disk against snapshot or provided before_content.

        Args:
            path: File that changed.
            before_content: If provided, use this as the "before" instead of
                the stored snapshot. This is useful when the caller has the
                BufferManager's original_content for open files.

        Returns None if user-saved, no before content available, or unchanged.
        """
        path = path.resolve()

        # Skip user's own saves
        if path in self._user_saved:
            self._user_saved.discard(path)
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                self._snapshots[path] = content
            except OSError:
                pass
            return None

        # Determine "before" content
        old_content = before_content or self._snapshots.get(path)
        if old_content is None:
            # No snapshot at all — store current content for next time
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                self._snapshots[path] = content
            except OSError:
                pass
            return None

        # Read current file
        try:
            new_content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

        if old_content == new_content:
            return None

        # Compute line-level diff
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

        added_lines: list[int] = []
        modified_lines: list[int] = []
        deleted_count: int = 0

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "insert":
                added_lines.extend(range(j1, j2))
            elif tag == "replace":
                modified_lines.extend(range(j1, j2))
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
        return change

    def update_snapshot(self, path: Path) -> None:
        """Update snapshot to current disk content."""
        path = path.resolve()
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            self._snapshots[path] = content
        except OSError:
            pass

    def get_unified_diff(self, path: Path) -> str:
        """Return unified diff string for a pending change."""
        path = path.resolve()
        change = self._pending_changes.get(path)
        if change is None:
            return ""

        old_lines = change.old_content.splitlines(keepends=True)
        new_lines = change.new_content.splitlines(keepends=True)
        diff = difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"a/{path.name}", tofile=f"b/{path.name}", n=3,
        )
        return "".join(diff)

    def get_pending_change(self, path: Path) -> FileChange | None:
        """Return the pending change for a path, or None."""
        path = path.resolve()
        return self._pending_changes.get(path)

    def clear_change(self, path: Path) -> None:
        """Remove pending change for a path."""
        path = path.resolve()
        self._pending_changes.pop(path, None)

    def clear_all(self) -> None:
        """Clear all snapshots and pending changes."""
        self._snapshots.clear()
        self._pending_changes.clear()
