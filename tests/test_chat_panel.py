"""Integration tests for chat panel (graceful degradation, restart)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from nano_claude.config.settings import CLAUDE_EXITED_MESSAGE, CLAUDE_NOT_FOUND_MESSAGE


class TestChatPanelGracefulDegradation:
    """Tests for ChatPanel behavior when claude CLI is not available."""

    @patch("nano_claude.panels.chat.shutil.which", return_value=None)
    def test_claude_not_found_shows_static_message(self, mock_which):
        """When claude is not on PATH, ChatPanel shows install instructions."""
        from nano_claude.panels.chat import ChatPanel

        panel = ChatPanel(id="chat")
        assert panel._claude_available is False

    @patch("nano_claude.panels.chat.shutil.which", return_value="/usr/local/bin/claude")
    def test_claude_found_sets_available(self, mock_which):
        """When claude is on PATH, ChatPanel marks it as available."""
        from nano_claude.panels.chat import ChatPanel

        panel = ChatPanel(id="chat")
        assert panel._claude_available is True


class TestChatPanelMessages:
    """Tests for the configuration message constants."""

    def test_not_found_message_contains_npm_install(self):
        assert "npm install" in CLAUDE_NOT_FOUND_MESSAGE

    def test_not_found_message_contains_claude_code(self):
        assert "Claude Code" in CLAUDE_NOT_FOUND_MESSAGE

    def test_exited_message_contains_restart(self):
        assert "restart" in CLAUDE_EXITED_MESSAGE.lower()

    def test_exited_message_has_exit_code_placeholder(self):
        formatted = CLAUDE_EXITED_MESSAGE.format(exit_code=0)
        assert "0" in formatted

    def test_exited_message_contains_ctrl_shift_r(self):
        assert "Ctrl+Shift+R" in CLAUDE_EXITED_MESSAGE


class TestChatPanelRestartAction:
    """Tests for the action_restart_claude method."""

    @patch("nano_claude.panels.chat.shutil.which", return_value=None)
    def test_restart_action_exists(self, mock_which):
        """ChatPanel has action_restart_claude method."""
        from nano_claude.panels.chat import ChatPanel

        panel = ChatPanel(id="chat")
        assert hasattr(panel, "action_restart_claude")
        assert callable(panel.action_restart_claude)


class TestAppBindings:
    """Tests for app-level Claude restart binding."""

    def test_app_has_restart_binding(self):
        from nano_claude.app import NanoClaudeApp

        binding_keys = [b.key for b in NanoClaudeApp.BINDINGS]
        assert "ctrl+shift+r" in binding_keys

    def test_app_restart_binding_has_correct_id(self):
        from nano_claude.app import NanoClaudeApp

        for b in NanoClaudeApp.BINDINGS:
            if b.key == "ctrl+shift+r":
                assert b.id == "claude.restart"
                break
        else:
            pytest.fail("ctrl+shift+r binding not found")

    def test_app_has_restart_claude_action(self):
        from nano_claude.app import NanoClaudeApp

        assert hasattr(NanoClaudeApp, "action_restart_claude")

    def test_app_has_stop_claude_pty_method(self):
        from nano_claude.app import NanoClaudeApp

        assert hasattr(NanoClaudeApp, "_stop_claude_pty")
