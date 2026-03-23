---
phase: 05-code-to-claude-interaction
plan: 01
subsystem: interaction
tags: [pty, bracketed-paste, code-fence, ctrl-l, selection]

# Dependency graph
requires:
  - phase: 03-claude-integration
    provides: "PTY subprocess with TerminalWidget and RESERVED_KEYS"
  - phase: 02-editor-panel
    provides: "EditorPanel with TextArea selection API and file buffers"
provides:
  - "CodeContext dataclass with format_code_fence method"
  - "write_to_pty_bracketed utility for safe PTY text injection"
  - "truncate_selection for large selection handling"
  - "EditorPanel.get_selection_context for extracting editor selection"
  - "Ctrl+L binding and action_send_to_claude wiring"
affects: [05-02-pin-context, future-interaction-features]

# Tech tracking
tech-stack:
  added: []
  patterns: [bracketed-paste-pty-injection, code-fence-formatting, selection-before-focus-switch]

key-files:
  created:
    - nano_claude/models/code_context.py
    - tests/test_code_interaction.py
  modified:
    - nano_claude/panels/editor.py
    - nano_claude/terminal/widget.py
    - nano_claude/app.py

key-decisions:
  - "Extract selection BEFORE focus switch to chat panel (selection may clear on blur)"
  - "Bracketed paste wrapping prevents terminal auto-indent on multi-line injection"
  - "4096-byte chunks for PTY writes to avoid buffer overflow"
  - "Truncation at 200 lines / 8192 bytes with trailing marker"

patterns-established:
  - "PTY injection pattern: format as code fence, wrap in bracketed paste, write in chunks"
  - "Selection extraction pattern: selected_text if exists, else current line at cursor"

requirements-completed: [INTERACT-01]

# Metrics
duration: 7min
completed: 2026-03-23
---

# Phase 5 Plan 1: Send Selection to Claude Summary

**Ctrl+L sends editor selection (or current line) to Claude's PTY as a bracketed-paste markdown code fence, then focuses the chat panel for prompt entry**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-23T15:39:08Z
- **Completed:** 2026-03-23T15:46:08Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- CodeContext dataclass formats selections as markdown code fences with file path, line range, and language
- write_to_pty_bracketed safely injects text into Claude's PTY using bracketed paste mode with chunked writes
- EditorPanel.get_selection_context extracts the current selection or falls back to current line
- Large selections (>200 lines or >8KB) are truncated with a clear marker
- Ctrl+L is reserved from PTY capture, bound in app, and wired end-to-end
- 13 new tests covering all code paths

## Task Commits

Each task was committed atomically:

1. **Task 1: Create CodeContext model, PTY write utility, and EditorPanel.get_selection_context**
   - `b4f251f` (test: add failing tests -- TDD RED)
   - `b8193e6` (feat: implement CodeContext, write_to_pty_bracketed, get_selection_context -- TDD GREEN)
2. **Task 2: Wire Ctrl+L binding, action_send_to_claude, and RESERVED_KEYS** - `0a4f180` (feat)

_Note: Task 1 followed TDD with RED/GREEN commits._

## Files Created/Modified
- `nano_claude/models/code_context.py` - CodeContext dataclass, truncate_selection, write_to_pty_bracketed, constants
- `nano_claude/panels/editor.py` - Added get_selection_context method and CodeContext import
- `nano_claude/terminal/widget.py` - Added "ctrl+l" to RESERVED_KEYS
- `nano_claude/app.py` - Added Ctrl+L binding, action_send_to_claude, top-level imports for TerminalWidget and write_to_pty_bracketed
- `tests/test_code_interaction.py` - 13 tests: CodeContext formatting, truncation, PTY write, constants, RESERVED_KEYS

## Decisions Made
- Extract selection BEFORE switching focus to chat panel (Textual may clear selection on blur)
- Use bracketed paste escape sequences to prevent terminal auto-indent on multi-line paste
- Write to PTY in 4096-byte chunks to avoid buffer overflow
- Truncate at 200 lines / 8192 bytes with "... (truncated)" marker
- Top-level import of TerminalWidget in app.py (was previously lazy-imported only in _stop_claude_pty)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test failure in test_change_tracker.py::TestComputeChange::test_reports_all_added_without_snapshot (unrelated to this plan's changes, confirmed by testing against prior commit)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- CodeContext model and write_to_pty_bracketed utility are ready for reuse by Plan 02 (Pin Context / Ctrl+P)
- RESERVED_KEYS pattern established for adding future shortcuts
- action_send_to_claude demonstrates the selection-extract-then-inject pattern that Plan 02 will extend

---
*Phase: 05-code-to-claude-interaction*
*Completed: 2026-03-23*

## Self-Check: PASSED
