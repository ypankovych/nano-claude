# Plan 03-02: Status/Cost Parser + Status Bar — Summary

**Status:** Complete
**Duration:** ~20 min (including bug fixes during checkpoint verification)

## What Was Built

### Task 1: StatusParser + App Integration
- `nano_claude/terminal/status_parser.py` — Parses PTY output for Claude state (thinking, tool use, permission) and cost/token info via regex
- `nano_claude/terminal/widget.py` — Feeds PTY data to StatusParser, bubbles StatusUpdate/CostUpdate messages
- `nano_claude/app.py` — Displays Claude status and cost in header sub_title
- `tests/test_status_parser.py` — 30 unit tests for parsing logic

### Task 2: Visual Verification (Checkpoint)
- Human verification confirmed Claude Code PTY renders correctly
- Several bug fixes applied during verification:
  - PTY quit deadlock: daemon thread + worker cancellation + os._exit fallback with 500ms timer
  - Stray "u" character: filter kitty keyboard protocol sequences before pyte
  - Double cursor: disabled pyte cursor rendering (Claude renders its own)
  - Loading message: "Starting Claude Code..." shown while PTY boots
  - Shutdown banner: full-screen "Shutting down..." modal during exit
  - Terminal restore: stty sane + /dev/tty for clean terminal state after force exit

## Key Files

### Created
- `nano_claude/terminal/status_parser.py`
- `tests/test_status_parser.py`

### Modified
- `nano_claude/terminal/widget.py` — status parser integration, daemon thread, escape sequence filtering
- `nano_claude/terminal/pty_manager.py` — SIGKILL for instant PTY stop
- `nano_claude/panels/chat.py` — loading message, panel title
- `nano_claude/app.py` — status bar, shutdown banner, force exit, worker cancellation
- `nano_claude/styles.tcss` — loading message styles

## Test Results
- 168 tests passing
- 30 new tests for status parser

## Deviations
- Used daemon thread instead of @work(thread=True) for PTY read loop — prevents Textual from blocking on worker join during exit
- Added ShutdownScreen modal + 500ms os._exit fallback — Textual's normal exit path is too slow
- Filter unsupported escape sequences (kitty keyboard, xterm queries) before pyte — Claude Code uses modern terminal features pyte doesn't support
