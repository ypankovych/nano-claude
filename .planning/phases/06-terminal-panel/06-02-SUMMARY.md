---
phase: 06-terminal-panel
plan: 02
subsystem: ui
tags: [textual, terminal, pty, layout, keyboard-bindings]

# Dependency graph
requires:
  - phase: 06-terminal-panel/01
    provides: TerminalPanel widget with ContentSwitcher tabs, minimize/restore, stop_all_ptys
provides:
  - App-level terminal panel integration with three-state Ctrl+T toggle
  - Ctrl+N/W tab management with focus guards
  - Shutdown cleanup via _stop_shell_ptys
  - Focus cycling support for terminal panel
  - 29 integration tests covering TERM-01, TERM-02, TERM-03
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Three-state toggle pattern (hidden->show+focus, visible->focus, focused->minimize)
    - Focus-guarded actions (Ctrl+N/W only respond when terminal panel is focused)
    - Vertical layout wrapper for bottom panel integration

key-files:
  created:
    - tests/test_terminal_panel.py
  modified:
    - nano_claude/app.py

key-decisions:
  - "Vertical(id='app-layout') wraps main-panels + terminal-panel for bottom panel layout"
  - "action_focus_panel checks isinstance(panel, TerminalPanel) and is_minimized to skip minimized terminal"
  - "Focus moved to editor BEFORE minimize to avoid focus-lost-to-nowhere"

patterns-established:
  - "Three-state toggle: hidden->show+focus, visible-unfocused->focus, focused->minimize"
  - "Focus-guarded app actions: check _panel_has_focus before delegating to panel"

requirements-completed: [TERM-01, TERM-02, TERM-03]

# Metrics
duration: 3min
completed: 2026-03-23
---

# Phase 06 Plan 02: Terminal Panel App Integration Summary

**Vertical layout restructure with three-state Ctrl+T toggle, focus-guarded Ctrl+N/W tab management, shutdown cleanup, and 29 integration tests**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-23T18:08:00Z
- **Completed:** 2026-03-23T18:11:01Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Wired TerminalPanel into app layout with Vertical wrapper and Ctrl+T/N/W bindings
- Implemented three-state toggle logic and focus-guarded tab management
- Added _stop_shell_ptys shutdown cleanup and action_focus_panel minimized-state check
- Created 29 integration tests covering all three TERM requirements

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire TerminalPanel into app layout, bindings, and lifecycle** - `7c86aac` (feat)
2. **Task 2: Create integration tests for terminal panel** - `03b0418` (test)

## Files Created/Modified
- `nano_claude/app.py` - Added TerminalPanel import, Vertical layout, Ctrl+T/N/W bindings, toggle/focus/cleanup actions
- `tests/test_terminal_panel.py` - 29 integration tests for RESERVED_KEYS, app bindings, app actions, TerminalPanel widget, settings

## Decisions Made
- Vertical(id="app-layout") wraps main-panels + terminal-panel for bottom panel layout
- action_focus_panel checks isinstance(panel, TerminalPanel) and is_minimized to skip minimized terminal
- Focus moved to editor BEFORE minimize to avoid focus-lost-to-nowhere

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing failure in tests/test_change_tracker.py::TestComputeChange::test_reports_all_added_without_snapshot (unrelated to this plan, not fixed per scope boundary rules)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Terminal panel feature is fully complete (Plan 01 widget + Plan 02 integration)
- All TERM requirements satisfied with test coverage
- Phase 06 (terminal-panel) is complete -- this is the final phase of v1.0

## Self-Check: PASSED

- All files exist (nano_claude/app.py, tests/test_terminal_panel.py, 06-02-SUMMARY.md)
- All commits verified (7c86aac, 03b0418)
- 29 tests pass, no regressions introduced

---
*Phase: 06-terminal-panel*
*Completed: 2026-03-23*
