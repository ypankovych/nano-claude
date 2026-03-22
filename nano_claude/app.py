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
        # Panel focus -- Ctrl+letter as primary (universally supported across terminals)
        # Per research Pitfall 1: Ctrl+number is unreliable in many terminals (iTerm2, tmux, screen)
        # Substitution: Ctrl+1/2/3 (from CONTEXT.md) -> Ctrl+b/e/r (primary)
        Binding("ctrl+b", "focus_panel('file-tree')", "Tree", id="focus.tree", priority=True, show=False),
        Binding("ctrl+e", "focus_panel('editor')", "Editor", id="focus.editor", priority=True, show=False),
        Binding("ctrl+r", "focus_panel('chat')", "Chat", id="focus.chat", priority=True, show=False),
        # Secondary bindings: Ctrl+1/2/3 for terminals that support them (per CONTEXT.md original spec)
        Binding("ctrl+1", "focus_panel('file-tree')", "Tree", id="focus.tree.alt", priority=True, show=False),
        Binding("ctrl+2", "focus_panel('editor')", "Editor", id="focus.editor.alt", priority=True, show=False),
        Binding("ctrl+3", "focus_panel('chat')", "Chat", id="focus.chat.alt", priority=True, show=False),
        # Focus cycling -- Tab as primary (universally supported)
        # Per research Pitfall 5: Ctrl+Tab is intercepted by most terminal emulators
        # Substitution: Ctrl+Tab (from CONTEXT.md) -> Tab (primary)
        Binding("tab", "focus_next", "Next Panel", id="focus.next", priority=True, show=False),
        Binding("shift+tab", "focus_previous", "Prev Panel", id="focus.prev", priority=True, show=False),
        # Secondary binding: Ctrl+Tab for terminals that pass it through
        Binding("ctrl+tab", "focus_next", "Next Panel", id="focus.next.alt", priority=True, show=False),
        # Panel resize
        Binding("ctrl+equal", "resize_panel(1)", "Grow", id="resize.grow", priority=True, show=True),
        Binding("ctrl+minus", "resize_panel(-1)", "Shrink", id="resize.shrink", priority=True, show=True),
        # Toggle file tree
        Binding("ctrl+backslash", "toggle_file_tree", "Toggle Tree", id="toggle.tree", priority=True, show=True),
        # Quit
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

    def action_focus_panel(self, panel_id: str) -> None:
        """Focus a specific panel by its DOM id. Does nothing if panel is hidden."""
        try:
            panel = self.query_one(f"#{panel_id}")
            if panel.has_class("hidden"):
                return
            # Find the first focusable child within the panel
            for widget in panel.query("*"):
                if widget.can_focus:
                    widget.focus()
                    return
            # Fallback: focus the panel itself if it can accept focus
            if panel.can_focus:
                panel.focus()
        except Exception:
            pass

    def action_resize_panel(self, delta: int) -> None:
        """Grow or shrink the active panel width by delta * 0.5 fr units."""
        focused = self.focused
        if focused is None:
            return
        # Walk up to find which panel contains the focused widget
        panel = focused
        while panel is not None and panel.id not in ("file-tree", "editor", "chat"):
            panel = panel.parent
        if panel is None:
            return
        # Map panel id to reactive attribute name
        attr_map = {
            "file-tree": "tree_width",
            "editor": "editor_width",
            "chat": "chat_width",
        }
        attr = attr_map.get(panel.id)
        if attr is None:
            return
        current = getattr(self, attr)
        new_val = max(0.5, current + delta * 0.5)  # 0.5fr step, minimum 0.5fr
        setattr(self, attr, new_val)
        self._apply_panel_widths()

    def action_toggle_file_tree(self) -> None:
        """Toggle file tree panel visibility."""
        tree = self.query_one("#file-tree")
        is_currently_visible = not tree.has_class("hidden")
        if is_currently_visible:
            # Move focus away BEFORE hiding (Pitfall 3: focus lost when panel hidden)
            if self._panel_has_focus(tree):
                self.action_focus_panel("editor")
            tree.add_class("hidden")
        else:
            tree.remove_class("hidden")
            self._apply_panel_widths()

    def _panel_has_focus(self, panel) -> bool:
        """Check if the panel or any of its children currently have focus."""
        focused = self.focused
        if focused is None:
            return False
        node = focused
        while node is not None:
            if node is panel:
                return True
            node = node.parent
        return False

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
