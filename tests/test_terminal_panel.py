"""Tests for terminal panel integration (TERM-01, TERM-02, TERM-03)."""

from __future__ import annotations

import pytest


class TestReservedKeys:
    """TERM-03: RESERVED_KEYS includes terminal panel shortcuts."""

    def test_reserved_keys_contains_ctrl_t(self):
        from nano_claude.terminal.widget import RESERVED_KEYS
        assert "ctrl+t" in RESERVED_KEYS

    def test_reserved_keys_contains_ctrl_n(self):
        from nano_claude.terminal.widget import RESERVED_KEYS
        assert "ctrl+n" in RESERVED_KEYS

    def test_reserved_keys_contains_ctrl_w(self):
        from nano_claude.terminal.widget import RESERVED_KEYS
        assert "ctrl+w" in RESERVED_KEYS

    def test_reserved_keys_minimum_count(self):
        """Ensure no keys were accidentally removed."""
        from nano_claude.terminal.widget import RESERVED_KEYS
        assert len(RESERVED_KEYS) >= 23


class TestAppBindings:
    """TERM-01, TERM-03: App-level terminal bindings."""

    def test_app_has_ctrl_t_binding(self):
        from nano_claude.app import NanoClaudeApp
        keys = [b.key for b in NanoClaudeApp.BINDINGS]
        assert "ctrl+t" in keys

    def test_app_has_ctrl_n_binding(self):
        from nano_claude.app import NanoClaudeApp
        keys = [b.key for b in NanoClaudeApp.BINDINGS]
        assert "ctrl+n" in keys

    def test_app_has_ctrl_w_binding(self):
        from nano_claude.app import NanoClaudeApp
        keys = [b.key for b in NanoClaudeApp.BINDINGS]
        assert "ctrl+w" in keys

    def test_ctrl_t_binding_action(self):
        from nano_claude.app import NanoClaudeApp
        for b in NanoClaudeApp.BINDINGS:
            if b.key == "ctrl+t":
                assert "toggle_terminal" in b.action
                break
        else:
            pytest.fail("ctrl+t binding not found")

    def test_ctrl_t_binding_id(self):
        from nano_claude.app import NanoClaudeApp
        for b in NanoClaudeApp.BINDINGS:
            if b.key == "ctrl+t":
                assert b.id == "terminal.toggle"
                break
        else:
            pytest.fail("ctrl+t binding not found")

    def test_ctrl_n_binding_action(self):
        from nano_claude.app import NanoClaudeApp
        for b in NanoClaudeApp.BINDINGS:
            if b.key == "ctrl+n":
                assert "new_terminal_tab" in b.action
                break
        else:
            pytest.fail("ctrl+n binding not found")

    def test_ctrl_w_binding_action(self):
        from nano_claude.app import NanoClaudeApp
        for b in NanoClaudeApp.BINDINGS:
            if b.key == "ctrl+w":
                assert "close_terminal_tab" in b.action
                break
        else:
            pytest.fail("ctrl+w binding not found")


class TestAppActions:
    """TERM-01, TERM-02: App has terminal action methods."""

    def test_app_has_toggle_terminal_action(self):
        from nano_claude.app import NanoClaudeApp
        assert hasattr(NanoClaudeApp, "action_toggle_terminal")

    def test_app_has_new_terminal_tab_action(self):
        from nano_claude.app import NanoClaudeApp
        assert hasattr(NanoClaudeApp, "action_new_terminal_tab")

    def test_app_has_close_terminal_tab_action(self):
        from nano_claude.app import NanoClaudeApp
        assert hasattr(NanoClaudeApp, "action_close_terminal_tab")

    def test_app_has_focus_terminal_method(self):
        from nano_claude.app import NanoClaudeApp
        assert hasattr(NanoClaudeApp, "_focus_terminal")

    def test_app_has_stop_shell_ptys_method(self):
        from nano_claude.app import NanoClaudeApp
        assert hasattr(NanoClaudeApp, "_stop_shell_ptys")


class TestTerminalPanelWidget:
    """TERM-02: TerminalPanel widget structure."""

    def test_terminal_panel_extends_base_panel(self):
        from nano_claude.panels.base import BasePanel
        from nano_claude.panels.terminal import TerminalPanel
        assert issubclass(TerminalPanel, BasePanel)

    def test_terminal_panel_starts_minimized(self):
        from nano_claude.panels.terminal import TerminalPanel
        panel = TerminalPanel(id="test-terminal")
        assert panel.is_minimized is True

    def test_terminal_panel_has_add_tab(self):
        from nano_claude.panels.terminal import TerminalPanel
        assert hasattr(TerminalPanel, "add_tab")

    def test_terminal_panel_has_close_active_tab(self):
        from nano_claude.panels.terminal import TerminalPanel
        assert hasattr(TerminalPanel, "close_active_tab")

    def test_terminal_panel_has_minimize(self):
        from nano_claude.panels.terminal import TerminalPanel
        assert hasattr(TerminalPanel, "minimize")

    def test_terminal_panel_has_restore(self):
        from nano_claude.panels.terminal import TerminalPanel
        assert hasattr(TerminalPanel, "restore")

    def test_terminal_panel_has_stop_all_ptys(self):
        from nano_claude.panels.terminal import TerminalPanel
        assert hasattr(TerminalPanel, "stop_all_ptys")

    def test_terminal_panel_has_get_active_terminal(self):
        from nano_claude.panels.terminal import TerminalPanel
        assert hasattr(TerminalPanel, "get_active_terminal")


class TestTerminalSettings:
    """TERM-02: Terminal settings constants exist."""

    def test_terminal_panel_height_constant(self):
        from nano_claude.config.settings import TERMINAL_PANEL_HEIGHT
        assert TERMINAL_PANEL_HEIGHT == "30%"

    def test_terminal_max_tabs_constant(self):
        from nano_claude.config.settings import TERMINAL_MAX_TABS
        assert TERMINAL_MAX_TABS == 8

    def test_shell_exited_message_constant(self):
        from nano_claude.config.settings import SHELL_EXITED_MESSAGE
        assert "exit_code" in SHELL_EXITED_MESSAGE
        formatted = SHELL_EXITED_MESSAGE.format(exit_code=0)
        assert "0" in formatted

    def test_terminal_status_idle_constant(self):
        from nano_claude.config.settings import TERMINAL_STATUS_IDLE
        assert "Terminal" in TERMINAL_STATUS_IDLE
        assert "Ctrl+T" in TERMINAL_STATUS_IDLE

    def test_terminal_status_running_constant(self):
        from nano_claude.config.settings import TERMINAL_STATUS_RUNNING
        formatted = TERMINAL_STATUS_RUNNING.format(count=2, s="s")
        assert "2" in formatted
