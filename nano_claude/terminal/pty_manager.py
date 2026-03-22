"""PTY subprocess lifecycle management.

This module manages the PTY subprocess for Claude Code CLI.
It does NOT depend on Textual -- pure stdlib + pyte.
"""

from __future__ import annotations

import fcntl
import os
import pty
import signal
import struct
import termios
import time

import pyte
from rich.style import Style
from rich.text import Text


# ---------------------------------------------------------------------------
# Key mapping: Textual key names -> ANSI escape sequences
# ---------------------------------------------------------------------------

KEY_MAP: dict[str, str] = {
    # Arrow keys
    "up": "\x1b[A",
    "down": "\x1b[B",
    "right": "\x1b[C",
    "left": "\x1b[D",
    # Navigation
    "home": "\x1b[H",
    "end": "\x1b[F",
    "pageup": "\x1b[5~",
    "pagedown": "\x1b[6~",
    "delete": "\x1b[3~",
    "insert": "\x1b[2~",
    # Control keys
    "enter": "\r",
    "backspace": "\x7f",
    "tab": "\t",
    "escape": "\x1b",
    # Function keys (xterm standard)
    "f1": "\x1bOP",
    "f2": "\x1bOQ",
    "f3": "\x1bOR",
    "f4": "\x1bOS",
    "f5": "\x1b[15~",
    "f6": "\x1b[17~",
    "f7": "\x1b[18~",
    "f8": "\x1b[19~",
    "f9": "\x1b[20~",
    "f10": "\x1b[21~",
    "f11": "\x1b[23~",
    "f12": "\x1b[24~",
}


def translate_key(event) -> str | None:
    """Translate a Textual key event to a string suitable for PTY write.

    Checks KEY_MAP first, then ctrl+letter combinations, then
    event.character for single printable characters.

    Returns None for unrecognized keys.
    """
    key = event.key

    # 1. Direct lookup in KEY_MAP
    if key in KEY_MAP:
        return KEY_MAP[key]

    # 2. Ctrl+letter -> control character (chr(ord(LETTER) - 64))
    if key.startswith("ctrl+") and len(key) == 6:
        letter = key[5]
        if letter.isalpha():
            return chr(ord(letter.upper()) - 64)

    # 3. Printable character from event
    if event.character and len(event.character) == 1:
        return event.character

    return None


# ---------------------------------------------------------------------------
# Pyte color mapping
# ---------------------------------------------------------------------------

PYTE_COLOR_MAP: dict[str, str] = {
    "black": "black",
    "red": "red",
    "green": "green",
    "brown": "yellow",
    "blue": "blue",
    "magenta": "magenta",
    "cyan": "cyan",
    "white": "white",
    "default": "default",
    # Bright variants
    "brightblack": "bright_black",
    "brightred": "bright_red",
    "brightgreen": "bright_green",
    "brightbrown": "bright_yellow",
    "brightblue": "bright_blue",
    "brightmagenta": "bright_magenta",
    "brightcyan": "bright_cyan",
    "brightwhite": "bright_white",
}


def _resolve_color(color_name: str) -> str | None:
    """Resolve a pyte color name to a Rich color string.

    Handles named colors via PYTE_COLOR_MAP and 256-color/hex codes.
    Returns None for 'default' to use terminal default.
    """
    if not color_name or color_name == "default":
        return None

    # Named color lookup
    mapped = PYTE_COLOR_MAP.get(color_name)
    if mapped and mapped != "default":
        return mapped

    # If it looks like a hex code (6 hex digits), prefix with #
    if len(color_name) == 6:
        try:
            int(color_name, 16)
            return f"#{color_name}"
        except ValueError:
            pass

    # Try as integer (256-color index)
    try:
        idx = int(color_name)
        return f"color({idx})"
    except (ValueError, TypeError):
        pass

    return None


def render_pyte_screen(screen: pyte.Screen, cursor_visible: bool = True) -> list[Text]:
    """Convert a pyte Screen buffer to a list of Rich Text lines.

    Iterates screen.buffer row by row, char by char. For each Char,
    builds a rich.style.Style from fg/bg/bold/italics/underscore/reverse
    attributes using PYTE_COLOR_MAP. Returns list of Text lines.
    """
    lines: list[Text] = []

    for row_idx in range(screen.lines):
        line = Text()
        row = screen.buffer[row_idx]
        for col_idx in range(screen.columns):
            char = row[col_idx]

            fg = _resolve_color(char.fg)
            bg = _resolve_color(char.bg)

            style = Style(
                color=fg,
                bgcolor=bg,
                bold=char.bold,
                italic=char.italics,
                underline=char.underscore,
                reverse=char.reverse,
            )

            # Cursor highlighting
            if (
                cursor_visible
                and row_idx == screen.cursor.y
                and col_idx == screen.cursor.x
            ):
                style = style + Style(reverse=True)

            line.append(char.data, style=style)

        lines.append(line)

    return lines


# ---------------------------------------------------------------------------
# PTY Manager
# ---------------------------------------------------------------------------


class PtyManager:
    """Manages one PTY subprocess lifecycle: spawn, read, resize, cleanup."""

    def __init__(self) -> None:
        self._pid: int | None = None
        self._fd: int | None = None

    @property
    def pid(self) -> int | None:
        """Return the PTY child process PID, or None if not spawned."""
        return self._pid

    @property
    def fd(self) -> int | None:
        """Return the PTY master file descriptor, or None if not spawned."""
        return self._fd

    @property
    def is_running(self) -> bool:
        """Check if the PTY child process is still running."""
        if self._pid is None:
            return False
        try:
            result_pid, _ = os.waitpid(self._pid, os.WNOHANG)
            return result_pid == 0
        except ChildProcessError:
            return False

    def spawn(self, command: str, cols: int, rows: int) -> tuple[int, int]:
        """Spawn a PTY subprocess running the given command.

        Child process sets environment (TERM, COLORTERM, COLUMNS, LINES)
        and then exec's the command. Parent stores pid/fd and configures
        the terminal window size.

        Returns (pid, fd) tuple.
        """
        child_pid, master_fd = pty.fork()

        if child_pid == 0:
            # Child process
            env = os.environ.copy()
            env["TERM"] = "xterm-256color"
            env["COLORTERM"] = "truecolor"
            env["COLUMNS"] = str(cols)
            env["LINES"] = str(rows)
            os.execvpe(command, [command], env)
            # execvpe does not return
        else:
            # Parent process
            self._pid = child_pid
            self._fd = master_fd
            # Set terminal window size
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
            return (child_pid, master_fd)

    def stop(self) -> None:
        """Stop the PTY subprocess.

        Closes the master fd FIRST to unblock any read threads, then
        sends SIGTERM to the child, waits briefly, escalates to SIGKILL.
        """
        # Close fd FIRST to unblock the read thread (os.read raises OSError)
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None

        if self._pid is not None:
            # SIGKILL immediately — claude is a subprocess we own,
            # no need to wait for graceful shutdown on quit.
            try:
                os.kill(self._pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
            try:
                os.waitpid(self._pid, os.WNOHANG)
            except (OSError, ChildProcessError):
                pass
            self._pid = None

    def resize(self, cols: int, rows: int) -> None:
        """Resize the PTY terminal window."""
        if self._fd is not None:
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self._fd, termios.TIOCSWINSZ, winsize)
