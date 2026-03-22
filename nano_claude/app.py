"""Main Textual App class with three-panel layout composition."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Footer, Header, Label

from nano_claude.config.settings import (
    CLAUDE_STATUS_SEPARATOR,
    COLLAPSE_CHAT_THRESHOLD,
    COLLAPSE_TREE_THRESHOLD,
    DEFAULT_CHAT_WIDTH,
    DEFAULT_EDITOR_WIDTH,
    DEFAULT_TREE_WIDTH,
)
from nano_claude.panels.chat import ChatPanel
from nano_claude.panels.editor import EditorPanel
from nano_claude.panels.file_tree import FileTreePanel, FilteredDirectoryTree
from nano_claude.services.file_watcher import FileSystemChanged, FileWatcherService
from nano_claude.terminal.status_parser import ClaudeState, CostUpdate, StatusUpdate


class UnsavedChangesScreen(ModalScreen[str]):
    """Modal screen prompting user about unsaved changes before quitting.

    Returns: "save" to save and quit, "discard" to quit without saving,
    "cancel" to abort the quit.
    """

    DEFAULT_CSS = """
    UnsavedChangesScreen {
        align: center middle;
    }
    #unsaved-dialog {
        width: 60;
        height: auto;
        max-height: 20;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #unsaved-dialog Label {
        width: 100%;
        margin-bottom: 1;
    }
    #unsaved-buttons {
        height: auto;
        width: 100%;
        align-horizontal: center;
    }
    #unsaved-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("y", "save_quit", "Save & Quit", id="unsaved.save", priority=True),
        Binding("n", "discard_quit", "Discard & Quit", id="unsaved.discard", priority=True),
        Binding("escape", "cancel_quit", "Cancel", id="unsaved.escape", priority=True),
    ]

    def __init__(self, unsaved_files: list[Path], **kwargs) -> None:
        super().__init__(**kwargs)
        self._unsaved_files = unsaved_files

    def compose(self) -> ComposeResult:
        file_list = "\n".join(f"  - {p.name}" for p in self._unsaved_files)
        with Vertical(id="unsaved-dialog"):
            yield Label(f"Unsaved changes in:\n{file_list}")
            with Horizontal(id="unsaved-buttons"):
                yield Button("Save & Quit [Y]", variant="success", id="btn-save")
                yield Button("Discard [N]", variant="error", id="btn-discard")
                yield Button("Cancel [Esc]", variant="default", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self.dismiss("save")
        elif event.button.id == "btn-discard":
            self.dismiss("discard")
        elif event.button.id == "btn-cancel":
            self.dismiss("cancel")

    def action_save_quit(self) -> None:
        self.dismiss("save")

    def action_discard_quit(self) -> None:
        self.dismiss("discard")

    def action_cancel_quit(self) -> None:
        self.dismiss("cancel")


class NanoClaudeApp(App):
    """nano-claude: a terminal-native IDE wrapper for Claude Code."""

    CSS_PATH = "styles.tcss"
    TITLE = "nano-claude"

    # Panel width state (fr units)
    tree_width = reactive(DEFAULT_TREE_WIDTH)
    editor_width = reactive(DEFAULT_EDITOR_WIDTH)
    chat_width = reactive(DEFAULT_CHAT_WIDTH)
    tree_visible = reactive(True)

    # Claude status display
    claude_status = reactive("idle")
    claude_cost = reactive("")

    # Optional path from CLI
    initial_path: str | None = None
    _current_file_path: str = ""

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
        # Toggle hidden files in tree
        Binding("ctrl+h", "toggle_hidden_files", "Hidden Files", id="tree.toggle_hidden", priority=True, show=True),
        # Save
        Binding("ctrl+s", "save_file", "Save", id="file.save", priority=True, show=True),
        # Search in editor
        Binding("ctrl+f", "toggle_search", "Find", id="editor.find", priority=True, show=True),
        # Quit
        Binding("ctrl+q", "quit", "Quit", id="app.quit", priority=True),
        # Restart Claude Code subprocess
        Binding("ctrl+shift+r", "restart_claude", "Restart Claude", id="claude.restart", priority=True, show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-panels"):
            yield FileTreePanel(id="file-tree")
            yield EditorPanel(id="editor")
            yield ChatPanel(id="chat")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize responsive collapse and start file watcher."""
        self._handle_responsive_collapse(self.size.width)
        # Start filesystem watcher for auto-refresh of file tree
        self._file_watcher = FileWatcherService(self, Path.cwd())
        self.run_worker(
            self._file_watcher.start(), exclusive=True, name="file-watcher"
        )

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

    def action_toggle_hidden_files(self) -> None:
        """Toggle hidden file visibility in the file tree."""
        try:
            panel = self.query_one("#file-tree", FileTreePanel)
            panel.action_toggle_hidden()
        except Exception:
            pass

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

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        """Open selected file in the editor panel."""
        editor = self.query_one(EditorPanel)
        editor.open_file(event.path)
        # Track file path separately for status bar combination
        try:
            rel = event.path.relative_to(Path.cwd())
            self._current_file_path = str(rel)
        except ValueError:
            self._current_file_path = event.path.name
        self._update_status_bar()

    def on_status_update(self, message: StatusUpdate) -> None:
        """Update Claude status display from PTY output parsing."""
        state_labels = {
            ClaudeState.IDLE: "idle",
            ClaudeState.THINKING: "thinking...",
            ClaudeState.TOOL_USE: f"using {message.detail}",
            ClaudeState.PERMISSION: "waiting for permission",
            ClaudeState.DISCONNECTED: "disconnected",
        }
        self.claude_status = state_labels.get(message.state, "idle")
        self._update_status_bar()

    def on_cost_update(self, message: CostUpdate) -> None:
        """Update Claude cost display from PTY output parsing."""
        if message.total_tokens > 0:
            if message.total_tokens >= 1000:
                tokens_str = f"{message.total_tokens / 1000:.1f}k"
            else:
                tokens_str = str(message.total_tokens)
            self.claude_cost = f"{tokens_str} tokens / ${message.total_cost_usd:.2f}"
        self._update_status_bar()

    def _update_status_bar(self) -> None:
        """Combine file path and Claude status/cost into the header sub_title."""
        parts = []
        if self.claude_status and self.claude_status != "idle":
            parts.append(f"Claude: {self.claude_status}")
        if self.claude_cost:
            parts.append(self.claude_cost)
        status_text = CLAUDE_STATUS_SEPARATOR.join(parts)
        # Combine file path with Claude status
        if self._current_file_path and status_text:
            self.sub_title = f"{self._current_file_path}  {status_text}"
        elif self._current_file_path:
            self.sub_title = self._current_file_path
        elif status_text:
            self.sub_title = status_text
        else:
            self.sub_title = ""

    def action_save_file(self) -> None:
        """Save the current file in the editor (Ctrl+S)."""
        editor = self.query_one(EditorPanel)
        editor.save_current_file()
        self._sync_modified_paths()

    def on_text_area_changed(self, event) -> None:
        """Sync modified file indicators to the tree when editor content changes."""
        self._sync_modified_paths()

    def _sync_modified_paths(self) -> None:
        """Update the file tree's modified path indicators from the editor's buffers."""
        try:
            editor = self.query_one(EditorPanel)
            tree = self.query_one("#directory-tree", FilteredDirectoryTree)
            modified = {p.resolve() for p in editor.get_unsaved_files()}
            tree.set_modified_paths(modified)
        except Exception:
            pass

    def action_toggle_search(self) -> None:
        """Toggle the search overlay in the editor panel (Ctrl+F)."""
        try:
            editor = self.query_one(EditorPanel)
            editor.action_toggle_search()
        except Exception:
            pass

    def on_file_system_changed(self, event: FileSystemChanged) -> None:
        """Handle filesystem changes -- refresh the file tree.

        This is the SOLE handler for FileSystemChanged. App.py owns
        inter-panel coordination (FileTreePanel does NOT handle this).
        """
        try:
            file_tree = self.query_one(FileTreePanel)
            self.run_worker(
                file_tree.reload_preserving_state(), name="tree-reload"
            )
        except Exception:
            pass

    def action_restart_claude(self) -> None:
        """Restart the Claude Code subprocess."""
        try:
            chat = self.query_one(ChatPanel)
            chat.action_restart_claude()
        except Exception:
            pass

    def _stop_claude_pty(self) -> None:
        """Stop the Claude PTY subprocess if running."""
        try:
            from nano_claude.terminal.widget import TerminalWidget

            terminal = self.query_one("#claude-terminal", TerminalWidget)
            terminal.stop_pty()
        except Exception:
            pass

    def action_quit(self) -> None:
        """Quit the application, prompting if there are unsaved changes."""
        editor = self.query_one(EditorPanel)
        if editor.has_unsaved_changes():
            unsaved = editor.get_unsaved_files()
            self.push_screen(
                UnsavedChangesScreen(unsaved),
                callback=self._handle_quit_response,
            )
        else:
            self._graceful_exit()

    def _handle_quit_response(self, response: str) -> None:
        """Handle the response from the unsaved changes dialog."""
        if response == "save":
            editor = self.query_one(EditorPanel)
            for path in editor.get_unsaved_files():
                editor._buffer_manager.save_file(path)
            self._graceful_exit()
        elif response == "discard":
            self._graceful_exit()

    def _graceful_exit(self) -> None:
        """Shut down subprocesses with progress feedback, then exit."""
        self.sub_title = "Shutting down..."
        self.run_worker(self._shutdown_sequence(), exclusive=True, name="shutdown")

    async def _shutdown_sequence(self) -> None:
        """Async shutdown with status updates in the header."""
        import asyncio

        self.sub_title = "Stopping Claude Code..."
        self._stop_claude_pty()
        await asyncio.sleep(0.05)

        self.sub_title = "Stopping file watcher..."
        if hasattr(self, "_file_watcher"):
            self._file_watcher.stop()
        await asyncio.sleep(0.05)

        self.sub_title = "Exiting..."
        self.exit()
        # "cancel" -- do nothing, return to editor

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
