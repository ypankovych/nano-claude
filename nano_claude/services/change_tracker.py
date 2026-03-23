"""ChangeTracker service for computing line-level diffs when files change on disk.

Maintains before-snapshots of tracked files and computes added/modified/deleted
line ranges using difflib.SequenceMatcher opcodes. Provides unified diff output
for display in a diff view.

All paths are resolved to absolute form for consistent comparison —
DirectoryTree uses one form, watchfiles uses another.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FileChange:
    """Result of computing a diff between a file's snapshot and its current content."""

    path: Path
    added_lines: list[int] = field(default_factory=list)
    modified_lines: list[int] = field(default_factory=list)
    deleted_count: int = 0
    old_content: str = ""
    new_content: str = ""


class ChangeTracker:
    """Tracks file snapshots and computes line-level diffs."""

    def __init__(self) -> None:
        self._snapshots: dict[Path, str] = {}
        self._pending_changes: dict[Path, FileChange] = {}
        self._user_saved: set[Path] = set()

    def ensure_snapshot(self, path: Path) -> None:
        """Read file content and store as snapshot if not already tracked."""
        path = path.resolve()
        if path in self._snapshots:
            return
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            self._snapshots[path] = content
        except OSError:
            pass

    def mark_user_saved(self, path: Path) -> None:
        """Mark a file as just saved by the user — ignore next filesystem event."""
        path = path.resolve()
        self._user_saved.add(path)
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            self._snapshots[path] = content
        except OSError:
            pass

    def compute_change(self, path: Path) -> FileChange | None:
        """Compare current file on disk against stored snapshot.

        Returns None if file was user-saved or content unchanged.
        For files without a prior snapshot, reports all lines as added.
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

        if path not in self._snapshots:
            # No pre-edit snapshot — report all lines as added
            try:
                new_content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return None
            new_lines = new_content.splitlines()
            change = FileChange(
                path=path,
                added_lines=list(range(len(new_lines))),
                modified_lines=[],
                deleted_count=0,
                old_content="",
                new_content=new_content,
            )
            self._pending_changes[path] = change
            self._snapshots[path] = new_content
            return change

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
        """Return a standard unified diff string for a pending change."""
        path = path.resolve()
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
        path = path.resolve()
        return self._pending_changes.get(path)

    def get_all_pending_paths(self) -> list[Path]:
        """Return all paths with pending changes."""
        return list(self._pending_changes.keys())

    def clear_change(self, path: Path) -> None:
        """Remove pending change for a path."""
        path = path.resolve()
        self._pending_changes.pop(path, None)

    def clear_all(self) -> None:
        """Clear all snapshots and pending changes."""
        self._snapshots.clear()
        self._pending_changes.clear()
