"""Search overlay widget for in-editor find functionality."""

from __future__ import annotations

from textual.containers import Horizontal
from textual.events import Key
from textual.message import Message
from textual.widgets import Input, Static


class SearchOverlay(Horizontal):
    """Dockable search bar that overlays the top of the editor panel.

    Hidden by default (display: none). Toggle visibility with show_overlay()
    and hide_overlay(). Posts SearchRequested messages when the user submits
    a query or navigates matches, and SearchClosed when dismissed.
    """

    class SearchRequested(Message):
        """Posted when the user wants to search or navigate matches.

        Attributes:
            query: The search string.
            direction: 1 for forward (next match), -1 for backward (previous).
        """

        def __init__(self, query: str, direction: int = 1) -> None:
            super().__init__()
            self.query = query
            self.direction = direction

    class SearchClosed(Message):
        """Posted when the user closes the search overlay (Escape)."""

    DEFAULT_CSS = """
    SearchOverlay {
        dock: top;
        height: auto;
        max-height: 3;
        display: none;
        background: $surface;
        border-bottom: solid $primary;
        padding: 0 1;
    }
    SearchOverlay.visible {
        display: block;
    }
    SearchOverlay Input {
        width: 1fr;
    }
    SearchOverlay #search-count {
        width: auto;
        min-width: 8;
        content-align: center middle;
        padding: 0 1;
    }
    """

    def compose(self):
        """Compose the search bar with an input field and match count."""
        yield Input(placeholder="Find...", id="search-input")
        yield Static("0/0", id="search-count")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """When Enter is pressed in the search input, search forward."""
        if event.value:
            self.post_message(self.SearchRequested(event.value, direction=1))

    def on_key(self, event: Key) -> None:
        """Handle keyboard shortcuts within the search overlay."""
        if event.key == "escape":
            self.hide_overlay()
            self.post_message(self.SearchClosed())
            event.prevent_default()
            event.stop()
        elif event.key == "ctrl+g":
            # Next match
            input_widget = self.query_one("#search-input", Input)
            if input_widget.value:
                self.post_message(
                    self.SearchRequested(input_widget.value, direction=1)
                )
            event.prevent_default()
            event.stop()
        elif event.key in ("ctrl+shift+g", "shift+enter"):
            # Previous match
            input_widget = self.query_one("#search-input", Input)
            if input_widget.value:
                self.post_message(
                    self.SearchRequested(input_widget.value, direction=-1)
                )
            event.prevent_default()
            event.stop()

    def show_overlay(self) -> None:
        """Show the search overlay and focus the input."""
        self.add_class("visible")
        try:
            self.query_one("#search-input", Input).focus()
        except Exception:
            pass

    def hide_overlay(self) -> None:
        """Hide the search overlay and clear the input."""
        self.remove_class("visible")
        try:
            self.query_one("#search-input", Input).value = ""
        except Exception:
            pass

    def update_count(self, current: int, total: int) -> None:
        """Update the match count display (e.g. '3/12')."""
        try:
            self.query_one("#search-count", Static).update(f"{current}/{total}")
        except Exception:
            pass
