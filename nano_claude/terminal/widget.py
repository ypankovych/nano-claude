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
from nano_claude.terminal.pty_manager import PtyManager, _render_history_line, render_pyte_screen, translate_key
from nano_claude.terminal.status_parser import ClaudeState, StatusParser

# Keys reserved for app-level bindings -- do NOT capture these.
RESERVED_KEYS: frozenset[str] = frozenset({
    "ctrl+b",
    "ctrl+d",
    "ctrl+e",
    "ctrl+f",
    "ctrl+h",
    "ctrl+j",
    "ctrl+l",        # send selection to Claude
    "ctrl+n",        # new terminal tab
    "ctrl+p",        # pin/unpin ambient context
    "ctrl+q",
    "ctrl+r",
    "ctrl+s",
    "ctrl+t",        # toggle terminal panel
    "ctrl+equal",
    "ctrl+minus",
    "ctrl+backslash",
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


class CloseTabRequested(Message):
    """Posted when user presses Ctrl+W to close this terminal tab."""
    pass


class SwitchTabRequested(Message):
    """Posted when user presses Ctrl+PageUp/PageDown to switch tabs."""

    def __init__(self, direction: int) -> None:
        super().__init__()
        self.direction = direction  # -1 = prev, +1 = next


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
        self._input_buffer: str = ""  # Track user's typed chars for context prepend
        self._render_dirty = False  # Throttle flag for ~30fps rendering
        self._render_timer: threading.Timer | None = None
        self._RENDER_INTERVAL = 0.033  # ~30fps
        self._scroll_lines = 0  # Lines scrolled up from live view

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
        """Feed received PTY data into the pyte terminal emulator and status parser.

        Pyte screen buffer is updated immediately but visual refresh is
        throttled to ~30fps to keep the rest of the app responsive.
        """
        if not self._running:
            return
        if self._stream is not None:
            # Strip escape sequences pyte doesn't handle (kitty keyboard, etc.)
            cleaned = _UNSUPPORTED_ESC_RE.sub("", message.data)
            self._stream.feed(cleaned)
            self._schedule_refresh()
        # Feed data to status parser and bubble any detected messages
        for msg in self._status_parser.feed(message.data):
            self.post_message(msg)

    def _schedule_refresh(self) -> None:
        """Mark screen dirty and schedule a refresh if not already pending.

        Coalesces rapid PTY updates into ~30fps visual refreshes so the
        rest of the app stays responsive during heavy Claude output.
        """
        self._render_dirty = True
        if self._render_timer is None or not self._render_timer.is_alive():
            self._render_timer = threading.Timer(
                self._RENDER_INTERVAL, self._do_throttled_refresh
            )
            self._render_timer.daemon = True
            self._render_timer.start()

    def _do_throttled_refresh(self) -> None:
        """Flush pending render from the timer thread."""
        if not self._running:
            return
        if self._render_dirty:
            self._render_dirty = False
            try:
                self.app.call_from_thread(self._refresh_and_scroll)
            except Exception:
                pass

    def _refresh_and_scroll(self) -> None:
        """Refresh content."""
        self.refresh()

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

        # Snap back to live view on any keypress
        if self._scroll_lines > 0:
            self._scroll_lines = 0
            self.refresh()

        # Ctrl+W: request tab close (bubbles to TerminalPanel)
        if event.key == "ctrl+w":
            event.stop()
            self.post_message(CloseTabRequested())
            return

        # Ctrl+Shift+Left/Right: switch tabs
        if event.key == "ctrl+shift+left":
            event.stop()
            self.post_message(SwitchTabRequested(-1))
            return
        if event.key == "ctrl+shift+right":
            event.stop()
            self.post_message(SwitchTabRequested(1))
            return

        # Let app-level bindings bubble up
        if event.key in RESERVED_KEYS:
            return

        fd = self._pty_manager.fd

        # Ambient context injection: on Enter, clear input, prepend context
        # to user's typed text, and submit as one combined prompt.
        if event.key == "enter":
            if (
                self._get_pinned_context is not None
                and self._input_buffer
                and self._status_parser.current_state == ClaudeState.IDLE
            ):
                context_text = self._get_pinned_context()
                if context_text:
                    user_text = self._input_buffer
                    self._input_buffer = ""
                    # Clear the visible input line (Ctrl+U kills the line)
                    try:
                        os.write(fd, b"\x15")
                    except OSError:
                        pass
                    # Write context + user's prompt as one message
                    full_prompt = context_text + "\n\n" + user_text
                    write_to_pty_bracketed(fd, full_prompt)
                    # Submit
                    try:
                        os.write(fd, b"\r")
                    except OSError:
                        pass
                    event.prevent_default()
                    return
            # Normal Enter — reset buffer
            self._input_buffer = ""

        # Track typed characters for input buffer
        if event.key == "backspace":
            if self._input_buffer:
                self._input_buffer = self._input_buffer[:-1]
        elif event.character and event.character.isprintable():
            self._input_buffer += event.character

        char = translate_key(event)
        if char is not None:
            try:
                os.write(fd, char.encode("utf-8"))
            except OSError:
                pass
            event.stop()

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
        """Render the pyte screen buffer, with history when scrolled up."""
        if self._screen is None:
            return Text("Starting Claude Code...")

        if self._scroll_lines == 0:
            # Live view — just render screen buffer
            lines = render_pyte_screen(self._screen, cursor_visible=False)
        else:
            # Scrolled up — mix history + screen lines
            history = list(self._screen.history.top) if hasattr(self._screen, "history") else []
            cols = self._screen.columns
            screen_lines = render_pyte_screen(self._screen, cursor_visible=False)
            history_rendered = [_render_history_line(h, cols) for h in history]
            all_lines = history_rendered + screen_lines
            visible = self._screen.lines
            end = len(all_lines) - self._scroll_lines
            start = max(0, end - visible)
            end = max(start, end)
            lines = all_lines[start:end]
            # Pad if not enough lines
            while len(lines) < visible:
                lines.append(Text(""))

        result = Text()
        for i, line in enumerate(lines):
            if i > 0:
                result.append("\n")
            result.append_text(line)
        return result

    def on_mouse_scroll_up(self, event) -> None:
        """Scroll up through terminal history."""
        if self._screen is not None and hasattr(self._screen, "history"):
            max_scroll = len(self._screen.history.top)
            if max_scroll > 0:
                self._scroll_lines = min(self._scroll_lines + 3, max_scroll)
                self.refresh()
            event.stop()

    def on_mouse_scroll_down(self, event) -> None:
        """Scroll down through terminal history."""
        if self._scroll_lines > 0:
            self._scroll_lines = max(0, self._scroll_lines - 3)
            self.refresh()
            event.stop()

    def stop_pty(self) -> None:
        """Stop the PTY subprocess."""
        self._running = False
        if self._render_timer is not None:
            self._render_timer.cancel()
            self._render_timer = None
        self._pty_manager.stop()

    def restart_pty(self) -> None:
        """Restart the PTY subprocess."""
        self.stop_pty()
        self._status_parser.reset()
        self.call_later(self._start_pty)
