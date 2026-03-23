---
phase: 03-claude-code-integration
verified: 2026-03-23T12:09:59Z
status: human_needed
score: 8/8 must-haves verified
human_verification:
  - test: "Launch the app with `uv run nano-claude`, focus the chat panel (Ctrl+R), type a prompt, and observe the response"
    expected: "Claude Code CLI starts inside the chat panel, typed characters are forwarded to the PTY, and Claude's response streams with ANSI colors and markdown formatting"
    why_human: "Streaming PTY rendering is a real-time visual behavior that cannot be verified by static code analysis"
  - test: "While Claude is responding, switch focus to the editor panel (Ctrl+E) and observe the header"
    expected: "Header sub_title updates to show 'Claude: thinking...' or 'Claude: using <tool>' even when the chat panel does not have focus"
    why_human: "Status bar visibility from non-chat panels requires a live app interaction to confirm"
  - test: "After a complete response, check the header sub_title for token/cost information"
    expected: "Sub_title shows something like '12.3k tokens / $0.04' after Claude finishes"
    why_human: "Cost display depends on Claude CLI output format matching the COST_PATTERN regex at runtime"
  - test: "Press Ctrl+Q to quit the app"
    expected: "Shutdown banner appears briefly, then the terminal is fully restored with no zombie claude processes"
    why_human: "Clean PTY shutdown and terminal restore (stty sane) requires live verification"
---

# Phase 3: Claude Code Integration Verification Report

**Phase Goal:** User can converse with Claude Code inside the TUI and see its responses streamed in real time with status feedback
**Verified:** 2026-03-23T12:09:59Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                | Status     | Evidence                                                                                                    |
| --- | ---------------------------------------------------------------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------- |
| 1   | User types a prompt in the chat panel and it reaches the Claude CLI PTY                              | VERIFIED   | `widget.py:on_key` translates key events via `translate_key`, writes to PTY fd with `os.write`             |
| 2   | Claude's streaming response renders in the chat panel with ANSI colors and markdown formatting       | VERIFIED   | `widget.py:on_pty_data_received` feeds to `pyte.HistoryScreen`; `render_pyte_screen` converts to Rich Text with bold/color/italic/underline |
| 3   | Claude Code subprocess inherits all features because it IS the real CLI                              | VERIFIED   | `pty_manager.py:spawn` calls `os.execvpe("claude", ...)` with the user's full env (copy of `os.environ`)   |
| 4   | If claude CLI is not installed, the app launches with an informative message                         | VERIFIED   | `chat.py:__init__` checks `shutil.which("claude")`; `compose()` yields `Static(CLAUDE_NOT_FOUND_MESSAGE)` with npm install instructions |
| 5   | If Claude process crashes or exits, user sees the error and can restart with Ctrl+Shift+R             | VERIFIED   | `chat.py:on_pty_exited` mounts `Static(CLAUDE_EXITED_MESSAGE)` with restart hint; `action_restart_claude` in both ChatPanel and App; `ctrl+shift+r` binding with `id="claude.restart"` |
| 6   | Closing the app kills the Claude PTY subprocess cleanly (no zombies)                                 | VERIFIED   | `app.py:_do_final_exit` calls `_stop_claude_pty` before `self.exit()`; `pty_manager.py:stop` sends SIGKILL and closes fd; ShutdownScreen has 500ms os._exit fallback |
| 7   | User sees a status indicator showing Claude's current state in the status bar                        | VERIFIED   | `status_parser.py:StatusParser.feed` detects Thinking/ToolUse/Permission; `app.py:on_status_update` sets `sub_title` via `_update_status_bar`; visible from all panels |
| 8   | User sees token usage and estimated cost in the status bar                                           | VERIFIED   | `status_parser.py:COST_PATTERN` matches token/cost; `app.py:on_cost_update` formats and sets `sub_title` with e.g. "12.3k tokens / $0.04" |

**Score:** 8/8 truths verified (automated checks pass; 4 items need human confirmation of live behavior)

### Required Artifacts

| Artifact                                    | Expected                                          | Status     | Details                                                                     |
| ------------------------------------------- | ------------------------------------------------- | ---------- | --------------------------------------------------------------------------- |
| `nano_claude/terminal/__init__.py`           | Terminal module package init                      | VERIFIED   | Exports TerminalWidget, PtyManager, PtyDataReceived, PtyExited, StatusParser, ClaudeState, StatusUpdate, CostUpdate |
| `nano_claude/terminal/pty_manager.py`        | PTY lifecycle: spawn, read, resize, cleanup       | VERIFIED   | 280 lines; PtyManager class with spawn/stop/resize/is_running; KEY_MAP (26 entries); translate_key; PYTE_COLOR_MAP (17 entries); render_pyte_screen |
| `nano_claude/terminal/widget.py`             | TerminalWidget with pyte, daemon read thread      | VERIFIED   | 228 lines; TerminalWidget(Widget, can_focus=True); pyte.HistoryScreen(history=10000); daemon threading.Thread; RESERVED_KEYS frozenset (16 entries) |
| `nano_claude/terminal/status_parser.py`      | StatusParser for state/cost extraction            | VERIFIED   | 143 lines; ClaudeState enum with 5 values; StatusParser with THINKING/TOOL/PERMISSION/COST patterns; feed/reset/_parse_token_count methods |
| `nano_claude/panels/chat.py`                 | ChatPanel with TerminalWidget, graceful degradation, restart | VERIFIED | 79 lines; shutil.which check; TerminalWidget embed; on_pty_exited; action_restart_claude |
| `tests/test_terminal_widget.py`              | Unit tests for PTY manager and terminal widget    | VERIFIED   | 29 tests — KEY_MAP, translate_key, PYTE_COLOR_MAP, render_pyte_screen, PtyManager; all passing |
| `tests/test_chat_panel.py`                   | Integration tests for chat panel                  | VERIFIED   | 12 tests — graceful degradation, messages, restart action, app bindings; all passing |
| `tests/test_status_parser.py`                | Unit tests for status/cost parsing                | VERIFIED   | 30 tests — ClaudeState enum, feed() state detection, cost parsing, buffer management, reset; all passing |

### Key Link Verification

| From                                    | To                                          | Via                                                     | Status   | Details                                                                                     |
| --------------------------------------- | ------------------------------------------- | ------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------- |
| `nano_claude/terminal/widget.py`        | `nano_claude/terminal/pty_manager.py`        | PtyManager used in TerminalWidget to spawn/read/write   | WIRED    | `widget.py:99` creates `PtyManager()`; `widget.py:117` calls `_pty_manager.spawn()`; `widget.py:190` calls `os.write(_pty_manager.fd, ...)` |
| `nano_claude/panels/chat.py`            | `nano_claude/terminal/widget.py`             | ChatPanel yields TerminalWidget in compose()            | WIRED    | `chat.py:38` yields `TerminalWidget(command="claude", id="claude-terminal")`                |
| `nano_claude/terminal/widget.py`        | `pyte.HistoryScreen`                         | pyte processes PTY output into screen buffer            | WIRED    | `widget.py:112` creates `pyte.HistoryScreen(cols, rows, history=10000)`; `widget.py:159` calls `_stream.feed(cleaned)` |
| `nano_claude/terminal/widget.py`        | `os.write(self._pty_manager.fd, ...)`        | Key events forwarded to PTY file descriptor             | WIRED    | `widget.py:190` `os.write(self._pty_manager.fd, char.encode("utf-8"))`                     |
| `nano_claude/app.py`                    | `nano_claude/panels/chat.py`                 | App kills Claude PTY on quit via action_quit            | WIRED    | `app.py:431` `action_quit` -> `_graceful_exit` -> ShutdownScreen -> `_do_final_exit` -> `_stop_claude_pty` -> `terminal.stop_pty()` |
| `nano_claude/terminal/widget.py`        | `nano_claude/terminal/status_parser.py`      | TerminalWidget feeds PTY data to StatusParser           | WIRED    | `widget.py:162-163` calls `self._status_parser.feed(message.data)` and `self.post_message(msg)` for each result |
| `nano_claude/terminal/status_parser.py` | `nano_claude/app.py`                         | StatusUpdate/CostUpdate messages bubble to app          | WIRED    | `app.py:331` `on_status_update`; `app.py:343` `on_cost_update`; both call `_update_status_bar` which sets `self.sub_title` |

### Requirements Coverage

| Requirement | Source Plan | Description                                                                                        | Status      | Evidence                                                                                                     |
| ----------- | ----------- | -------------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------ |
| CLAUDE-01   | 03-01-PLAN  | User can type prompts and receive streaming responses from the actual Claude Code CLI subprocess   | SATISFIED   | TerminalWidget forwards keys via os.write to PTY fd; daemon thread reads output and feeds pyte for display    |
| CLAUDE-02   | 03-01-PLAN  | Claude Code subprocess inherits all features without reimplementation                              | SATISFIED   | `spawn()` uses `os.execvpe("claude", ["claude"], env)` where env is a copy of `os.environ` — full inheritance |
| CLAUDE-03   | 03-01-PLAN  | User sees responses with markdown formatting and syntax-highlighted code blocks                    | SATISFIED   | pyte.HistoryScreen processes ANSI escapes; render_pyte_screen maps colors/bold/italic to Rich Text styles    |
| CLAUDE-04   | 03-02-PLAN  | User sees a status indicator showing Claude's current state                                        | SATISFIED   | StatusParser detects THINKING/TOOL_USE/PERMISSION from PTY output; app `on_status_update` sets sub_title     |
| CLAUDE-05   | 03-02-PLAN  | User sees token usage and estimated cost for the current session in the status bar                 | SATISFIED   | COST_PATTERN regex matches "Nk tokens * $N.NN"; `on_cost_update` formats and sets sub_title                  |

**Note on REQUIREMENTS.md discrepancy:** CLAUDE-04 and CLAUDE-05 are marked `[ ]` (Pending) in `.planning/REQUIREMENTS.md` but the implementation is fully present and tested in the codebase. The requirement tracker was not updated when Plan 03-02 completed. The code satisfies both requirements; the tracker checkbox is a documentation artifact, not a gap.

### Anti-Patterns Found

None. No TODO/FIXME/placeholder/stub patterns found in any of the 5 key implementation files. The `return []` in `status_parser.py:81` is legitimate (returns empty list when no patterns match — correct behavior, tested in `test_plain_text_returns_empty_list`).

### Human Verification Required

#### 1. Streaming Response Rendering

**Test:** Launch `uv run nano-claude`, focus the chat panel with Ctrl+R, type a short prompt such as "hello", and press Enter.
**Expected:** Characters appear in the PTY as they are typed, then Claude's response streams token-by-token with ANSI colors and markdown formatting visible.
**Why human:** Streaming PTY rendering is a real-time visual behavior that cannot be verified by static code analysis. The pyte pipeline is wired correctly but only runtime execution confirms the rendered output is correct.

#### 2. Status Bar Visibility from Non-Chat Panels

**Test:** While Claude is actively responding to a prompt, press Ctrl+E to focus the editor panel and look at the header area.
**Expected:** The header sub_title shows "Claude: thinking..." or "Claude: using Read" (or similar) even though the chat panel no longer has focus.
**Why human:** The sub_title update path is wired (StatusUpdate -> on_status_update -> _update_status_bar -> self.sub_title) but confirming it is actually visible in the Textual Header widget from all panel focus states requires live verification.

#### 3. Cost Display After Response

**Test:** After Claude completes a response, observe the header sub_title.
**Expected:** Sub_title shows token count and cost, e.g. "1.2k tokens / $0.01".
**Why human:** The COST_PATTERN regex must match the exact format Claude CLI prints. If Claude's output format changed since the regex was written, cost display will silently fail. Only a live run confirms the regex matches real output.

#### 4. Clean Quit and Terminal Restore

**Test:** Press Ctrl+Q to quit the application.
**Expected:** The shutdown banner ("Shutting down...") briefly appears, then the terminal is fully restored to normal state (cursor visible, no color artifacts, no stray claude processes).
**Why human:** The os._exit(0) fallback and `stty sane` terminal restore sequence require live execution to confirm no zombie processes remain and the terminal is in a clean state.

### Gaps Summary

No gaps found. All 8 truths are verified at the code level — files exist, are substantive (not stubs), and are properly wired. All 71 tests (29 terminal, 12 chat panel, 30 status parser) pass. The 4 human verification items are not gaps; they are confirmations of correct live behavior that automated checks cannot substitute for.

The REQUIREMENTS.md checkbox discrepancy for CLAUDE-04 and CLAUDE-05 (showing `[ ]` while the implementation is complete) is a tracker update oversight, not a code gap.

---

_Verified: 2026-03-23T12:09:59Z_
_Verifier: Claude (gsd-verifier)_
