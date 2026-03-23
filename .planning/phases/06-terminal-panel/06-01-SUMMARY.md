---
phase: 06-terminal-panel
plan: 01
subsystem: ui
tags: [terminal, pty, textual, content-switcher, shell, tabs]

# Dependency graph
requires:
  - phase: 03-claude-integration
    provides: "TerminalWidget, PtyExited, PtyManager, RESERVED_KEYS"
  - phase: 01-layout-focus
    provides: "BasePanel base class"
provides:
  - "TerminalPanel widget with multi-tab shell session management"
  - "RESERVED_KEYS updated with ctrl+t/n/w for terminal shortcuts"
  - "Terminal panel CSS rules and #app-layout wrapper rule"
  - "Terminal settings constants (height, max tabs, status messages)"
affects: [06-terminal-panel]

# Tech tracking
tech-stack:
  added: []
  patterns: ["ContentSwitcher for tab management", "reactive minimize/restore state"]

key-files:
  created:
    - nano_claude/panels/terminal.py
  modified:
    - nano_claude/terminal/widget.py
    - nano_claude/config/settings.py
    - nano_claude/styles.tcss

key-decisions:
  - "ContentSwitcher for tab management with 1-indexed position display in tab bar"
  - "Starts minimized (status line only) per CONTEXT.md, auto-opens first tab on restore"
  - "Rich markup for tab bar with bold reverse highlighting on active tab"
  - "Shell exit replaces dead terminal with Static message inside switcher"

patterns-established:
  - "TerminalPanel minimize/restore pattern: reactive bool with _apply_minimized_state guard"
  - "Tab lifecycle: add_tab creates TerminalWidget, close_active_tab stops PTY first, last tab close triggers minimize"

requirements-completed: [TERM-01, TERM-02]

# Metrics
duration: 2min
completed: 2026-03-23
---

# Phase 06 Plan 01: Terminal Panel Widget Summary

**Multi-tab TerminalPanel with ContentSwitcher tab management, minimize/restore reactive state, $SHELL spawning, and RESERVED_KEYS protection for ctrl+t/n/w**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-23T18:03:18Z
- **Completed:** 2026-03-23T18:05:26Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created TerminalPanel widget extending BasePanel with full tab lifecycle (add/close/stop_all)
- Added minimize/restore reactive state starting minimized, with auto-tab-creation on restore
- Updated RESERVED_KEYS with ctrl+t, ctrl+n, ctrl+w (24 keys total) preventing PTY consumption
- Added terminal panel CSS rules for tab bar, switcher, status line, and app-layout wrapper

## Task Commits

Each task was committed atomically:

1. **Task 1: Create TerminalPanel widget with tab management and minimize/restore** - `7088e01` (feat)
2. **Task 2: Update RESERVED_KEYS and add terminal panel CSS rules** - `55dd21c` (feat)

## Files Created/Modified
- `nano_claude/panels/terminal.py` - TerminalPanel with ContentSwitcher tabs, minimize/restore, PtyExited handling
- `nano_claude/config/settings.py` - Terminal panel constants (height, max tabs, status messages)
- `nano_claude/terminal/widget.py` - RESERVED_KEYS updated with ctrl+t/n/w, reordered alphabetically
- `nano_claude/styles.tcss` - CSS rules for #terminal-panel, tab bar, switcher, status line, #app-layout

## Decisions Made
- ContentSwitcher for tab management -- Textual's built-in widget for showing one child at a time, natural fit for tab switching
- Rich markup for tab bar display -- bold reverse for active tab, plain for inactive, using Text.from_markup
- Shell exit shows Static message in-place -- dead terminal replaced with exit message inside switcher, preserving tab structure
- Starts minimized per CONTEXT.md -- status line only visible until user activates with ctrl+t

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test failure in test_change_tracker.py (test_reports_all_added_without_snapshot) -- not caused by this plan's changes, out of scope

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- TerminalPanel widget is self-contained and ready for Plan 02 integration
- Plan 02 will wire TerminalPanel into the app layout, bindings, and focus system
- CSS rules for #app-layout already prepared for the Vertical wrapper Plan 02 will add

## Self-Check: PASSED

All 4 files verified present. Both task commits (7088e01, 55dd21c) verified in git log.

---
*Phase: 06-terminal-panel*
*Completed: 2026-03-23*
