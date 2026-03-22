"""File buffer model for tracking open file state in the editor."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

from nano_claude.config.settings import EXTENSION_TO_LANGUAGE


@dataclass
class FileBuffer:
    """Represents an open file's state in the editor.

    Tracks original content (at last save/open) and current content
    (as edited by the user) to detect unsaved modifications.
    """

    path: Path
    original_content: str
    current_content: str
    cursor_location: tuple[int, int] = (0, 0)
    scroll_offset: tuple[int, int] = (0, 0)

    @property
    def is_modified(self) -> bool:
        """Return True if current content differs from the last saved/opened content."""
        return self.current_content != self.original_content


class BufferManager:
    """Manages open file buffers for the editor.

    Caches buffers by path so switching between files preserves edits.
    """

    def __init__(self) -> None:
        self._buffers: dict[Path, FileBuffer] = {}

    def open_file(self, path: Path) -> FileBuffer:
        """Open a file and return its buffer, using cache if already open."""
        if path in self._buffers:
            return self._buffers[path]
        content = path.read_text(encoding="utf-8", errors="replace")
        buf = FileBuffer(
            path=path,
            original_content=content,
            current_content=content,
        )
        self._buffers[path] = buf
        return buf

    def save_file(self, path: Path) -> None:
        """Write current buffer content to disk and mark as unmodified."""
        buf = self._buffers[path]
        path.write_text(buf.current_content, encoding="utf-8")
        buf.original_content = buf.current_content

    def has_unsaved_changes(self) -> bool:
        """Return True if any open buffer has been modified."""
        return any(buf.is_modified for buf in self._buffers.values())

    def get_unsaved_files(self) -> list[Path]:
        """Return paths of all buffers with unsaved changes."""
        return [buf.path for buf in self._buffers.values() if buf.is_modified]

    def update_content(self, path: Path, content: str) -> None:
        """Update the current content for a buffer."""
        if path in self._buffers:
            self._buffers[path].current_content = content


def detect_indentation(content: str, sample_lines: int = 100) -> tuple[str, int]:
    """Detect indentation style and width from file content.

    Scans the first sample_lines lines and determines whether the file
    uses tabs or spaces, and the most common indent width.

    Returns:
        A tuple of (indent_type, indent_width) where indent_type is
        "tabs" or "spaces" and indent_width is an integer (2-8).
        Default: ("spaces", 4).
    """
    if not content.strip():
        return ("spaces", 4)

    lines = content.split("\n")[:sample_lines]
    tab_count = 0
    space_count = 0
    space_widths: list[int] = []

    for line in lines:
        if not line or not line[0] in (" ", "\t"):
            continue
        if line[0] == "\t":
            tab_count += 1
        else:
            # Count leading spaces
            stripped = line.lstrip(" ")
            indent = len(line) - len(stripped)
            if indent > 0:
                space_count += 1
                space_widths.append(indent)

    if tab_count == 0 and space_count == 0:
        return ("spaces", 4)

    if tab_count > space_count:
        return ("tabs", 4)

    # Find most common indent width via GCD of space widths
    if space_widths:
        gcd = space_widths[0]
        for w in space_widths[1:]:
            gcd = math.gcd(gcd, w)
        # Clamp to 2-8 range
        gcd = max(2, min(8, gcd))
        return ("spaces", gcd)

    return ("spaces", 4)


def detect_language(path: Path) -> str | None:
    """Detect the programming language from a file's extension.

    Uses the EXTENSION_TO_LANGUAGE mapping from settings.

    Returns:
        Language name string for TextArea syntax highlighting, or None
        if the extension is not recognized.
    """
    return EXTENSION_TO_LANGUAGE.get(path.suffix.lower())
