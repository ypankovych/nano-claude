"""ChangedFilesOverlay: selectable list of files changed by Claude."""

from __future__ import annotations

from pathlib import Path

from textual.message import Message
from textual.widget import Widget
from textual.widgets import OptionList


class ChangedFilesOverlay(Widget):
    """Overlay widget showing a selectable list of changed file paths.

    Docked to the top of the editor panel. Hidden by default; shown
    when multiple files change at once so the user can pick which to open.
    """

    DEFAULT_CSS = """
    ChangedFilesOverlay {
        dock: top;
        height: auto;
        max-height: 12;
        display: none;
        background: $surface;
        border-bottom: solid $accent;
        padding: 0 1;
    }
    ChangedFilesOverlay.visible {
        display: block;
    }
    ChangedFilesOverlay OptionList {
        height: auto;
        max-height: 10;
    }
    """

    class FileSelected(Message):
        """Posted when user selects a file from the changed files list."""

        def __init__(self, path: Path) -> None:
            super().__init__()
            self.path = path

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._paths: list[Path] = []

    def compose(self):
        yield OptionList(id="changed-files-list")

    def show_files(self, paths: list[Path]) -> None:
        """Populate and show the overlay with a list of changed file paths."""
        self._paths = paths
        option_list = self.query_one(OptionList)
        option_list.clear_options()
        for p in paths:
            try:
                rel = p.relative_to(Path.cwd())
            except ValueError:
                rel = p
            option_list.add_option(str(rel))
        self.add_class("visible")
        option_list.focus()

    def hide_overlay(self) -> None:
        """Hide the overlay."""
        self.remove_class("visible")

    def on_option_list_option_selected(self, event) -> None:
        """Handle selection from the OptionList."""
        idx = event.option_index
        if 0 <= idx < len(self._paths):
            self.post_message(self.FileSelected(self._paths[idx]))
        self.hide_overlay()

    def on_key(self, event) -> None:
        """Handle Escape to close the overlay."""
        if event.key == "escape":
            self.hide_overlay()
            event.prevent_default()
