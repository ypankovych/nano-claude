"""Chat panel -- embedded Claude Code CLI via PTY terminal emulation."""

from __future__ import annotations

import shutil

from textual.app import ComposeResult
from textual.widgets import Static

from nano_claude.config.settings import CLAUDE_EXITED_MESSAGE, CLAUDE_NOT_FOUND_MESSAGE
from nano_claude.panels.base import BasePanel
from nano_claude.terminal.widget import PtyExited, TerminalWidget


class ChatPanel(BasePanel):
    """Right panel: Claude Code CLI interface.

    Embeds the real Claude Code CLI via TerminalWidget when the 'claude'
    command is available on PATH. Shows install instructions otherwise.
    Handles process exit with restart support via Ctrl+Shift+R.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._claude_available: bool = shutil.which("claude") is not None

    def compose(self) -> ComposeResult:
        if not self._claude_available:
            msg = Static(CLAUDE_NOT_FOUND_MESSAGE, id="claude-not-found")
            msg.can_focus = True
            yield msg
        else:
            yield TerminalWidget(command="claude", id="claude-terminal")

    def on_pty_exited(self, message: PtyExited) -> None:
        """Handle PTY subprocess exit -- show exit message with restart hint."""
        # Remove the terminal widget if present
        try:
            terminal = self.query_one("#claude-terminal", TerminalWidget)
            terminal.remove()
        except Exception:
            pass

        msg = Static(
            CLAUDE_EXITED_MESSAGE.format(exit_code=message.exit_code),
            id="claude-exited",
        )
        msg.can_focus = True
        self.mount(msg)

    def action_restart_claude(self) -> None:
        """Restart the Claude Code subprocess."""
        # Remove exit message if present
        try:
            exited_msg = self.query_one("#claude-exited", Static)
            exited_msg.remove()
        except Exception:
            pass

        # Check if a terminal widget already exists
        try:
            terminal = self.query_one("#claude-terminal", TerminalWidget)
            terminal.restart_pty()
        except Exception:
            # No terminal widget -- mount a new one
            self.mount(TerminalWidget(command="claude", id="claude-terminal"))
