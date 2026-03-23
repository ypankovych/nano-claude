"""DiffView: read-only widget for displaying colored unified diffs."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

MAX_DIFF_LINES = 5000


class DiffView(Static):
    """Read-only unified diff display with colored lines.

    Renders unified diff output with standard coloring:
    - Green for added lines (+)
    - Red for deleted lines (-)
    - Cyan for hunk headers (@@)
    - Bold for file headers (+++/---)
    - Default for context lines
    """

    DEFAULT_CSS = """
    DiffView {
        overflow-y: auto;
        overflow-x: auto;
        width: 1fr;
        height: 1fr;
        padding: 0 1;
    }
    """

    def set_diff(self, diff_text: str) -> None:
        """Parse unified diff text and render with colors.

        Args:
            diff_text: Output from difflib.unified_diff joined as a string.
                If empty, shows a "no changes" message.
        """
        raise NotImplementedError("Not yet implemented")
