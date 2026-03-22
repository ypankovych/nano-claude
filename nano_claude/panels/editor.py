"""Editor panel with TextArea code editor, file buffer management, and search."""

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
from nano_claude.widgets.search_overlay import SearchOverlay
from nano_claude.widgets.searchable_text_area import SearchableTextArea


def find_all_matches(query: str, text: str) -> list[tuple[int, int]]:
    """Find all occurrences of query in text (case-insensitive).

    Args:
        query: The search string (case-insensitive).
        text: The full text content to search within.

    Returns:
        List of (row, col) tuples for each match start position.
    """
    if not query:
        return []

    matches: list[tuple[int, int]] = []
    query_lower = query.lower()
    query_len = len(query_lower)

    for row, line in enumerate(text.split("\n")):
        line_lower = line.lower()
        start = 0
        while True:
            idx = line_lower.find(query_lower, start)
            if idx == -1:
                break
            matches.append((row, idx))
            start = idx + query_len

    return matches


class EditorPanel(BasePanel):
    """Center panel: code editor with syntax highlighting, buffer management, and search.

    Uses SearchableTextArea for editing files with line numbers,
    syntax highlighting, undo/redo, and multi-match highlighting.
    Tracks open file buffers so switching files preserves unsaved edits.
    """

    current_file: reactive[Path | None] = reactive(None)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._buffer_manager = BufferManager()
        self._search_matches: list[tuple[int, int]] = []
        self._current_match_index: int = -1
        self._last_search_query: str = ""

    def compose(self):
        self.panel_title = "Editor"
        yield SearchOverlay(id="search-overlay")
        yield SearchableTextArea(
            "",
            language=None,
            theme="monokai",
            show_line_numbers=True,
            soft_wrap=False,
            tab_behavior="indent",
            id="code-editor",
        )

    def on_mount(self) -> None:
        """Store reference to SearchableTextArea and show README or welcome."""
        from nano_claude.config.settings import WELCOME_GREETING

        self._text_area = self.query_one("#code-editor", SearchableTextArea)

        # Auto-open README.md if it exists, otherwise show welcome greeting
        readme_path = Path.cwd() / "README.md"
        if readme_path.is_file():
            self.open_file(readme_path)
        else:
            self._text_area.load_text(WELCOME_GREETING)
            self.panel_title = "Welcome"

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

        # Clear search state when switching files
        self._clear_search_state()

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

    # ----- Search functionality -----

    def action_toggle_search(self) -> None:
        """Toggle the search overlay visibility."""
        overlay = self.query_one(SearchOverlay)
        if overlay.has_class("visible"):
            overlay.hide_overlay()
            self._clear_search_state()
        else:
            overlay.show_overlay()

    def on_search_overlay_search_requested(
        self, event: SearchOverlay.SearchRequested
    ) -> None:
        """Handle search request from the overlay."""
        overlay = self.query_one(SearchOverlay)

        if event.query != self._last_search_query:
            # New query -- find all matches
            self._search_matches = find_all_matches(event.query, self._text_area.text)
            self._last_search_query = event.query
            self._current_match_index = 0 if self._search_matches else -1
            self._text_area.set_search_matches(
                self._search_matches, len(event.query)
            )
        else:
            # Same query -- navigate
            if self._search_matches:
                if event.direction == 1:
                    self._current_match_index = (
                        self._current_match_index + 1
                    ) % len(self._search_matches)
                else:
                    self._current_match_index = (
                        self._current_match_index - 1
                    ) % len(self._search_matches)

        # Update count display
        if self._search_matches:
            overlay.update_count(
                self._current_match_index + 1, len(self._search_matches)
            )
            self._text_area.set_current_match(self._current_match_index)
        else:
            overlay.update_count(0, 0)

    def on_search_overlay_search_closed(
        self, event: SearchOverlay.SearchClosed
    ) -> None:
        """Handle search overlay close -- clear all highlights."""
        self._clear_search_state()
        self._text_area.focus()

    def _clear_search_state(self) -> None:
        """Clear all search matches and reset state."""
        self._text_area.clear_search_matches()
        self._search_matches = []
        self._current_match_index = -1
        self._last_search_query = ""

    # ----- Private helpers -----

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
            self.panel_title = f"[italic orange1]{name}[/] [bold red]●[/]"
        else:
            self.panel_title = name

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Update buffer and title when TextArea content changes."""
        if self.current_file is not None:
            self._buffer_manager.update_content(
                self.current_file, self._text_area.text
            )
            self._update_title()
