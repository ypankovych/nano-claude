"""Editor panel with TextArea code editor and file buffer management."""

from __future__ import annotations

from pathlib import Path

from textual.reactive import reactive
from textual.widgets import TextArea

from nano_claude.config.settings import MAX_FILE_SIZE_BYTES
from nano_claude.models.file_buffer import (
    BufferManager,
    detect_indentation,
    detect_language,
)
from nano_claude.panels.base import BasePanel


class EditorPanel(BasePanel):
    """Center panel: code editor with syntax highlighting and buffer management.

    Uses TextArea.code_editor() for editing files with line numbers,
    syntax highlighting, and undo/redo support. Tracks open file
    buffers so switching files preserves unsaved edits.
    """

    current_file: reactive[Path | None] = reactive(None)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._buffer_manager = BufferManager()

    def compose(self):
        self.panel_title = "Editor"
        yield TextArea.code_editor(
            "",
            language=None,
            theme="monokai",
            soft_wrap=False,
            id="code-editor",
        )

    def on_mount(self) -> None:
        """Store reference to TextArea for quick access."""
        self._text_area = self.query_one("#code-editor", TextArea)

    def open_file(self, path: Path) -> None:
        """Open a file in the editor with syntax highlighting.

        Checks for binary and oversized files. Saves current buffer state
        before switching. Loads content, sets language, and detects indentation.
        """
        # Check file size
        try:
            file_size = path.stat().st_size
        except OSError:
            self.notify(f"Cannot access {path.name}", severity="error")
            return

        if file_size > MAX_FILE_SIZE_BYTES:
            self.notify(
                f"File too large ({file_size:,} bytes). Max: {MAX_FILE_SIZE_BYTES:,}.",
                severity="warning",
            )
            return

        # Check for binary content
        try:
            with open(path, "rb") as f:
                sample = f.read(8192)
            if b"\x00" in sample:
                self.notify("Cannot display binary file", severity="warning")
                return
        except OSError:
            self.notify(f"Cannot read {path.name}", severity="error")
            return

        # Save current buffer state before switching
        if self.current_file is not None:
            self._save_buffer_state()

        # Load file into buffer
        buf = self._buffer_manager.open_file(path)
        language = detect_language(path)
        _indent_type, indent_width = detect_indentation(buf.current_content)

        # Update TextArea
        self._text_area.load_text(buf.current_content)
        self._text_area.language = language
        self._text_area.indent_width = indent_width
        self._text_area.cursor_location = buf.cursor_location

        # Update state
        self.current_file = path
        self._update_title()

    def save_current_file(self) -> None:
        """Save the current file to disk.

        Updates the buffer, writes to disk, and shows a notification.
        """
        if self.current_file is None:
            return

        # Sync TextArea content to buffer before saving
        buf = self._buffer_manager.open_file(self.current_file)
        buf.current_content = self._text_area.text

        self._buffer_manager.save_file(self.current_file)
        self._update_title()
        self.notify(f"Saved {self.current_file.name}", severity="information")

    def has_unsaved_changes(self) -> bool:
        """Return True if any open buffer has unsaved changes."""
        # Sync current TextArea content to buffer first
        if self.current_file is not None:
            self._save_buffer_state()
        return self._buffer_manager.has_unsaved_changes()

    def get_unsaved_files(self) -> list[Path]:
        """Return list of paths with unsaved changes."""
        if self.current_file is not None:
            self._save_buffer_state()
        return self._buffer_manager.get_unsaved_files()

    def _save_buffer_state(self) -> None:
        """Store current TextArea state into the current file's buffer."""
        if self.current_file is None:
            return
        try:
            buf = self._buffer_manager.open_file(self.current_file)
            buf.current_content = self._text_area.text
            buf.cursor_location = self._text_area.cursor_location
        except Exception:
            pass

    def _update_title(self) -> None:
        """Update panel title to reflect current file and modified state."""
        if self.current_file is None:
            self.panel_title = "Editor"
            return

        name = self.current_file.name
        buf = self._buffer_manager.open_file(self.current_file)
        if buf.is_modified:
            self.panel_title = f"{name} [bold $error].[/]"
        else:
            self.panel_title = name

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Update buffer and title when TextArea content changes."""
        if self.current_file is not None:
            self._buffer_manager.update_content(
                self.current_file, self._text_area.text
            )
            self._update_title()
