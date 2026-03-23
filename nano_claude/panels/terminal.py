"""Terminal panel -- multi-tab shell sessions via PTY terminal emulation."""

from __future__ import annotations

import os

from rich.text import Text
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import ContentSwitcher, Static

from nano_claude.config.settings import (
    SHELL_EXITED_MESSAGE,
    TERMINAL_MAX_TABS,
    TERMINAL_PANEL_HEIGHT,
    TERMINAL_STATUS_IDLE,
    TERMINAL_STATUS_RUNNING,
)
from nano_claude.panels.base import BasePanel
from nano_claude.terminal.widget import PtyExited, TerminalWidget


class TerminalPanel(BasePanel):
    """Bottom panel: multi-tab shell sessions.

    Manages multiple shell tabs via ContentSwitcher. Starts minimized
    (status line only) and expands on demand. Each tab spawns the user's
    $SHELL in a PTY via TerminalWidget.
    """

    DEFAULT_CSS = """
    TerminalPanel {
        height: auto;
    }
    TerminalPanel #terminal-tab-bar {
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    TerminalPanel #terminal-status-line {
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    is_minimized = reactive(True)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._tab_counter: int = 0

    def compose(self) -> ComposeResult:
        self.panel_title = "Terminal"
        yield Static("", id="terminal-tab-bar")
        yield ContentSwitcher(id="terminal-switcher")
        yield Static(TERMINAL_STATUS_IDLE, id="terminal-status-line")

    def on_mount(self) -> None:
        """Set initial display states (minimized by default)."""
        self._apply_minimized_state()

    def add_tab(self) -> None:
        """Add a new shell tab to the terminal panel."""
        switcher = self.query_one("#terminal-switcher", ContentSwitcher)

        if len(list(switcher.children)) >= TERMINAL_MAX_TABS:
            self.notify(
                f"Maximum of {TERMINAL_MAX_TABS} terminal tabs reached.",
                severity="warning",
            )
            return

        self._tab_counter += 1
        tab_id = f"shell-{self._tab_counter}"
        shell = os.environ.get("SHELL", "/bin/sh")
        terminal = TerminalWidget(command=shell, id=tab_id)
        switcher.mount(terminal)
        switcher.current = tab_id
        self._update_tab_bar()
        terminal.focus()

    def close_active_tab(self) -> None:
        """Close the currently active tab."""
        switcher = self.query_one("#terminal-switcher", ContentSwitcher)

        if switcher.current is None:
            return

        current_id = switcher.current

        # Stop PTY before removal
        try:
            current_widget = switcher.get_child_by_id(current_id)
            if isinstance(current_widget, TerminalWidget):
                current_widget.stop_pty()
        except Exception:
            pass

        remaining = [c for c in switcher.children if c.id != current_id]

        if remaining:
            switcher.current = remaining[-1].id
        else:
            switcher.current = None

        try:
            switcher.get_child_by_id(current_id).remove()
        except Exception:
            pass

        self._update_tab_bar()

        if not remaining:
            self.minimize()

    def minimize(self) -> None:
        """Minimize the terminal panel to a single status line."""
        self.is_minimized = True

    def restore(self) -> None:
        """Restore the terminal panel to full size."""
        switcher = self.query_one("#terminal-switcher", ContentSwitcher)

        if not list(switcher.children):
            self.add_tab()

        self.is_minimized = False

    def watch_is_minimized(self, minimized: bool) -> None:
        """React to minimized state changes."""
        self._apply_minimized_state()

    def _apply_minimized_state(self) -> None:
        """Apply visual state based on is_minimized flag."""
        try:
            tab_bar = self.query_one("#terminal-tab-bar", Static)
            switcher = self.query_one("#terminal-switcher", ContentSwitcher)
            status_line = self.query_one("#terminal-status-line", Static)
        except Exception:
            return

        if self.is_minimized:
            tab_bar.display = False
            switcher.display = False
            status_line.display = True
            self.styles.height = "auto"
        else:
            tab_bar.display = True
            switcher.display = True
            status_line.display = False
            self.styles.height = TERMINAL_PANEL_HEIGHT

    def _update_tab_bar(self) -> None:
        """Update the tab bar display and status text."""
        try:
            switcher = self.query_one("#terminal-switcher", ContentSwitcher)
            tab_bar = self.query_one("#terminal-tab-bar", Static)
        except Exception:
            return

        children = list(switcher.children)
        parts: list[str] = []

        for i, child in enumerate(children, 1):
            if child.id == switcher.current:
                parts.append(f"[bold reverse] {i} [/]")
            else:
                parts.append(f" {i} ")

        tab_bar.update(Text.from_markup(" ".join(parts)))
        self._update_status_text()

    def _update_status_text(self) -> None:
        """Update the status line text with current tab count."""
        try:
            switcher = self.query_one("#terminal-switcher", ContentSwitcher)
            status_line = self.query_one("#terminal-status-line", Static)
        except Exception:
            return

        count = len(list(switcher.children))
        if count > 0:
            status_line.update(
                TERMINAL_STATUS_RUNNING.format(
                    count=count, s="s" if count != 1 else ""
                )
            )
        else:
            status_line.update(TERMINAL_STATUS_IDLE)

    def on_pty_exited(self, message: PtyExited) -> None:
        """Handle shell exit within a tab."""
        switcher = self.query_one("#terminal-switcher", ContentSwitcher)

        # Find which terminal sent the exit message
        sender = message._sender
        if not isinstance(sender, TerminalWidget):
            return

        terminal_id = sender.id
        if terminal_id is None:
            return

        # Create an exit message widget
        exit_id = f"exited-{terminal_id}"
        exit_msg = Static(
            SHELL_EXITED_MESSAGE.format(exit_code=message.exit_code),
            id=exit_id,
        )
        exit_msg.can_focus = True

        # Mount the exit message, switch to it, remove the dead terminal
        switcher.mount(exit_msg)
        switcher.current = exit_id

        try:
            sender.remove()
        except Exception:
            pass

        self._update_tab_bar()

    def get_active_terminal(self) -> TerminalWidget | None:
        """Return the currently active TerminalWidget, or None."""
        try:
            switcher = self.query_one("#terminal-switcher", ContentSwitcher)
            if switcher.current is None:
                return None
            child = switcher.get_child_by_id(switcher.current)
            if isinstance(child, TerminalWidget):
                return child
        except Exception:
            pass
        return None

    def stop_all_ptys(self) -> None:
        """Stop all running PTY subprocesses."""
        try:
            switcher = self.query_one("#terminal-switcher", ContentSwitcher)
            for child in switcher.children:
                if isinstance(child, TerminalWidget):
                    try:
                        child.stop_pty()
                    except Exception:
                        pass
        except Exception:
            pass

    @property
    def tab_count(self) -> int:
        """Return the number of open tabs."""
        try:
            switcher = self.query_one("#terminal-switcher", ContentSwitcher)
            return len(list(switcher.children))
        except Exception:
            return 0
