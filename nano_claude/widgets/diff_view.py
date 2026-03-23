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

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._diff_renderable: Text = Text("No changes to display", style="dim italic")

    @property
    def renderable(self) -> Text:
        """Return the current diff renderable for testing and rendering."""
        return self._diff_renderable

    def set_diff(self, diff_text: str) -> None:
        """Parse unified diff text and render with colors.

        Args:
            diff_text: Output from difflib.unified_diff joined as a string.
                If empty, shows a "no changes" message.
        """
        if not diff_text.strip():
            self._diff_renderable = Text(
                "No changes to display", style="dim italic"
            )
            self._try_update()
            return

        lines = diff_text.splitlines()
        truncated = False
        if len(lines) > MAX_DIFF_LINES:
            lines = lines[:MAX_DIFF_LINES]
            truncated = True

        result = Text()
        for line in lines:
            if line.startswith("+++") or line.startswith("---"):
                result.append(line + "\n", style="bold")
            elif line.startswith("@@"):
                result.append(line + "\n", style="cyan")
            elif line.startswith("+"):
                result.append(line + "\n", style="green")
            elif line.startswith("-"):
                result.append(line + "\n", style="red")
            else:
                result.append(line + "\n")

        if truncated:
            result.append(
                f"\n... (truncated, showing first {MAX_DIFF_LINES} lines)\n",
                style="dim italic",
            )

        self._diff_renderable = result
        self._try_update()

    def _try_update(self) -> None:
        """Update the widget display if mounted in an app context."""
        try:
            self.update(self._diff_renderable)
        except Exception:
            # Not mounted yet -- renderable is stored for when we are
            pass
