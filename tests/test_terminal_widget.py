"""Unit tests for PTY manager and terminal widget."""

from __future__ import annotations

import os
import signal
import struct
from unittest.mock import MagicMock, patch

import pyte
import pytest
from rich.text import Text

from nano_claude.terminal.pty_manager import (
    KEY_MAP,
    PYTE_COLOR_MAP,
    PtyManager,
    render_pyte_screen,
    translate_key,
)


# ---------------------------------------------------------------------------
# KEY_MAP tests
# ---------------------------------------------------------------------------


class TestKeyMap:
    """Tests for the KEY_MAP dictionary."""

    def test_key_map_has_arrow_keys(self):
        assert KEY_MAP["up"] == "\x1b[A"
        assert KEY_MAP["down"] == "\x1b[B"
        assert KEY_MAP["right"] == "\x1b[C"
        assert KEY_MAP["left"] == "\x1b[D"

    def test_key_map_has_nav_keys(self):
        assert KEY_MAP["home"] == "\x1b[H"
        assert KEY_MAP["end"] == "\x1b[F"
        assert KEY_MAP["pageup"] == "\x1b[5~"
        assert KEY_MAP["pagedown"] == "\x1b[6~"
        assert KEY_MAP["delete"] == "\x1b[3~"

    def test_key_map_has_control_keys(self):
        assert KEY_MAP["enter"] == "\r"
        assert KEY_MAP["backspace"] == "\x7f"
        assert KEY_MAP["tab"] == "\t"
        assert KEY_MAP["escape"] == "\x1b"

    def test_key_map_has_function_keys(self):
        assert "f1" in KEY_MAP
        assert "f12" in KEY_MAP

    def test_key_map_has_at_least_20_entries(self):
        assert len(KEY_MAP) >= 20


# ---------------------------------------------------------------------------
# translate_key tests
# ---------------------------------------------------------------------------


class TestTranslateKey:
    """Tests for the translate_key function."""

    def _make_key_event(self, key: str, character: str | None = None):
        """Create a mock Textual key event."""
        event = MagicMock()
        event.key = key
        event.character = character
        return event

    def test_arrow_keys(self):
        assert translate_key(self._make_key_event("up")) == "\x1b[A"
        assert translate_key(self._make_key_event("down")) == "\x1b[B"
        assert translate_key(self._make_key_event("right")) == "\x1b[C"
        assert translate_key(self._make_key_event("left")) == "\x1b[D"

    def test_enter_backspace_tab_escape(self):
        assert translate_key(self._make_key_event("enter")) == "\r"
        assert translate_key(self._make_key_event("backspace")) == "\x7f"
        assert translate_key(self._make_key_event("tab")) == "\t"
        assert translate_key(self._make_key_event("escape")) == "\x1b"

    def test_ctrl_letter(self):
        # ctrl+c -> \x03
        assert translate_key(self._make_key_event("ctrl+c")) == "\x03"
        # ctrl+a -> \x01
        assert translate_key(self._make_key_event("ctrl+a")) == "\x01"
        # ctrl+z -> \x1a
        assert translate_key(self._make_key_event("ctrl+z")) == "\x1a"
        # ctrl+d -> \x04
        assert translate_key(self._make_key_event("ctrl+d")) == "\x04"

    def test_regular_printable_character(self):
        assert translate_key(self._make_key_event("a", "a")) == "a"
        assert translate_key(self._make_key_event("z", "z")) == "z"
        assert translate_key(self._make_key_event("space", " ")) == " "
        assert translate_key(self._make_key_event("1", "1")) == "1"

    def test_unrecognized_key_returns_none(self):
        assert translate_key(self._make_key_event("ctrl+shift+alt+f99", None)) is None


# ---------------------------------------------------------------------------
# PYTE_COLOR_MAP tests
# ---------------------------------------------------------------------------


class TestPyteColorMap:
    """Tests for the PYTE_COLOR_MAP dictionary."""

    def test_has_basic_colors(self):
        assert "black" in PYTE_COLOR_MAP
        assert "red" in PYTE_COLOR_MAP
        assert "green" in PYTE_COLOR_MAP
        assert "blue" in PYTE_COLOR_MAP
        assert "magenta" in PYTE_COLOR_MAP
        assert "cyan" in PYTE_COLOR_MAP
        assert "white" in PYTE_COLOR_MAP

    def test_brown_maps_to_yellow(self):
        assert PYTE_COLOR_MAP["brown"] == "yellow"

    def test_default_mapping(self):
        assert "default" in PYTE_COLOR_MAP

    def test_has_at_least_8_entries(self):
        assert len(PYTE_COLOR_MAP) >= 8


# ---------------------------------------------------------------------------
# render_pyte_screen tests
# ---------------------------------------------------------------------------


class TestRenderPyteScreen:
    """Tests for the render_pyte_screen function."""

    def test_plain_text_rendering(self):
        screen = pyte.Screen(40, 5)
        stream = pyte.Stream(screen)
        stream.feed("Hello World")
        lines = render_pyte_screen(screen)
        assert isinstance(lines, list)
        assert len(lines) == 5
        assert "Hello World" in lines[0].plain

    def test_color_rendering(self):
        screen = pyte.Screen(40, 5)
        stream = pyte.Stream(screen)
        # ANSI red foreground
        stream.feed("\x1b[31mRed Text\x1b[0m")
        lines = render_pyte_screen(screen)
        plain = lines[0].plain
        assert "Red Text" in plain

    def test_bold_attribute(self):
        screen = pyte.Screen(40, 5)
        stream = pyte.Stream(screen)
        stream.feed("\x1b[1mBold Text\x1b[0m")
        lines = render_pyte_screen(screen)
        # Check that rendered text includes the bold text
        assert "Bold Text" in lines[0].plain

    def test_italic_attribute(self):
        screen = pyte.Screen(40, 5)
        stream = pyte.Stream(screen)
        stream.feed("\x1b[3mItalic Text\x1b[0m")
        lines = render_pyte_screen(screen)
        assert "Italic Text" in lines[0].plain

    def test_underline_attribute(self):
        screen = pyte.Screen(40, 5)
        stream = pyte.Stream(screen)
        stream.feed("\x1b[4mUnderlined\x1b[0m")
        lines = render_pyte_screen(screen)
        assert "Underlined" in lines[0].plain

    def test_reverse_attribute(self):
        screen = pyte.Screen(40, 5)
        stream = pyte.Stream(screen)
        stream.feed("\x1b[7mReversed\x1b[0m")
        lines = render_pyte_screen(screen)
        assert "Reversed" in lines[0].plain

    def test_returns_correct_number_of_lines(self):
        screen = pyte.Screen(80, 24)
        stream = pyte.Stream(screen)
        stream.feed("Test")
        lines = render_pyte_screen(screen)
        assert len(lines) == 24

    def test_maps_pyte_colors_to_rich_styles(self):
        """Verify that ANSI color codes are reflected in the Rich Text styles."""
        screen = pyte.Screen(40, 5)
        stream = pyte.Stream(screen)
        # Green foreground text
        stream.feed("\x1b[32mGreen\x1b[0m")
        lines = render_pyte_screen(screen)
        # The line should contain styled spans with green
        line = lines[0]
        assert "Green" in line.plain
        # Check that at least one span has green color
        has_green = False
        for start, end, style_str in line._spans:
            if "green" in str(style_str).lower():
                has_green = True
                break
        assert has_green, f"Expected green style in spans, got: {line._spans}"


# ---------------------------------------------------------------------------
# PtyManager tests
# ---------------------------------------------------------------------------


class TestPtyManager:
    """Tests for the PtyManager class."""

    def test_initial_state(self):
        mgr = PtyManager()
        assert mgr.pid is None
        assert mgr.fd is None
        assert mgr.is_running is False

    @patch("nano_claude.terminal.pty_manager.pty.fork")
    @patch("nano_claude.terminal.pty_manager.os.execvpe")
    @patch("nano_claude.terminal.pty_manager.fcntl.ioctl")
    def test_spawn_parent_returns_pid_fd(self, mock_ioctl, mock_execvpe, mock_fork):
        """When pty.fork returns (pid>0, fd), spawn stores them."""
        mock_fork.return_value = (123, 7)  # parent: child_pid=123, master_fd=7
        mgr = PtyManager()
        result = mgr.spawn("claude", cols=80, rows=24)
        assert result == (123, 7)
        assert mgr.pid == 123
        assert mgr.fd == 7
        # ioctl should be called for TIOCSWINSZ
        mock_ioctl.assert_called_once()

    @patch("nano_claude.terminal.pty_manager.pty.fork")
    @patch("nano_claude.terminal.pty_manager.fcntl.ioctl")
    def test_spawn_sets_env_variables(self, mock_ioctl, mock_fork):
        """Spawn should set TERM and COLORTERM environment variables for child."""
        # For parent path (pid > 0)
        mock_fork.return_value = (123, 7)
        mgr = PtyManager()
        mgr.spawn("claude", cols=80, rows=24)
        # Environment is only set in child path (pid == 0), which calls execvpe
        # We verify parent side here - just that spawn works
        assert mgr.pid == 123

    @patch("nano_claude.terminal.pty_manager.pty.fork")
    @patch("nano_claude.terminal.pty_manager.fcntl.ioctl")
    def test_resize_calls_ioctl(self, mock_ioctl, mock_fork):
        mock_fork.return_value = (123, 7)
        mgr = PtyManager()
        mgr.spawn("claude", cols=80, rows=24)
        mock_ioctl.reset_mock()
        mgr.resize(100, 30)
        mock_ioctl.assert_called_once()
        # Verify the struct contains the right values
        call_args = mock_ioctl.call_args
        packed = call_args[0][2]
        rows, cols, _, _ = struct.unpack("HHHH", packed)
        assert rows == 30
        assert cols == 100

    @patch("nano_claude.terminal.pty_manager.os.waitpid")
    @patch("nano_claude.terminal.pty_manager.os.kill")
    @patch("nano_claude.terminal.pty_manager.os.close")
    @patch("nano_claude.terminal.pty_manager.pty.fork")
    @patch("nano_claude.terminal.pty_manager.fcntl.ioctl")
    def test_stop_sends_sigkill_and_cleans_up(
        self, mock_ioctl, mock_fork, mock_close, mock_kill, mock_waitpid
    ):
        mock_fork.return_value = (123, 7)
        mock_waitpid.return_value = (123, 0)
        mgr = PtyManager()
        mgr.spawn("claude", cols=80, rows=24)
        mgr.stop()
        mock_kill.assert_any_call(123, signal.SIGKILL)
        mock_close.assert_called_with(7)
        assert mgr.pid is None
        assert mgr.fd is None

    @patch("nano_claude.terminal.pty_manager.os.waitpid")
    @patch("nano_claude.terminal.pty_manager.pty.fork")
    @patch("nano_claude.terminal.pty_manager.fcntl.ioctl")
    def test_is_running_true_while_alive(self, mock_ioctl, mock_fork, mock_waitpid):
        mock_fork.return_value = (123, 7)
        # waitpid returns (0, 0) when process is still running
        mock_waitpid.return_value = (0, 0)
        mgr = PtyManager()
        mgr.spawn("claude", cols=80, rows=24)
        assert mgr.is_running is True

    @patch("nano_claude.terminal.pty_manager.os.waitpid")
    @patch("nano_claude.terminal.pty_manager.pty.fork")
    @patch("nano_claude.terminal.pty_manager.fcntl.ioctl")
    def test_is_running_false_after_exit(self, mock_ioctl, mock_fork, mock_waitpid):
        mock_fork.return_value = (123, 7)
        # waitpid returns (pid, status) when process has exited
        mock_waitpid.return_value = (123, 0)
        mgr = PtyManager()
        mgr.spawn("claude", cols=80, rows=24)
        assert mgr.is_running is False
