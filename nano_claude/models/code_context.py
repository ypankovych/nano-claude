"""Code context model for sending editor selections to Claude's PTY."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BRACKETED_PASTE_START = "\x1b[200~"
BRACKETED_PASTE_END = "\x1b[201~"
MAX_SELECTION_LINES = 200
MAX_SELECTION_BYTES = 8192


@dataclass
class CodeContext:
    """Represents a code selection from the editor.

    Contains the file path, line range, selected text, and detected language.
    Used to format code fences for injection into Claude's PTY input.
    """

    file_path: Path
    start_line: int  # 1-indexed
    end_line: int  # 1-indexed
    text: str
    language: str | None

    def format_code_fence(self, cwd: Path) -> str:
        """Format the selection as a markdown code fence.

        Args:
            cwd: Current working directory for computing relative paths.

        Returns:
            Markdown code fence string with file path and line numbers.
        """
        try:
            rel_path = self.file_path.relative_to(cwd)
        except ValueError:
            rel_path = self.file_path.name
        lang = self.language or ""
        return f"```{lang}\n# {rel_path} lines {self.start_line}-{self.end_line}\n{self.text}\n```\n"


def truncate_selection(text: str) -> tuple[str, bool]:
    """Truncate a selection that exceeds line or byte limits.

    Args:
        text: The selected text to potentially truncate.

    Returns:
        Tuple of (possibly truncated text, whether truncation occurred).
    """
    lines = text.split("\n")
    truncated = False
    if len(lines) > MAX_SELECTION_LINES:
        lines = lines[:MAX_SELECTION_LINES]
        truncated = True
    result = "\n".join(lines)
    if len(result.encode("utf-8")) > MAX_SELECTION_BYTES:
        while len(result.encode("utf-8")) > MAX_SELECTION_BYTES and lines:
            lines.pop()
            result = "\n".join(lines)
        truncated = True
    if truncated:
        result += "\n... (truncated)"
    return result, truncated


def write_to_pty_bracketed(fd: int, text: str) -> None:
    """Write text to a PTY file descriptor wrapped in bracketed paste.

    Uses bracketed paste mode escape sequences so the terminal treats
    the injected text as pasted content (no auto-indent, etc.).
    Writes in chunks of 4096 bytes to avoid PTY buffer overflow.

    Args:
        fd: PTY file descriptor.
        text: Text to inject into the PTY.
    """
    payload = f"{BRACKETED_PASTE_START}{text}{BRACKETED_PASTE_END}"
    data = payload.encode("utf-8")
    chunk_size = 4096
    offset = 0
    while offset < len(data):
        written = os.write(fd, data[offset : offset + chunk_size])
        offset += written
