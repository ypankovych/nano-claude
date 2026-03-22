"""Base panel container with consistent border and focus-within styling."""

from textual.containers import Vertical
from textual.reactive import reactive


class BasePanel(Vertical):
    """Base container for all nano-claude panels.

    Provides consistent border, title, and focus-within styling.
    Child widgets should be focusable; the container itself is not.
    """

    can_focus = False

    DEFAULT_CSS = """
    BasePanel {
        border: round $secondary;
        border-title-color: $text-muted;
        border-title-style: none;
    }
    BasePanel:focus-within {
        border: round $accent;
        border-title-color: $accent;
        border-title-style: bold;
    }
    """

    panel_title = reactive("")

    def watch_panel_title(self, title: str) -> None:
        """Update border title when panel_title changes."""
        self.border_title = title
