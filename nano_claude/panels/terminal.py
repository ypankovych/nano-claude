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
from nano_claude.terminal.widget import CloseTabRequested, PtyExited, SwitchTabRequested, TerminalWidget


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
        self._dead_tabs: set[str] = set()

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

        if len([c for c in switcher.children if c.id not in self._dead_tabs]) >= TERMINAL_MAX_TABS:
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

    def on_close_tab_requested(self, message: CloseTabRequested) -> None:
        """Handle Ctrl+W from a child TerminalWidget."""
        message.stop()
        sender = message._sender
        if not isinstance(sender, TerminalWidget):
            return

        switcher = self.query_one("#terminal-switcher", ContentSwitcher)
        tab_id = sender.id

        # Stop PTY, mark dead
        sender._closed_by_user = True
        sender.stop_pty()
        self._dead_tabs.add(tab_id)

        # Find remaining live tabs
        others = [c for c in switcher.children if c.id not in self._dead_tabs]

        # Switch before removing
        if others:
            switcher.current = others[-1].id
        else:
            switcher.current = None

        # Remove the dead widget (async — completes next tick)
        sender.remove()

        self._update_tab_bar()

        if others:
            if isinstance(others[-1], TerminalWidget):
                others[-1].focus()
        else:
            # Last tab closed — create a fresh one
            self.add_tab()

    def on_switch_tab_requested(self, message: SwitchTabRequested) -> None:
        """Handle Ctrl+PageUp/PageDown to switch tabs."""
        message.stop()
        switcher = self.query_one("#terminal-switcher", ContentSwitcher)
        live = [c for c in switcher.children if c.id not in self._dead_tabs]
        if len(live) < 2:
            return
        current_idx = next(
            (i for i, c in enumerate(live) if c.id == switcher.current), 0
        )
        new_idx = (current_idx + message.direction) % len(live)
        switcher.current = live[new_idx].id
        self._update_tab_bar()
        if isinstance(live[new_idx], TerminalWidget):
            live[new_idx].focus()

    def close_active_tab(self) -> None:
        """Programmatic close (used by tests / external callers)."""
        terminal = self.get_active_terminal()
        if terminal is not None:
            terminal.post_message(CloseTabRequested())

    def on_pty_exited(self, message: PtyExited) -> None:
        """Handle natural shell exit (user typed 'exit')."""
        sender = message._sender
        if not isinstance(sender, TerminalWidget):
            return
        if getattr(sender, "_closed_by_user", False):
            return

        terminal_id = sender.id
        if terminal_id is None:
            return

        switcher = self.query_one("#terminal-switcher", ContentSwitcher)
        exit_id = f"exited-{terminal_id}"
        exit_msg = Static(
            SHELL_EXITED_MESSAGE.format(exit_code=message.exit_code),
            id=exit_id,
        )
        exit_msg.can_focus = True
        switcher.mount(exit_msg)
        switcher.current = exit_id
        try:
            sender.remove()
        except Exception:
            pass
        self._update_tab_bar()

    def minimize(self) -> None:
        """Minimize the terminal panel to a single status line."""
        self.is_minimized = True

    def restore(self) -> None:
        """Restore the terminal panel to full size."""
        switcher = self.query_one("#terminal-switcher", ContentSwitcher)
        live = [c for c in switcher.children if c.id not in self._dead_tabs]
        if not live:
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

        children = [c for c in switcher.children if c.id not in self._dead_tabs]
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

        count = len([c for c in switcher.children if c.id not in self._dead_tabs])
        if count > 0:
            status_line.update(
                TERMINAL_STATUS_RUNNING.format(
                    count=count, s="s" if count != 1 else ""
                )
            )
        else:
            status_line.update(TERMINAL_STATUS_IDLE)

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
            return len([c for c in switcher.children if c.id not in self._dead_tabs])
        except Exception:
            return 0
