"""Tests for Code-to-Claude interaction: CodeContext, PTY write, editor selection."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nano_claude.models.code_context import (
    BRACKETED_PASTE_END,
    BRACKETED_PASTE_START,
    MAX_SELECTION_BYTES,
    MAX_SELECTION_LINES,
    CodeContext,
    truncate_selection,
    write_to_pty_bracketed,
)


class TestCodeContextFormatting:
    """Tests for CodeContext.format_code_fence."""

    def test_format_code_fence_with_language(self, tmp_path: Path) -> None:
        ctx = CodeContext(
            file_path=tmp_path / "src" / "main.py",
            start_line=5,
            end_line=10,
            text="def hello():\n    pass",
            language="python",
        )
        result = ctx.format_code_fence(tmp_path)
        assert result == "```python\n# src/main.py lines 5-10\ndef hello():\n    pass\n```\n"

    def test_format_code_fence_without_language(self, tmp_path: Path) -> None:
        ctx = CodeContext(
            file_path=tmp_path / "data.txt",
            start_line=1,
            end_line=1,
            text="hello world",
            language=None,
        )
        result = ctx.format_code_fence(tmp_path)
        assert result == "```\n# data.txt lines 1-1\nhello world\n```\n"

    def test_format_code_fence_outside_cwd(self, tmp_path: Path) -> None:
        """When file is outside cwd, fall back to filename only."""
        ctx = CodeContext(
            file_path=Path("/some/other/project/main.rs"),
            start_line=42,
            end_line=58,
            text="fn main() {}",
            language="rust",
        )
        result = ctx.format_code_fence(tmp_path)
        assert result == "```rust\n# main.rs lines 42-58\nfn main() {}\n```\n"


class TestTruncateSelection:
    """Tests for truncate_selection."""

    def test_within_limits(self) -> None:
        text = "line1\nline2\nline3"
        result, truncated = truncate_selection(text)
        assert result == text
        assert truncated is False

    def test_exceeding_max_lines(self) -> None:
        lines = [f"line {i}" for i in range(300)]
        text = "\n".join(lines)
        result, truncated = truncate_selection(text)
        assert truncated is True
        assert result.endswith("... (truncated)")
        # Should have at most MAX_SELECTION_LINES lines before the truncation marker
        result_lines = result.split("\n")
        # The last line is "... (truncated)", so lines before it are <= MAX_SELECTION_LINES
        assert len(result_lines) <= MAX_SELECTION_LINES + 1

    def test_exceeding_max_bytes(self) -> None:
        # Each line is about 100 bytes, 100 lines = ~10KB > 8192
        lines = ["x" * 100 for _ in range(100)]
        text = "\n".join(lines)
        result, truncated = truncate_selection(text)
        assert truncated is True
        assert result.endswith("... (truncated)")
        assert len(result.encode("utf-8")) <= MAX_SELECTION_BYTES + len("\n... (truncated)".encode("utf-8"))


class TestWriteToPtyBracketed:
    """Tests for write_to_pty_bracketed."""

    def test_wraps_in_bracketed_paste(self) -> None:
        written_data = bytearray()

        def fake_write(fd, data):
            written_data.extend(data)
            return len(data)

        with patch("nano_claude.models.code_context.os.write", side_effect=fake_write):
            write_to_pty_bracketed(42, "hello world")

        decoded = written_data.decode("utf-8")
        assert decoded.startswith(BRACKETED_PASTE_START)
        assert decoded.endswith(BRACKETED_PASTE_END)
        assert "hello world" in decoded

    def test_chunked_writes(self) -> None:
        """Large data should be written in chunks of 4096 bytes."""
        write_sizes = []

        def fake_write(fd, data):
            write_sizes.append(len(data))
            return len(data)

        large_text = "x" * 10000  # Much larger than 4096

        with patch("nano_claude.models.code_context.os.write", side_effect=fake_write):
            write_to_pty_bracketed(42, large_text)

        # All chunks except possibly the last should be <= 4096
        for size in write_sizes[:-1]:
            assert size <= 4096
        assert sum(write_sizes) > 10000  # Total data written includes brackets


class TestConstants:
    """Tests for module-level constants."""

    def test_bracketed_paste_start(self) -> None:
        assert BRACKETED_PASTE_START == "\x1b[200~"

    def test_bracketed_paste_end(self) -> None:
        assert BRACKETED_PASTE_END == "\x1b[201~"

    def test_max_selection_lines(self) -> None:
        assert MAX_SELECTION_LINES == 200

    def test_max_selection_bytes(self) -> None:
        assert MAX_SELECTION_BYTES == 8192


class TestReservedKeys:
    """Tests for RESERVED_KEYS containing ctrl+l and ctrl+p."""

    def test_ctrl_l_is_reserved(self) -> None:
        from nano_claude.terminal.widget import RESERVED_KEYS

        assert "ctrl+l" in RESERVED_KEYS

    def test_ctrl_p_is_reserved(self) -> None:
        from nano_claude.terminal.widget import RESERVED_KEYS

        assert "ctrl+p" in RESERVED_KEYS


class TestPinContext:
    """Tests for pin/unpin toggle on NanoClaudeApp."""

    def test_pin_stores_context(self, tmp_path: Path) -> None:
        """Verify that a CodeContext can be stored as _pinned_context."""
        from nano_claude.app import NanoClaudeApp

        app = NanoClaudeApp.__new__(NanoClaudeApp)
        app._pinned_context = None  # Initialize

        ctx = CodeContext(
            file_path=tmp_path / "main.py",
            start_line=10,
            end_line=20,
            text="some code",
            language="python",
        )
        app._pinned_context = ctx
        assert app._pinned_context is ctx
        assert app._pinned_context.start_line == 10
        assert app._pinned_context.end_line == 20

    def test_unpin_clears_context(self, tmp_path: Path) -> None:
        """Setting _pinned_context to None clears the pin."""
        from nano_claude.app import NanoClaudeApp

        app = NanoClaudeApp.__new__(NanoClaudeApp)
        ctx = CodeContext(
            file_path=tmp_path / "main.py",
            start_line=1,
            end_line=5,
            text="code",
            language="python",
        )
        app._pinned_context = ctx
        assert app._pinned_context is not None

        app._pinned_context = None
        assert app._pinned_context is None

    def test_ctrl_p_is_reserved(self) -> None:
        from nano_claude.terminal.widget import RESERVED_KEYS

        assert "ctrl+p" in RESERVED_KEYS

    def test_pin_context_binding_exists(self) -> None:
        """Verify Ctrl+P binding is registered on NanoClaudeApp."""
        from nano_claude.app import NanoClaudeApp

        binding_keys = [b.key for b in NanoClaudeApp.BINDINGS]
        assert "ctrl+p" in binding_keys

    def test_action_pin_context_exists(self) -> None:
        """Verify action_pin_context method exists."""
        from nano_claude.app import NanoClaudeApp

        assert hasattr(NanoClaudeApp, "action_pin_context")
        assert callable(getattr(NanoClaudeApp, "action_pin_context"))


class TestGetPinnedContextText:
    """Tests for _get_pinned_context_text helper."""

    def test_returns_none_when_not_pinned(self) -> None:
        """_get_pinned_context_text returns None when nothing is pinned."""
        from nano_claude.app import NanoClaudeApp

        app = NanoClaudeApp.__new__(NanoClaudeApp)
        app._pinned_context = None
        result = app._get_pinned_context_text()
        assert result is None

    def test_returns_formatted_fence_when_pinned(self, tmp_path: Path) -> None:
        """_get_pinned_context_text returns code fence string when context is pinned."""
        from nano_claude.app import NanoClaudeApp

        app = NanoClaudeApp.__new__(NanoClaudeApp)
        ctx = CodeContext(
            file_path=tmp_path / "src" / "utils.py",
            start_line=5,
            end_line=15,
            text="def helper():\n    return 42",
            language="python",
        )
        app._pinned_context = ctx

        with patch("nano_claude.app.Path.cwd", return_value=tmp_path):
            result = app._get_pinned_context_text()

        assert result is not None
        assert "```python" in result
        assert "src/utils.py lines 5-15" in result
        assert "def helper():" in result


class TestAmbientContextInjection:
    """Tests for Enter key interception with ambient context injection."""

    def test_enter_with_pinned_context_prepends_to_prompt(self) -> None:
        """Enter with pinned context clears input, writes context+user text, submits."""
        from nano_claude.terminal.status_parser import ClaudeState
        from nano_claude.terminal.widget import TerminalWidget

        widget = TerminalWidget.__new__(TerminalWidget)
        widget._running = True
        widget._pty_manager = MagicMock()
        widget._pty_manager.fd = 42
        widget._status_parser = MagicMock()
        widget._status_parser.current_state = ClaudeState.IDLE
        widget._scroll_lines = 0
        widget._input_buffer = "fix this bug"
        widget._scroll_lines = 0
        widget._get_pinned_context = MagicMock(
            return_value="```py\n# f.py lines 1-5\ncode\n```\n"
        )

        writes = []

        def fake_write(fd, data):
            writes.append(data)
            return len(data)

        event = MagicMock()
        event.key = "enter"
        event.character = None

        with patch("nano_claude.terminal.widget.os.write", side_effect=fake_write):
            with patch("nano_claude.terminal.widget.write_to_pty_bracketed") as mock_bracketed:
                widget.on_key(event)
                # Ctrl+U sent to clear input
                assert b"\x15" in writes
                # Context + user text written via bracketed paste
                mock_bracketed.assert_called_once_with(
                    42, "```py\n# f.py lines 1-5\ncode\n```\n\n\nfix this bug"
                )
                # Enter sent to submit
                assert b"\r" in writes
        # Buffer cleared after submission
        assert widget._input_buffer == ""
        event.prevent_default.assert_called()

    def test_enter_without_pinned_context_no_injection(self) -> None:
        """Enter key without pinned context should not inject anything."""
        from nano_claude.terminal.widget import TerminalWidget

        widget = TerminalWidget.__new__(TerminalWidget)
        widget._running = True
        widget._pty_manager = MagicMock()
        widget._pty_manager.fd = 42
        widget._status_parser = MagicMock()
        widget._get_pinned_context = None
        widget._scroll_lines = 0
        widget._input_buffer = "hello"

        event = MagicMock()
        event.key = "enter"
        event.character = None

        with patch("nano_claude.terminal.widget.write_to_pty_bracketed") as mock_bracketed:
            with patch("nano_claude.terminal.widget.translate_key", return_value="\r"):
                with patch("nano_claude.terminal.widget.os.write", return_value=1):
                    widget.on_key(event)
            mock_bracketed.assert_not_called()
        # Buffer should be cleared on normal Enter
        assert widget._input_buffer == ""

    def test_enter_with_empty_buffer_no_injection(self) -> None:
        """Enter with pinned context but empty buffer should not inject."""
        from nano_claude.terminal.status_parser import ClaudeState
        from nano_claude.terminal.widget import TerminalWidget

        widget = TerminalWidget.__new__(TerminalWidget)
        widget._running = True
        widget._pty_manager = MagicMock()
        widget._pty_manager.fd = 42
        widget._status_parser = MagicMock()
        widget._status_parser.current_state = ClaudeState.IDLE
        widget._scroll_lines = 0
        widget._input_buffer = ""
        widget._get_pinned_context = MagicMock(return_value="context")

        event = MagicMock()
        event.key = "enter"
        event.character = None

        with patch("nano_claude.terminal.widget.write_to_pty_bracketed") as mock_bracketed:
            with patch("nano_claude.terminal.widget.translate_key", return_value="\r"):
                with patch("nano_claude.terminal.widget.os.write", return_value=1):
                    widget.on_key(event)
            mock_bracketed.assert_not_called()

    def test_enter_with_context_but_not_idle_no_injection(self) -> None:
        """Enter key when Claude is not IDLE should not inject context."""
        from nano_claude.terminal.status_parser import ClaudeState
        from nano_claude.terminal.widget import TerminalWidget

        widget = TerminalWidget.__new__(TerminalWidget)
        widget._running = True
        widget._pty_manager = MagicMock()
        widget._pty_manager.fd = 42
        widget._status_parser = MagicMock()
        widget._status_parser.current_state = ClaudeState.THINKING
        widget._scroll_lines = 0
        widget._input_buffer = "hello"
        widget._get_pinned_context = MagicMock(return_value="context")

        event = MagicMock()
        event.key = "enter"
        event.character = None

        with patch("nano_claude.terminal.widget.write_to_pty_bracketed") as mock_bracketed:
            with patch("nano_claude.terminal.widget.translate_key", return_value="\r"):
                with patch("nano_claude.terminal.widget.os.write", return_value=1):
                    widget.on_key(event)
            mock_bracketed.assert_not_called()

    def test_input_buffer_tracks_keystrokes(self) -> None:
        """Input buffer tracks typed characters and handles backspace."""
        from nano_claude.terminal.widget import TerminalWidget

        widget = TerminalWidget.__new__(TerminalWidget)
        widget._running = True
        widget._pty_manager = MagicMock()
        widget._pty_manager.fd = 42
        widget._status_parser = MagicMock()
        widget._get_pinned_context = None
        widget._scroll_lines = 0
        widget._input_buffer = ""

        with patch("nano_claude.terminal.widget.translate_key", return_value="x"):
            with patch("nano_claude.terminal.widget.os.write", return_value=1):
                # Type 'h'
                ev = MagicMock()
                ev.key = "h"
                ev.character = "h"
                widget.on_key(ev)
                assert widget._input_buffer == "h"

                # Type 'i'
                ev2 = MagicMock()
                ev2.key = "i"
                ev2.character = "i"
                widget.on_key(ev2)
                assert widget._input_buffer == "hi"

                # Backspace
                ev3 = MagicMock()
                ev3.key = "backspace"
                ev3.character = None
                widget.on_key(ev3)
                assert widget._input_buffer == "h"


class TestContextInjectionGuard:
    """Tests for state guard preventing injection in non-IDLE states."""

    def test_idle_state_allows_injection(self) -> None:
        """ClaudeState.IDLE allows context injection when buffer has content."""
        from nano_claude.terminal.status_parser import ClaudeState
        from nano_claude.terminal.widget import TerminalWidget

        widget = TerminalWidget.__new__(TerminalWidget)
        widget._running = True
        widget._pty_manager = MagicMock()
        widget._pty_manager.fd = 42
        widget._status_parser = MagicMock()
        widget._status_parser.current_state = ClaudeState.IDLE
        widget._scroll_lines = 0
        widget._input_buffer = "test prompt"
        widget._get_pinned_context = MagicMock(return_value="context")

        event = MagicMock()
        event.key = "enter"
        event.character = None

        with patch("nano_claude.terminal.widget.write_to_pty_bracketed") as mock_bracketed:
            with patch("nano_claude.terminal.widget.os.write", return_value=1):
                widget.on_key(event)
            mock_bracketed.assert_called_once()

    def test_thinking_state_blocks_injection(self) -> None:
        from nano_claude.terminal.status_parser import ClaudeState
        from nano_claude.terminal.widget import TerminalWidget

        widget = TerminalWidget.__new__(TerminalWidget)
        widget._running = True
        widget._pty_manager = MagicMock()
        widget._pty_manager.fd = 42
        widget._status_parser = MagicMock()
        widget._status_parser.current_state = ClaudeState.THINKING
        widget._scroll_lines = 0
        widget._input_buffer = "test"
        widget._get_pinned_context = MagicMock(return_value="context")

        event = MagicMock()
        event.key = "enter"
        event.character = None

        with patch("nano_claude.terminal.widget.write_to_pty_bracketed") as mock_bracketed:
            with patch("nano_claude.terminal.widget.translate_key", return_value="\r"):
                with patch("nano_claude.terminal.widget.os.write", return_value=1):
                    widget.on_key(event)
            mock_bracketed.assert_not_called()

    def test_tool_use_state_blocks_injection(self) -> None:
        from nano_claude.terminal.status_parser import ClaudeState
        from nano_claude.terminal.widget import TerminalWidget

        widget = TerminalWidget.__new__(TerminalWidget)
        widget._running = True
        widget._pty_manager = MagicMock()
        widget._pty_manager.fd = 42
        widget._status_parser = MagicMock()
        widget._status_parser.current_state = ClaudeState.TOOL_USE
        widget._scroll_lines = 0
        widget._input_buffer = "test"
        widget._get_pinned_context = MagicMock(return_value="context")

        event = MagicMock()
        event.key = "enter"
        event.character = None

        with patch("nano_claude.terminal.widget.write_to_pty_bracketed") as mock_bracketed:
            with patch("nano_claude.terminal.widget.translate_key", return_value="\r"):
                with patch("nano_claude.terminal.widget.os.write", return_value=1):
                    widget.on_key(event)
            mock_bracketed.assert_not_called()

    def test_permission_state_blocks_injection(self) -> None:
        from nano_claude.terminal.status_parser import ClaudeState
        from nano_claude.terminal.widget import TerminalWidget

        widget = TerminalWidget.__new__(TerminalWidget)
        widget._running = True
        widget._pty_manager = MagicMock()
        widget._pty_manager.fd = 42
        widget._status_parser = MagicMock()
        widget._status_parser.current_state = ClaudeState.PERMISSION
        widget._scroll_lines = 0
        widget._input_buffer = "test"
        widget._get_pinned_context = MagicMock(return_value="context")

        event = MagicMock()
        event.key = "enter"
        event.character = None

        with patch("nano_claude.terminal.widget.write_to_pty_bracketed") as mock_bracketed:
            with patch("nano_claude.terminal.widget.translate_key", return_value="\r"):
                with patch("nano_claude.terminal.widget.os.write", return_value=1):
                    widget.on_key(event)
            mock_bracketed.assert_not_called()
