"""Main Textual App class with three-panel layout composition."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Footer, Header

from nano_claude.config.settings import (
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
