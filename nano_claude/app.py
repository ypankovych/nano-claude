"""Main Textual App class with three-panel layout composition."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Footer, Header

from nano_claude.config.settings import (
    COLLAPSE_CHAT_THRESHOLD,
    COLLAPSE_TREE_THRESHOLD,
    DEFAULT_CHAT_WIDTH,
    DEFAULT_EDITOR_WIDTH,
    DEFAULT_TREE_WIDTH,
)
from nano_claude.panels.chat import ChatPanel
from nano_claude.panels.editor import EditorPanel
from nano_claude.panels.file_tree import FileTreePanel


class NanoClaudeApp(App):
    """nano-claude: a terminal-native IDE wrapper for Claude Code."""

    CSS_PATH = "styles.tcss"
    TITLE = "nano-claude"

    # Panel width state (fr units)
    tree_width = reactive(DEFAULT_TREE_WIDTH)
    editor_width = reactive(DEFAULT_EDITOR_WIDTH)
    chat_width = reactive(DEFAULT_CHAT_WIDTH)
    tree_visible = reactive(True)

    # Optional path from CLI
    initial_path: str | None = None

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", id="app.quit", priority=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-panels"):
            yield FileTreePanel(id="file-tree")
            yield EditorPanel(id="editor")
            yield ChatPanel(id="chat")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize responsive collapse based on starting terminal size."""
        self._handle_responsive_collapse(self.size.width)

    def on_resize(self, event) -> None:
        """Handle terminal resize -- collapse panels at small sizes."""
        # Defer to after layout recalculation (Pitfall 4 from research)
        self.call_later(self._handle_responsive_collapse, event.size.width)

    def _handle_responsive_collapse(self, terminal_width: int) -> None:
        """Collapse or restore panels based on terminal width thresholds."""
        file_tree = self.query_one("#file-tree")
        chat = self.query_one("#chat")

        # File tree hides first
        if terminal_width < COLLAPSE_TREE_THRESHOLD:
            file_tree.add_class("hidden")
        else:
            file_tree.remove_class("hidden")

        # Chat hides at very narrow widths
        if terminal_width < COLLAPSE_CHAT_THRESHOLD:
            chat.add_class("hidden")
        else:
            chat.remove_class("hidden")

        self._apply_panel_widths()

    def _apply_panel_widths(self) -> None:
        """Apply current fr-based widths to all visible panels."""
        panels = {
            "file-tree": self.tree_width,
            "editor": self.editor_width,
            "chat": self.chat_width,
        }
        for panel_id, fr_val in panels.items():
            try:
                panel = self.query_one(f"#{panel_id}")
                if not panel.has_class("hidden"):
                    panel.styles.width = f"{fr_val}fr"
            except Exception:
                pass
