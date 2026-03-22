"""StatusParser: extracts Claude state and cost from PTY output.

Monitors raw PTY output for patterns indicating Claude's current state
(thinking, tool use, permission prompts) and token/cost summaries.
Posts StatusUpdate and CostUpdate messages for app-level status bar display.
"""

from __future__ import annotations

import re
from enum import Enum, auto

from textual.message import Message


class ClaudeState(Enum):
    """Claude Code CLI operational states."""

    IDLE = auto()
    THINKING = auto()
    TOOL_USE = auto()
    PERMISSION = auto()
    DISCONNECTED = auto()


class StatusUpdate(Message):
    """Posted when Claude's operational state changes."""

    def __init__(self, state: ClaudeState, detail: str = "") -> None:
        super().__init__()
        self.state = state
        self.detail = detail


class CostUpdate(Message):
    """Posted when token/cost information is detected in PTY output."""

    def __init__(self, total_tokens: int = 0, total_cost_usd: float = 0.0) -> None:
        super().__init__()
        self.total_tokens = total_tokens
        self.total_cost_usd = total_cost_usd


# Buffer management constants
_BUFFER_MAX = 4096
_BUFFER_TRIM_TO = 2048


class StatusParser:
    """Parses raw PTY output to extract Claude state and cost information.

    Patterns are checked against each new data chunk (not the full buffer)
    for performance. The buffer is maintained for potential multi-chunk
    pattern matching in the future.
    """

    # Compiled regex patterns (class-level for performance)
    THINKING_PATTERN = re.compile(r"Thinking")
    TOOL_PATTERN = re.compile(
        r"\[(Read|Write|Edit|Bash|Glob|Grep|WebSearch|WebFetch|TodoRead|TodoWrite|Task)\]"
    )
    PERMISSION_PATTERN = re.compile(r"(?:Allow|Deny|Do you want to)")
    COST_PATTERN = re.compile(
        r"(\d+\.?\d*[kK]?)\s*tokens?\s*[*\xb7]\s*\$(\d+\.?\d*)"
    )

    def __init__(self) -> None:
        self._state: ClaudeState = ClaudeState.IDLE
        self._buffer: str = ""
        self._last_cost: CostUpdate = CostUpdate()

    def feed(self, data: str) -> list[Message]:
        """Feed new PTY data and return any detected state/cost messages.

        Checks patterns against the new data chunk for performance.
        Appends data to buffer and trims when buffer exceeds threshold.

        Returns a list of StatusUpdate and/or CostUpdate messages.
        """
        if not data:
            return []

        # Append to buffer
        self._buffer += data

        # Trim buffer if it exceeds max size (keep tail)
        if len(self._buffer) > _BUFFER_MAX:
            self._buffer = self._buffer[-_BUFFER_TRIM_TO:]

        messages: list[Message] = []

        # Check for tool use pattern (most specific, check first)
        tool_match = self.TOOL_PATTERN.search(data)
        if tool_match:
            tool_name = tool_match.group(1)
            self._state = ClaudeState.TOOL_USE
            messages.append(StatusUpdate(ClaudeState.TOOL_USE, detail=tool_name))

        # Check for permission prompt
        elif self.PERMISSION_PATTERN.search(data):
            self._state = ClaudeState.PERMISSION
            messages.append(StatusUpdate(ClaudeState.PERMISSION))

        # Check for thinking state
        elif self.THINKING_PATTERN.search(data):
            self._state = ClaudeState.THINKING
            messages.append(StatusUpdate(ClaudeState.THINKING))

        # Check for cost/token pattern (can appear alongside state patterns)
        cost_match = self.COST_PATTERN.search(data)
        if cost_match:
            tokens = self._parse_token_count(cost_match.group(1))
            cost_usd = float(cost_match.group(2))
            cost_msg = CostUpdate(total_tokens=tokens, total_cost_usd=cost_usd)
            self._last_cost = cost_msg
            messages.append(cost_msg)

        return messages

    def reset(self) -> None:
        """Reset parser state to idle and clear the buffer."""
        self._state = ClaudeState.IDLE
        self._buffer = ""
        self._last_cost = CostUpdate()

    @staticmethod
    def _parse_token_count(s: str) -> int:
        """Parse a token count string, handling 'k'/'K' suffix for thousands.

        Examples:
            "12.3k" -> 12300
            "1.5K"  -> 1500
            "500"   -> 500
            "0.8k"  -> 800
        """
        if s.endswith(("k", "K")):
            return int(float(s[:-1]) * 1000)
        return int(float(s))

    @property
    def current_state(self) -> ClaudeState:
        """Return the current parsed Claude state."""
        return self._state
