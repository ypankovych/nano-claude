"""TerminalWidget: pyte-backed Textual widget with PTY I/O.

Renders a PTY subprocess (Claude Code CLI) inside a Textual widget
using pyte for terminal emulation and Rich for styled rendering.
"""

from __future__ import annotations

import os
import re
import threading

import pyte
from rich.text import Text
from textual import events
from textual.message import Message
from textual.widget import Widget

# Escape sequences that pyte doesn't handle — strip before feeding to pyte stream.
# Claude Code uses kitty keyboard protocol (\x1b[>1u, \x1b[<u), xterm queries
# (\x1b[>0q), cursor style (\x1b[N q), and device attributes (\x1b[c).
# If pyte doesn't recognize these, trailing chars like 'u' or 'q' appear in the buffer.
_UNSUPPORTED_ESC_RE = re.compile(
    r"\x1b\[[<>?=]?[0-9;]*u"     # kitty keyboard: \x1b[>1u, \x1b[<u, \x1b[?u
    r"|\x1b\[>[0-9;]*[a-zA-Z]"   # CSI > sequences: \x1b[>0q (xterm version)
    r"|\x1b\[[0-9;]* [a-zA-Z]"   # CSI Sp sequences: \x1b[1 q (cursor style)
    r"|\x1b\[c"                   # Device attributes query
)

from nano_claude.models.code_context import write_to_pty_bracketed
from nano_claude.terminal.pty_manager import PtyManager, render_pyte_screen, translate_key
from nano_claude.terminal.status_parser import ClaudeState, StatusParser

# Keys reserved for app-level bindings -- do NOT capture these.
RESERVED_KEYS: frozenset[str] = frozenset({
    "ctrl+b",
    "ctrl+d",
    "ctrl+e",
    "ctrl+j",
    "ctrl+l",        # send selection to Claude
    "ctrl+p",        # pin/unpin ambient context
    "ctrl+r",
    "ctrl+q",
    "ctrl+equal",
    "ctrl+minus",
    "ctrl+backslash",
    "ctrl+h",
    "ctrl+s",
    "ctrl+f",
    "ctrl+1",
    "ctrl+2",
    "ctrl+3",
    "ctrl+shift+r",
    "tab",
    "shift+tab",
    "ctrl+tab",
})


class PtyDataReceived(Message):
    """Posted when data is received from the PTY subprocess."""

    def __init__(self, data: str) -> None:
        super().__init__()
        self.data = data


class PtyExited(Message):
    """Posted when the PTY subprocess exits."""

    def __init__(self, exit_code: int | None = None) -> None:
        super().__init__()
        self.exit_code = exit_code


class TerminalWidget(Widget, can_focus=True):
    """A Textual widget that embeds a PTY subprocess via pyte terminal emulation.

    Spawns a command (default: "claude") in a PTY, reads output in a
    background thread, feeds it through pyte for ANSI processing, and
    renders the screen buffer using Rich Text with full color support.
    """

    # Hide Textual's native cursor — pyte renders its own via reverse style
    CURSOR_BLINK = False
    show_cursor = False

    DEFAULT_CSS = """
    TerminalWidget {
        overflow-y: auto;
        height: 1fr;
        width: 1fr;
    }
    TerminalWidget:focus {
        /* No Textual cursor — pyte handles it */
    }
    """

    def __init__(self, command: str = "claude", **kwargs) -> None:
        super().__init__(**kwargs)
        self._command = command
        self._screen: pyte.HistoryScreen | None = None
        self._stream: pyte.Stream | None = None
        self._pty_manager = PtyManager()
        self._status_parser = StatusParser()
        self._running = False
        self._get_pinned_context: callable | None = None  # Set by app for ambient context

    def on_mount(self) -> None:
        """Defer PTY start until layout determines widget size."""
        self.call_later(self._start_pty)

    def _start_pty(self) -> None:
        """Initialize pyte screen and spawn the PTY subprocess."""
        cols = max(self.size.width, 10)
        rows = max(self.size.height, 5)

        self._screen = pyte.HistoryScreen(cols, rows, history=10000)
        self._stream = pyte.Stream(self._screen)
        self._stream.attach(self._screen)

        try:
            self._pty_manager.spawn(self._command, cols, rows)
            self._running = True
            self._start_read_loop()
        except FileNotFoundError:
            # Command not found -- will be handled by ChatPanel
            self._running = False

    def _start_read_loop(self) -> None:
        """Start a daemon thread to read PTY output.

        Uses a raw daemon thread instead of @work(thread=True) so Textual
        doesn't wait for it to join on exit — instant quit.
        """
        fd = self._pty_manager.fd
        if fd is None:
            return

        def _read_loop():
            while self._running:
                try:
                    data = os.read(fd, 65536)
                    if not data:
                        break
                    decoded = data.decode("utf-8", errors="replace")
                    self.post_message(PtyDataReceived(decoded))
                except OSError:
                    break

            if self._running:
                try:
                    self.app.call_from_thread(self._handle_pty_exit)
                except Exception:
                    pass

        t = threading.Thread(target=_read_loop, daemon=True)
        t.start()

    def on_pty_data_received(self, message: PtyDataReceived) -> None:
        """Feed received PTY data into the pyte terminal emulator and status parser."""
        if self._stream is not None:
            # Strip escape sequences pyte doesn't handle (kitty keyboard, etc.)
            cleaned = _UNSUPPORTED_ESC_RE.sub("", message.data)
            self._stream.feed(cleaned)
            self.refresh()
        # Feed data to status parser and bubble any detected messages
        for msg in self._status_parser.feed(message.data):
            self.post_message(msg)

    def _handle_pty_exit(self) -> None:
        """Handle PTY subprocess exit."""
        self._running = False
        exit_code: int | None = None
        try:
            if self._pty_manager.pid is not None:
                _, status = os.waitpid(self._pty_manager.pid, os.WNOHANG)
                if os.WIFEXITED(status):
                    exit_code = os.WEXITSTATUS(status)
        except (OSError, ChildProcessError):
            pass
        self.post_message(PtyExited(exit_code=exit_code))

    def on_key(self, event: events.Key) -> None:
        """Forward key events to the PTY subprocess."""
        if not self._running or self._pty_manager.fd is None:
            return

        # Let app-level bindings bubble up
        if event.key in RESERVED_KEYS:
            return

        fd = self._pty_manager.fd

        # Ambient context injection: on Enter, if context is pinned and Claude is idle
        if event.key == "enter" and self._get_pinned_context is not None:
            context_text = self._get_pinned_context()
            if context_text and self._status_parser.current_state == ClaudeState.IDLE:
                write_to_pty_bracketed(fd, context_text)

        char = translate_key(event)
        if char is not None:
            try:
                os.write(fd, char.encode("utf-8"))
            except OSError:
                pass
            event.prevent_default()

    def on_resize(self, event: events.Resize) -> None:
        """Resize the pyte screen and PTY when the widget resizes."""
        if self._running and self._screen is not None:
            new_cols = max(event.size.width, 10)
            new_rows = max(event.size.height, 5)
            try:
                self._screen.resize(new_rows, new_cols)
                self._pty_manager.resize(new_cols, new_rows)
            except Exception:
                pass

    def render(self) -> Text:
        """Render the pyte screen buffer as Rich Text."""
        if self._screen is None:
            return Text("Starting Claude Code...")

        lines = render_pyte_screen(self._screen, cursor_visible=False)
        result = Text()
        for i, line in enumerate(lines):
            if i > 0:
                result.append("\n")
            result.append_text(line)
        return result

    def stop_pty(self) -> None:
        """Stop the PTY subprocess."""
        self._running = False
        self._pty_manager.stop()

    def restart_pty(self) -> None:
        """Restart the PTY subprocess."""
        self.stop_pty()
        self._status_parser.reset()
        self.call_later(self._start_pty)
