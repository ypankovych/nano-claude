---
phase: 03-claude-code-integration
plan: 01
subsystem: terminal
tags: [pyte, pty, terminal-emulation, ansi, rich, textual-widget]

# Dependency graph
requires:
  - phase: 02-panel-features
    provides: "BasePanel, EditorPanel, FileTreePanel, app layout, settings module"
provides:
  - "nano_claude/terminal/ module with PTY lifecycle management"
  - "TerminalWidget: pyte-backed Textual widget with threaded PTY I/O"
  - "PtyManager: spawn/stop/resize/is_running for PTY subprocess"
  - "ChatPanel with embedded Claude CLI or graceful degradation"
  - "Ctrl+Shift+R restart binding for Claude subprocess"
  - "Clean PTY shutdown on app quit (no zombie processes)"
affects: [03-02, 04-auto-jump-cursor, 05-interaction-refinements, 06-terminal-panel]

# Tech tracking
tech-stack:
  added: [pyte, wcwidth]
  patterns: [pty.fork for subprocess, pyte.HistoryScreen for terminal emulation, threaded PTY read with @work(thread=True), RESERVED_KEYS frozenset for key passthrough]

key-files:
  created:
    - nano_claude/terminal/__init__.py
    - nano_claude/terminal/pty_manager.py
    - nano_claude/terminal/widget.py
    - tests/test_terminal_widget.py
    - tests/test_chat_panel.py
  modified:
    - nano_claude/panels/chat.py
    - nano_claude/app.py
    - nano_claude/config/settings.py
    - nano_claude/styles.tcss
    - pyproject.toml
    - uv.lock

key-decisions:
  - "Used stdlib pty.fork() instead of ptyprocess (avoids extra dependency, per research open question 4)"
  - "pyte.HistoryScreen with history=10000 for scrollback (per research open question 5)"
  - "RESERVED_KEYS frozenset excludes 17 app-level bindings from PTY capture"
  - "Threaded read loop with @work(thread=True, exclusive=True) for PTY I/O"
  - "Extracted _stop_claude_pty helper for DRY cleanup in action_quit and _handle_quit_response"

patterns-established:
  - "PTY widget pattern: PtyManager (no Textual deps) + TerminalWidget (Textual integration)"
  - "render_pyte_screen: pyte Screen.buffer to Rich Text with color/style fidelity"
  - "translate_key: Textual key events to ANSI escape sequences via KEY_MAP + ctrl+letter fallback"
  - "Graceful degradation: shutil.which check in compose() with Static fallback message"

requirements-completed: [CLAUDE-01, CLAUDE-02, CLAUDE-03]

# Metrics
duration: 5min
completed: 2026-03-22
---

# Phase 3 Plan 1: Terminal Emulation & Claude CLI Integration Summary

**PTY terminal emulation via pyte + pty.fork with embedded Claude Code CLI in ChatPanel, graceful degradation, and process lifecycle management**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-22T18:45:55Z
- **Completed:** 2026-03-22T18:51:37Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- Built complete terminal emulation module (nano_claude/terminal/) with PTY subprocess management, key translation (26+ key mappings), and pyte screen rendering with full ANSI color fidelity
- Replaced ChatPanel placeholder with real Claude Code CLI integration via TerminalWidget, with graceful degradation when claude CLI is not installed
- Added clean process lifecycle: PTY subprocess killed on app quit, Ctrl+Shift+R restart from anywhere, exit message with restart hint
- 41 new tests (29 terminal + 12 chat panel) all passing, full suite of 138 tests green

## Task Commits

Each task was committed atomically:

1. **Task 1: Create terminal emulation module (PTY manager + TerminalWidget)** - `57dfa8e` (test: RED), `307f2ac` (feat: GREEN)
2. **Task 2: Replace ChatPanel placeholder and wire PTY lifecycle into app** - `508b422` (feat)

_Note: Task 1 followed TDD with separate RED and GREEN commits._

## Files Created/Modified
- `nano_claude/terminal/__init__.py` - Package init exporting TerminalWidget, PtyManager, PtyDataReceived, PtyExited
- `nano_claude/terminal/pty_manager.py` - PTY lifecycle management, KEY_MAP, translate_key, PYTE_COLOR_MAP, render_pyte_screen, PtyManager class
- `nano_claude/terminal/widget.py` - TerminalWidget with pyte.HistoryScreen, threaded read loop, RESERVED_KEYS, PtyDataReceived/PtyExited messages
- `nano_claude/panels/chat.py` - Rewritten: embeds TerminalWidget or shows install instructions, handles PTY exit with restart
- `nano_claude/app.py` - Added Ctrl+Shift+R binding, action_restart_claude, _stop_claude_pty, PTY cleanup in quit paths
- `nano_claude/config/settings.py` - Added CLAUDE_NOT_FOUND_MESSAGE, CLAUDE_EXITED_MESSAGE, CLAUDE_RESTART_KEY
- `nano_claude/styles.tcss` - Added #claude-not-found, #claude-exited, #claude-terminal styles
- `tests/test_terminal_widget.py` - 29 tests for KEY_MAP, translate_key, PYTE_COLOR_MAP, render_pyte_screen, PtyManager
- `tests/test_chat_panel.py` - 12 tests for graceful degradation, messages, restart action, app bindings
- `pyproject.toml` - Added pyte dependency
- `uv.lock` - Updated lockfile

## Decisions Made
- Used stdlib pty.fork() instead of ptyprocess to avoid an extra dependency (pyte example uses raw pty.fork)
- pyte.HistoryScreen with history=10000 for scrollback (sufficient for most sessions)
- RESERVED_KEYS frozenset with 17 keys ensures app-level bindings (Ctrl+B/E/R/Q, Tab, etc.) always bubble up from the terminal
- Extracted _stop_claude_pty as a helper method for DRY cleanup across action_quit and _handle_quit_response
- PtyManager is Textual-independent (pure stdlib + pyte) for testability; TerminalWidget handles Textual integration

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Terminal emulation infrastructure complete, ready for Plan 03-02 (streaming bridge, if applicable)
- TerminalWidget and PtyManager are well-tested and modular for future enhancements
- ChatPanel graceful degradation ensures the app works even without claude CLI installed

## Self-Check: PASSED

All 10 created/modified files verified present. All 3 task commits (57dfa8e, 307f2ac, 508b422) verified in git log. 138/138 tests passing.

---
*Phase: 03-claude-code-integration*
*Completed: 2026-03-22*
