---
phase: 02-file-tree-and-code-editor
plan: 01
subsystem: ui
tags: [textual, directory-tree, file-filtering, tree-sitter, watchfiles]

# Dependency graph
requires:
  - phase: 01-app-shell-and-layout plan 01
    provides: Three-panel layout with FileTreePanel placeholder
  - phase: 01-app-shell-and-layout plan 02
    provides: Focus management, keybinding infrastructure with priority and ids
provides:
  - FilteredDirectoryTree widget with hidden file filtering and sort order
  - HIDDEN_PATTERNS frozenset (12 patterns) and EXTENSION_TO_LANGUAGE dict (26 mappings)
  - MAX_FILE_SIZE_BYTES constant for large file threshold
  - Ctrl+H toggle for hidden file visibility
  - Phase 2 dependencies installed (textual[syntax], watchfiles, tree-sitter-language-pack)
affects: [02-02-PLAN, 02-03-PLAN, 04-change-detection]

# Tech tracking
tech-stack:
  added: [tree-sitter 0.25.2, tree-sitter-language-pack 1.0.0, watchfiles 1.1.1]
  patterns: [DirectoryTree subclass with filter_paths override, reactive show_hidden with guarded watch, directories-first sort]

key-files:
  created: []
  modified:
    - nano_claude/panels/file_tree.py
    - nano_claude/config/settings.py
    - nano_claude/app.py
    - pyproject.toml
    - tests/test_file_tree.py

key-decisions:
  - "Used frozenset for HIDDEN_PATTERNS -- immutable, hashable, performant for membership testing"
  - "Guard watch_show_hidden with try/except to handle reactive initialization outside mounted context"
  - "Sort filter_paths output: directories first, then files, case-insensitive alphabetical within groups"
  - "Ctrl+H for hidden file toggle -- standard dotfile visibility shortcut"

patterns-established:
  - "DirectoryTree subclass pattern: override filter_paths for custom filtering, reactive + watcher for live toggle"
  - "Guarded watcher pattern: wrap self.reload() in try/except for reactive attrs accessed before mount"
  - "Unit test pattern for Textual reactives: use _reactive_<name> internal attr or rely on defaults to avoid triggering watchers outside app context"

requirements-completed: [TREE-01, TREE-02]

# Metrics
duration: 5min
completed: 2026-03-22
---

# Phase 02 Plan 01: File Tree Widget Summary

**FilteredDirectoryTree with hidden file filtering (12 patterns + dotfiles), directories-first sort, and Ctrl+H toggle, replacing the Phase 1 placeholder**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-22T17:20:38Z
- **Completed:** 2026-03-22T17:26:33Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Installed Phase 2 dependencies: textual[syntax], watchfiles 1.1.1, tree-sitter-language-pack 1.0.0
- Added HIDDEN_PATTERNS (12 entries), EXTENSION_TO_LANGUAGE (26 mappings), MAX_FILE_SIZE_BYTES (1MB) to settings
- Replaced FileTreePanel placeholder with FilteredDirectoryTree that filters hidden files and dotfiles by default
- Added Ctrl+H binding to toggle hidden file visibility via show_hidden reactive
- Root directory expanded one level deep on mount
- 22 new tests (14 config + 8 widget/integration), total suite at 49 tests all passing

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1: Install dependencies and add configuration constants**
   - `289369f` (test) - failing tests for configuration constants
   - `2ef079c` (feat) - install deps, add HIDDEN_PATTERNS, EXTENSION_TO_LANGUAGE, MAX_FILE_SIZE_BYTES
2. **Task 2: Replace FileTreePanel placeholder with FilteredDirectoryTree**
   - `ad68d43` (test) - failing tests for FilteredDirectoryTree and FileTreePanel
   - `898949a` (feat) - implement FilteredDirectoryTree, update FileTreePanel, add Ctrl+H binding

## Files Created/Modified
- `pyproject.toml` - Added textual[syntax], watchfiles, tree-sitter-language-pack dependencies
- `nano_claude/config/settings.py` - Added HIDDEN_PATTERNS, EXTENSION_TO_LANGUAGE, MAX_FILE_SIZE_BYTES constants
- `nano_claude/panels/file_tree.py` - Replaced placeholder with FilteredDirectoryTree and FileTreePanel with tree composition
- `nano_claude/app.py` - Added Ctrl+H binding and action_toggle_hidden_files method
- `tests/test_file_tree.py` - 22 tests for config constants, filter_paths, integration

## Decisions Made
- Used frozenset for HIDDEN_PATTERNS for immutability and O(1) membership testing
- Guard watch_show_hidden with try/except to handle reactive initialization before widget mount (Textual reactive descriptor triggers watcher on first property access, even outside app context)
- Ctrl+H chosen for hidden file toggle (standard convention from file managers)
- Unit tests for filter_paths use default reactive value (False) or _reactive_show_hidden internal attribute to avoid triggering watcher outside app context

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Guarded watch_show_hidden against NoActiveAppError**
- **Found during:** Task 2 (TDD GREEN phase)
- **Issue:** Textual reactive descriptor triggers watch function on first property access, even when widget is not mounted. This caused NoActiveAppError in unit tests when filter_paths accessed self.show_hidden.
- **Fix:** Wrapped self.reload() in watch_show_hidden with try/except to gracefully handle unmounted context
- **Files modified:** nano_claude/panels/file_tree.py
- **Verification:** All 49 tests pass including unit tests that construct FilteredDirectoryTree outside app
- **Committed in:** 898949a (Task 2 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Minor defensive coding for Textual reactive lifecycle. No scope creep.

## Issues Encountered
None beyond the deviation documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- FilteredDirectoryTree is ready for Plan 02 (editor panel with TextArea.code_editor)
- EXTENSION_TO_LANGUAGE map ready for editor syntax highlighting detection
- MAX_FILE_SIZE_BYTES ready for large file warning in editor
- Ctrl+H toggle and hidden file filtering working for user exploration
- Tree keyboard navigation (up/down/enter) works natively via DirectoryTree
- TREE-01 and TREE-02 requirements satisfied

## Self-Check: PASSED

All 5 modified files verified present. All 4 task commits verified in git history.

---
*Phase: 02-file-tree-and-code-editor*
*Completed: 2026-03-22*
