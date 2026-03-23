---
phase: 04-change-detection-and-auto-jump
plan: 01
subsystem: editor, services
tags: [difflib, change-detection, file-watcher, auto-reload, overlay]

# Dependency graph
requires:
  - phase: 02-editor-and-file-tree
    provides: "SearchableTextArea render_line pattern, BufferManager, FileWatcherService"
provides:
  - "ChangeTracker service with snapshot/diff computation"
  - "SearchableTextArea change highlights (green added, yellow modified)"
  - "ChangedFilesOverlay widget for multi-file change selection"
  - "EditorPanel reload_from_disk, scroll_to_line, set_change_highlights"
  - "App-level Ctrl+J jump-to-change with notification pipeline"
  - "ExternalChangeConflictScreen for unsaved edit conflicts"
affects: [04-02, diff-view, auto-jump]

# Tech tracking
tech-stack:
  added: [difflib.SequenceMatcher, difflib.unified_diff]
  patterns: [change-highlight-layering, auto-reload-with-conflict-detection]

key-files:
  created:
    - nano_claude/services/change_tracker.py
    - nano_claude/widgets/changed_files_overlay.py
    - tests/test_change_tracker.py
    - tests/test_change_detection.py
  modified:
    - nano_claude/widgets/searchable_text_area.py
    - nano_claude/panels/editor.py
    - nano_claude/app.py
    - nano_claude/terminal/widget.py

key-decisions:
  - "Used TextArea.render_line (grandparent) for base strip, then layer change highlights UNDER search highlights"
  - "Change highlights use dark_green (added) and dark_goldenrod (modified) for subtle background tinting"
  - "ExternalChangeConflictScreen follows UnsavedChangesScreen pattern with inline DEFAULT_CSS"
  - "Ctrl+J for jump-to-change (not Ctrl+G as context suggested) to avoid conflict with potential go-to-line"
  - "Change highlights auto-clear when user types in the file (stale diff markers)"

patterns-established:
  - "Change highlight layering: base syntax -> change tint -> search highlights (newest on top)"
  - "ChangeTracker snapshot-then-diff pattern with auto-update after compute"
  - "Auto-reload with conflict detection: check buf.is_modified before silent reload"

requirements-completed: [CHNG-01, CHNG-03]

# Metrics
duration: 8min
completed: 2026-03-23
---

# Phase 04 Plan 01: Change Detection and Auto-Jump Summary

**ChangeTracker service with difflib diff computation, green/yellow line highlights, Ctrl+J jump-to-change, auto-reload with conflict prompting, and changed-files overlay for multi-file navigation**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-23T12:39:57Z
- **Completed:** 2026-03-23T12:48:06Z
- **Tasks:** 2
- **Files modified:** 9 (7 source + 2 test)

## Accomplishments
- ChangeTracker service computes line-level diffs (added/modified/deleted) using difflib.SequenceMatcher opcodes
- SearchableTextArea renders green/yellow background tints on changed lines, layered under search highlights
- Toast notifications show filename and Ctrl+J hint when files change on disk
- Ctrl+J opens the most recently changed file and scrolls to first changed line
- ChangedFilesOverlay provides selectable list when multiple files change simultaneously
- Auto-reload preserves cursor position for unmodified open buffers
- ExternalChangeConflictScreen prompts user when open file has unsaved edits AND disk changes
- Change highlights auto-clear when user starts editing

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ChangeTracker service and test scaffolds** (TDD)
   - `d41eabe` (test): add failing tests for ChangeTracker service
   - `967299d` (feat): implement ChangeTracker service with difflib-based diff computation
2. **Task 2: Wire change detection into app** - `aecf336` (feat)

## Files Created/Modified
- `nano_claude/services/change_tracker.py` - FileChange dataclass and ChangeTracker with snapshot/diff/clear operations
- `nano_claude/widgets/changed_files_overlay.py` - Overlay widget for selecting from multiple changed files
- `nano_claude/widgets/searchable_text_area.py` - Added change highlight styles and render_line layering
- `nano_claude/panels/editor.py` - Added set_change_highlights, reload_from_disk, scroll_to_line, show_changed_files
- `nano_claude/app.py` - Extended on_file_system_changed, added Ctrl+J binding, ExternalChangeConflictScreen, ChangeTracker init
- `nano_claude/terminal/widget.py` - Added ctrl+j and ctrl+d to RESERVED_KEYS
- `tests/test_change_tracker.py` - 17 unit tests for ChangeTracker diff computation
- `tests/test_change_detection.py` - 22 integration tests for change detection pipeline

## Decisions Made
- Used TextArea.render_line (grandparent call) as base strip, then layer change highlights UNDER search highlights so search always wins visually
- Change highlights use dark_green and dark_goldenrod for subtle tinting that doesn't overwhelm syntax highlighting
- Chose Ctrl+J for jump-to-change instead of Ctrl+G (suggested in context) to avoid future conflict with go-to-line
- ExternalChangeConflictScreen uses inline DEFAULT_CSS following UnsavedChangesScreen pattern
- Change highlights auto-clear on any user edit to avoid stale markers

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Change detection pipeline fully operational for Plan 02 (diff view, Ctrl+D toggle)
- ChangeTracker.get_unified_diff() already implemented, ready for diff view rendering
- All 207 tests pass with no regressions

## Self-Check: PASSED

All 4 created files verified present on disk. All 3 commit hashes verified in git log.

---
*Phase: 04-change-detection-and-auto-jump*
*Completed: 2026-03-23*
