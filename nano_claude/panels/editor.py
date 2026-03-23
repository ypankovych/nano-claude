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
from nano_claude.widgets.changed_files_overlay import ChangedFilesOverlay
from nano_claude.widgets.diff_view import DiffView
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
        # Count of pending reloads — suppresses change-clear in on_text_area_changed.
        # Incremented by reload_from_disk, decremented by handlers.
        self._reload_count: int = 0
        # Change highlight state per file
        self._file_change_highlights: dict[Path, tuple[list[int], list[int]]] = {}
        # Diff view toggle state
        self._diff_mode: bool = False

    def compose(self):
        self.panel_title = "Editor"
        yield ChangedFilesOverlay(id="changed-files-overlay")
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
        yield DiffView(id="diff-view")

    def on_mount(self) -> None:
        """Store reference to SearchableTextArea and DiffView, show README or welcome."""
        from nano_claude.config.settings import WELCOME_GREETING

        self._text_area = self.query_one("#code-editor", SearchableTextArea)
        self._diff_view = self.query_one("#diff-view", DiffView)
        self._diff_view.display = False

        # Auto-open README.md if it exists, otherwise show welcome greeting
        readme_path = Path.cwd() / "README.md"
        if readme_path.is_file():
            self.open_file(readme_path)
        else:
            self._text_area.load_text(WELCOME_GREETING)
            self.panel_title = "Welcome"

    def open_file(self, path: Path) -> None:
        """Open a file in the editor with syntax highlighting.

        Resolves the path to absolute form for consistent comparison with
        filesystem watcher paths. Checks for binary and oversized files.
        Saves current buffer state before switching.
        """
        path = path.resolve()
        # Exit diff mode if active
        if self._diff_mode:
            self._diff_view.display = False
            self._text_area.display = True
            self._diff_mode = False

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

        # Restore change highlights if they exist for this file
        if path in self._file_change_highlights:
            added, modified = self._file_change_highlights[path]
            self._text_area.set_change_highlights(added, modified)
        else:
            self._text_area.clear_change_highlights()

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

    # ----- Change detection support -----

    def set_change_highlights(
        self, path: Path, added: list[int], modified: list[int]
    ) -> None:
        """Apply change highlights for a file.

        Stores highlights so they can be restored when switching files.
        If the file is currently displayed, applies highlights immediately.
        """
        path = path.resolve()
        self._file_change_highlights[path] = (added, modified)
        if path == self.current_file:
            self._text_area.set_change_highlights(added, modified)

    def clear_change_highlights_for_file(self, path: Path) -> None:
        """Remove change highlights for a file."""
        path = path.resolve()
        self._file_change_highlights.pop(path, None)
        if path == self.current_file:
            self._text_area.clear_change_highlights()

    def scroll_to_line(self, line: int) -> None:
        """Move cursor to a specific line and scroll it into view."""
        try:
            doc = self._text_area.document
            total_lines = doc.line_count
            target_line = min(line, total_lines - 1)
            target_line = max(0, target_line)
            self._text_area.cursor_location = (target_line, 0)
            self._text_area.scroll_cursor_visible()
        except Exception:
            pass

    def action_toggle_diff(self) -> None:
        """Toggle between normal editor and diff view."""
        if self._diff_mode:
            # Return to normal editing
            self._diff_view.display = False
            self._text_area.display = True
            self._diff_mode = False
            self._update_title()
        else:
            # Show diff view
            if self.current_file is None:
                self.notify("No file open", severity="warning")
                return
            # Get the app's change tracker
            app = self.app
            if not hasattr(app, "_change_tracker"):
                self.notify("No changes tracked", severity="information")
                return
            diff_text = app._change_tracker.get_unified_diff(self.current_file)
            if not diff_text:
                self.notify("No changes for this file", severity="information")
                return
            self._diff_view.set_diff(diff_text)
            self._text_area.display = False
            self._diff_view.display = True
            self._diff_mode = True
            self.panel_title = f"Diff: {self.current_file.name}"

    def reload_from_disk(self, path: Path) -> None:
        """Reload a file from disk, preserving cursor position.

        Used for auto-reload when an open file changes externally
        and the buffer has no unsaved edits. Sets _reloading flag to
        prevent on_text_area_changed from clearing change highlights.
        """
        path = path.resolve()
        if path not in self._buffer_manager._buffers:
            return

        try:
            new_content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return

        buf = self._buffer_manager._buffers[path]
        # Save cursor position
        old_cursor = buf.cursor_location
        old_scroll = buf.scroll_offset

        # Update buffer content (both original and current since it was unmodified)
        buf.original_content = new_content
        buf.current_content = new_content

        # If this is the currently displayed file, reload the TextArea
        # Flag _reloading so on_text_area_changed doesn't clear highlights
        if path == self.current_file:
            self._reload_count += 1
            self._text_area.load_text(new_content)
            # Restore cursor, clamping to new file length
            total_lines = self._text_area.document.line_count
            row = min(old_cursor[0], total_lines - 1)
            row = max(0, row)
            line_text = self._text_area.document.get_line(row)
            col = min(old_cursor[1], len(line_text))
            self._text_area.cursor_location = (row, col)
            self._update_title()
            # NOTE: _reloading stays True until on_text_area_changed consumes it.
            # TextArea.Changed is a queued message processed in the next event
            # loop iteration, so setting _reloading=False here would be too early.

    def show_changed_files(self, paths: list[Path]) -> None:
        """Show the changed files overlay with a list of file paths."""
        try:
            overlay = self.query_one(ChangedFilesOverlay)
            overlay.show_files(paths)
        except Exception:
            pass

    def on_changed_files_overlay_file_selected(
        self, event: ChangedFilesOverlay.FileSelected
    ) -> None:
        """Handle file selection from the changed files overlay."""
        self.open_file(event.path)

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
        """Store current TextArea state into the buffer for the current file."""
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
        """Update buffer and title when TextArea content changes.

        Clears change highlights only on USER edits (not programmatic reloads).
        The _reloading flag is set by reload_from_disk and consumed here.
        """
        if self._reload_count > 0:
            self._reload_count -= 1
            event.stop()  # Don't bubble to app — prevents clearing change state
            return
        if self.current_file is not None:
            self._buffer_manager.update_content(
                self.current_file, self._text_area.text
            )
            self._update_title()
            # Clear change highlights when user edits the file
            if self.current_file in self._file_change_highlights:
                self.clear_change_highlights_for_file(self.current_file)
