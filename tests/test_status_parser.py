"""Unit tests for StatusParser -- extracts Claude state and cost from PTY output."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# ClaudeState enum tests
# ---------------------------------------------------------------------------


class TestClaudeState:
    """Tests for the ClaudeState enum."""

    def test_has_idle(self):
        from nano_claude.terminal.status_parser import ClaudeState

        assert hasattr(ClaudeState, "IDLE")

    def test_has_thinking(self):
        from nano_claude.terminal.status_parser import ClaudeState

        assert hasattr(ClaudeState, "THINKING")

    def test_has_tool_use(self):
        from nano_claude.terminal.status_parser import ClaudeState

        assert hasattr(ClaudeState, "TOOL_USE")

    def test_has_permission(self):
        from nano_claude.terminal.status_parser import ClaudeState

        assert hasattr(ClaudeState, "PERMISSION")

    def test_has_disconnected(self):
        from nano_claude.terminal.status_parser import ClaudeState

        assert hasattr(ClaudeState, "DISCONNECTED")


# ---------------------------------------------------------------------------
# StatusParser.feed() tests -- state detection
# ---------------------------------------------------------------------------


class TestStatusParserFeedState:
    """Tests for StatusParser.feed() state detection."""

    def test_thinking_returns_status_update(self):
        from nano_claude.terminal.status_parser import ClaudeState, StatusParser, StatusUpdate

        parser = StatusParser()
        messages = parser.feed("Thinking")
        status_msgs = [m for m in messages if isinstance(m, StatusUpdate)]
        assert len(status_msgs) >= 1
        assert status_msgs[0].state == ClaudeState.THINKING

    def test_tool_read_returns_tool_use(self):
        from nano_claude.terminal.status_parser import ClaudeState, StatusParser, StatusUpdate

        parser = StatusParser()
        messages = parser.feed("[Read]")
        status_msgs = [m for m in messages if isinstance(m, StatusUpdate)]
        assert len(status_msgs) >= 1
        assert status_msgs[0].state == ClaudeState.TOOL_USE
        assert status_msgs[0].detail == "Read"

    def test_tool_write_returns_tool_use(self):
        from nano_claude.terminal.status_parser import ClaudeState, StatusParser, StatusUpdate

        parser = StatusParser()
        messages = parser.feed("[Write]")
        status_msgs = [m for m in messages if isinstance(m, StatusUpdate)]
        assert len(status_msgs) >= 1
        assert status_msgs[0].state == ClaudeState.TOOL_USE
        assert status_msgs[0].detail == "Write"

    def test_tool_edit_returns_tool_use(self):
        from nano_claude.terminal.status_parser import ClaudeState, StatusParser, StatusUpdate

        parser = StatusParser()
        messages = parser.feed("[Edit]")
        status_msgs = [m for m in messages if isinstance(m, StatusUpdate)]
        assert len(status_msgs) >= 1
        assert status_msgs[0].state == ClaudeState.TOOL_USE
        assert status_msgs[0].detail == "Edit"

    def test_tool_bash_returns_tool_use(self):
        from nano_claude.terminal.status_parser import ClaudeState, StatusParser, StatusUpdate

        parser = StatusParser()
        messages = parser.feed("[Bash]")
        status_msgs = [m for m in messages if isinstance(m, StatusUpdate)]
        assert len(status_msgs) >= 1
        assert status_msgs[0].state == ClaudeState.TOOL_USE
        assert status_msgs[0].detail == "Bash"

    def test_tool_glob_returns_tool_use(self):
        from nano_claude.terminal.status_parser import ClaudeState, StatusParser, StatusUpdate

        parser = StatusParser()
        messages = parser.feed("[Glob]")
        status_msgs = [m for m in messages if isinstance(m, StatusUpdate)]
        assert len(status_msgs) >= 1
        assert status_msgs[0].state == ClaudeState.TOOL_USE
        assert status_msgs[0].detail == "Glob"

    def test_tool_grep_returns_tool_use(self):
        from nano_claude.terminal.status_parser import ClaudeState, StatusParser, StatusUpdate

        parser = StatusParser()
        messages = parser.feed("[Grep]")
        status_msgs = [m for m in messages if isinstance(m, StatusUpdate)]
        assert len(status_msgs) >= 1
        assert status_msgs[0].state == ClaudeState.TOOL_USE
        assert status_msgs[0].detail == "Grep"

    def test_tool_webfetch_returns_tool_use(self):
        from nano_claude.terminal.status_parser import ClaudeState, StatusParser, StatusUpdate

        parser = StatusParser()
        messages = parser.feed("[WebFetch]")
        status_msgs = [m for m in messages if isinstance(m, StatusUpdate)]
        assert len(status_msgs) >= 1
        assert status_msgs[0].state == ClaudeState.TOOL_USE
        assert status_msgs[0].detail == "WebFetch"

    def test_permission_prompt_returns_permission(self):
        from nano_claude.terminal.status_parser import ClaudeState, StatusParser, StatusUpdate

        parser = StatusParser()
        messages = parser.feed("Allow this action? Allow / Deny")
        status_msgs = [m for m in messages if isinstance(m, StatusUpdate)]
        assert len(status_msgs) >= 1
        assert status_msgs[0].state == ClaudeState.PERMISSION

    def test_do_you_want_permission_prompt(self):
        from nano_claude.terminal.status_parser import ClaudeState, StatusParser, StatusUpdate

        parser = StatusParser()
        messages = parser.feed("Do you want to allow this?")
        status_msgs = [m for m in messages if isinstance(m, StatusUpdate)]
        assert len(status_msgs) >= 1
        assert status_msgs[0].state == ClaudeState.PERMISSION

    def test_plain_text_returns_empty_list(self):
        from nano_claude.terminal.status_parser import StatusParser

        parser = StatusParser()
        messages = parser.feed("Hello world, just some text")
        assert messages == []

    def test_empty_string_returns_empty_list(self):
        from nano_claude.terminal.status_parser import StatusParser

        parser = StatusParser()
        messages = parser.feed("")
        assert messages == []


# ---------------------------------------------------------------------------
# StatusParser.feed() tests -- cost detection
# ---------------------------------------------------------------------------


class TestStatusParserFeedCost:
    """Tests for StatusParser.feed() cost detection."""

    def test_k_suffix_tokens_returns_cost_update(self):
        from nano_claude.terminal.status_parser import CostUpdate, StatusParser

        parser = StatusParser()
        messages = parser.feed("12.3k tokens * $0.04")
        cost_msgs = [m for m in messages if isinstance(m, CostUpdate)]
        assert len(cost_msgs) >= 1
        assert cost_msgs[0].total_tokens == 12300
        assert cost_msgs[0].total_cost_usd == pytest.approx(0.04)

    def test_plain_tokens_returns_cost_update(self):
        from nano_claude.terminal.status_parser import CostUpdate, StatusParser

        parser = StatusParser()
        messages = parser.feed("500 tokens * $0.01")
        cost_msgs = [m for m in messages if isinstance(m, CostUpdate)]
        assert len(cost_msgs) >= 1
        assert cost_msgs[0].total_tokens == 500
        assert cost_msgs[0].total_cost_usd == pytest.approx(0.01)

    def test_middle_dot_separator(self):
        """Cost pattern with middle dot (Unicode bullet) separator."""
        from nano_claude.terminal.status_parser import CostUpdate, StatusParser

        parser = StatusParser()
        messages = parser.feed("12.3k tokens \u00b7 $0.04")
        cost_msgs = [m for m in messages if isinstance(m, CostUpdate)]
        assert len(cost_msgs) >= 1
        assert cost_msgs[0].total_tokens == 12300

    def test_multiple_patterns_in_one_feed(self):
        """Feed with both tool use and cost should return multiple messages."""
        from nano_claude.terminal.status_parser import CostUpdate, StatusParser, StatusUpdate

        parser = StatusParser()
        messages = parser.feed("[Read] some output 500 tokens * $0.01")
        status_msgs = [m for m in messages if isinstance(m, StatusUpdate)]
        cost_msgs = [m for m in messages if isinstance(m, CostUpdate)]
        assert len(status_msgs) >= 1
        assert len(cost_msgs) >= 1


# ---------------------------------------------------------------------------
# StatusParser._parse_token_count tests
# ---------------------------------------------------------------------------


class TestParseTokenCount:
    """Tests for StatusParser._parse_token_count static method."""

    def test_k_suffix_lowercase(self):
        from nano_claude.terminal.status_parser import StatusParser

        assert StatusParser._parse_token_count("12.3k") == 12300

    def test_k_suffix_uppercase(self):
        from nano_claude.terminal.status_parser import StatusParser

        assert StatusParser._parse_token_count("1.5K") == 1500

    def test_plain_integer(self):
        from nano_claude.terminal.status_parser import StatusParser

        assert StatusParser._parse_token_count("500") == 500

    def test_small_k_value(self):
        from nano_claude.terminal.status_parser import StatusParser

        assert StatusParser._parse_token_count("0.8k") == 800


# ---------------------------------------------------------------------------
# StatusParser buffer management tests
# ---------------------------------------------------------------------------


class TestStatusParserBuffer:
    """Tests for StatusParser buffer trimming."""

    def test_buffer_trims_when_exceeding_4096(self):
        from nano_claude.terminal.status_parser import StatusParser

        parser = StatusParser()
        # Feed 5000 chars total
        parser.feed("x" * 5000)
        assert len(parser._buffer) <= 4096

    def test_buffer_keeps_tail_after_trim(self):
        from nano_claude.terminal.status_parser import StatusParser

        parser = StatusParser()
        # Feed data that exceeds 4096 -- buffer should keep tail (last 2048 chars)
        parser.feed("A" * 3000)
        parser.feed("B" * 2000)  # total 5000, triggers trim
        # After trim, buffer should be 2048 chars from the tail
        assert len(parser._buffer) <= 4096
        # Buffer should contain the most recent chars (Bs)
        assert "B" in parser._buffer


# ---------------------------------------------------------------------------
# StatusParser.reset() tests
# ---------------------------------------------------------------------------


class TestStatusParserReset:
    """Tests for StatusParser.reset() method."""

    def test_reset_clears_state_to_idle(self):
        from nano_claude.terminal.status_parser import ClaudeState, StatusParser

        parser = StatusParser()
        parser.feed("Thinking")
        parser.reset()
        assert parser.current_state == ClaudeState.IDLE

    def test_reset_clears_buffer(self):
        from nano_claude.terminal.status_parser import StatusParser

        parser = StatusParser()
        parser.feed("some data here")
        parser.reset()
        assert parser._buffer == ""


# ---------------------------------------------------------------------------
# StatusParser.current_state property tests
# ---------------------------------------------------------------------------


class TestStatusParserCurrentState:
    """Tests for StatusParser.current_state property."""

    def test_initial_state_is_idle(self):
        from nano_claude.terminal.status_parser import ClaudeState, StatusParser

        parser = StatusParser()
        assert parser.current_state == ClaudeState.IDLE
