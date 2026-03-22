"""TerminalWidget: pyte-backed Textual widget with PTY I/O.

Renders a PTY subprocess (Claude Code CLI) inside a Textual widget
using pyte for terminal emulation and Rich for styled rendering.
"""

from __future__ import annotations

import os

import pyte
from rich.text import Text
from textual import events, work
from textual.message import Message
from textual.widget import Widget

from nano_claude.terminal.pty_manager import PtyManager, render_pyte_screen, translate_key
from nano_claude.terminal.status_parser import StatusParser

# Keys reserved for app-level bindings -- do NOT capture these.
RESERVED_KEYS: frozenset[str] = frozenset({
    "ctrl+b",
    "ctrl+e",
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

    DEFAULT_CSS = """
    TerminalWidget {
        overflow-y: auto;
        height: 1fr;
        width: 1fr;
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

    @work(thread=True, exclusive=True)
    def _start_read_loop(self) -> None:
        """Background thread: read PTY output and post messages."""
        fd = self._pty_manager.fd
        if fd is None:
            return

        while self._running:
            try:
                data = os.read(fd, 65536)
                if not data:
                    break
                decoded = data.decode("utf-8", errors="replace")
                self.post_message(PtyDataReceived(decoded))
            except OSError:
                break

        # Only handle exit if we're not shutting down — avoids deadlock
        # where call_from_thread blocks waiting for the main thread
        # which is waiting for this worker to finish.
        if self._running:
            try:
                self.app.call_from_thread(self._handle_pty_exit)
            except Exception:
                pass

    def on_pty_data_received(self, message: PtyDataReceived) -> None:
        """Feed received PTY data into the pyte terminal emulator and status parser."""
        if self._stream is not None:
            self._stream.feed(message.data)
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

        char = translate_key(event)
        if char is not None:
            try:
                os.write(self._pty_manager.fd, char.encode("utf-8"))
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

        lines = render_pyte_screen(self._screen)
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
