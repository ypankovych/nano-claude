---
phase: 01-app-shell-and-layout
plan: 01
subsystem: ui
tags: [textual, tui, layout, panels, responsive, click]

# Dependency graph
requires: []
provides:
  - Three-panel TUI layout (file-tree, editor, chat) with Header/Footer
  - BasePanel container with border and focus-within styling
  - Responsive panel collapse at small terminal widths
  - CLI entry point with optional path argument
  - Project scaffolding with pyproject.toml, uv, and test infrastructure
affects: [02-app-shell-and-layout, 02-file-tree-and-editor, 03-claude-integration]

# Tech tracking
tech-stack:
  added: [textual 8.1.1, click 8.3.1, pytest 9.0.2, pytest-asyncio 1.3.0, ruff, textual-dev]
  patterns: [Horizontal container with fr-unit widths, BasePanel inheritance, CSS-driven layout, on_resize with call_later]

key-files:
  created:
    - pyproject.toml
    - nano_claude/__init__.py
    - nano_claude/__main__.py
    - nano_claude/cli.py
    - nano_claude/app.py
    - nano_claude/styles.tcss
    - nano_claude/panels/__init__.py
    - nano_claude/panels/base.py
    - nano_claude/panels/file_tree.py
    - nano_claude/panels/editor.py
    - nano_claude/panels/chat.py
    - nano_claude/config/__init__.py
    - nano_claude/config/settings.py
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_layout.py
    - tests/test_responsive.py
  modified: []

key-decisions:
  - "Used fr units (1fr/3.3fr/2.3fr) instead of percentages for automatic redistribution on panel toggle"
  - "BasePanel uses DEFAULT_CSS for border styling to avoid duplication in styles.tcss"
  - "EditorPanel checks Path.cwd()/README.md at compose time for startup content decision"
  - "Responsive collapse uses on_resize with call_later to defer after layout recalculation"

patterns-established:
  - "BasePanel inheritance: all panels extend BasePanel(Vertical) for consistent border/focus styling"
  - "Panel placeholder pattern: Static with can_focus=True and unique id for Phase 2+ replacement"
  - "Responsive collapse: CSS .hidden class with on_resize handler checking threshold constants"
  - "Test pattern: async with app.run_test(size=(w,h)) as pilot for Textual integration tests"

requirements-completed: [LAYOUT-01, LAYOUT-04]

# Metrics
duration: 5min
completed: 2026-03-22
---

# Phase 01 Plan 01: App Shell and Three-Panel Layout Summary

**Three-panel TUI layout (file-tree/editor/chat) with fr-based widths, responsive collapse at small terminals, and README.md auto-detection on startup**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-22T16:25:17Z
- **Completed:** 2026-03-22T16:30:04Z
- **Tasks:** 2
- **Files modified:** 17

## Accomplishments
- Three-panel layout with Horizontal container using fr-based widths (1fr/3.3fr/2.3fr approximating 15%/50%/35%)
- EditorPanel auto-detects README.md in cwd and shows its name, or displays welcome greeting with shortcut hints
- Responsive panel collapse: file tree hides at <60 cols, chat hides at <40 cols, panels restore on resize
- Full project scaffolding with pyproject.toml, CLI entry point, and 14 passing tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Create project scaffolding and three-panel layout**
   - `066e39d` (test) - failing tests for layout structure
   - `eddd98d` (feat) - implementation with all 8 layout tests passing
2. **Task 2: Implement responsive resize and panel collapse logic**
   - `543278e` (test) - failing tests for responsive behavior
   - `01c0305` (feat) - implementation with all 14 tests passing

## Files Created/Modified
- `pyproject.toml` - Project config with textual, click deps and test settings
- `nano_claude/__init__.py` - Package init with version
- `nano_claude/__main__.py` - python -m entry point
- `nano_claude/cli.py` - Click CLI with optional path argument
- `nano_claude/app.py` - NanoClaudeApp with layout composition and responsive collapse
- `nano_claude/styles.tcss` - Textual CSS with fr-based panel widths
- `nano_claude/panels/base.py` - BasePanel(Vertical) with border/focus-within styling
- `nano_claude/panels/file_tree.py` - FileTreePanel placeholder
- `nano_claude/panels/editor.py` - EditorPanel with README.md detection
- `nano_claude/panels/chat.py` - ChatPanel placeholder
- `nano_claude/config/settings.py` - Layout defaults, collapse thresholds, welcome greeting
- `tests/conftest.py` - Shared test fixtures
- `tests/test_layout.py` - 8 tests for layout structure and startup content
- `tests/test_responsive.py` - 6 tests for resize collapse/restore behavior

## Decisions Made
- Used fr units (1fr/3.3fr/2.3fr) instead of percentages -- fr units auto-redistribute when panels are hidden
- BasePanel applies border styling via DEFAULT_CSS rather than duplicating in styles.tcss -- avoids specificity conflicts
- EditorPanel checks README.md at compose time, not mount time -- simpler and testable with monkeypatch.chdir
- Responsive collapse defers via call_later per Pitfall 4 (on_resize fires before layout redraws)
- Static widget `.content` attribute used for test assertions (not `.renderable` which doesn't exist)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Static widget attribute access in tests**
- **Found during:** Task 1 (TDD GREEN phase)
- **Issue:** Plan's test code used `placeholder.renderable` but Textual 8.1.1 Static widget uses `.content` attribute
- **Fix:** Changed test assertions to use `placeholder.content` instead of `placeholder.renderable`
- **Files modified:** tests/test_layout.py
- **Verification:** All 8 layout tests pass
- **Committed in:** eddd98d (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Trivial API naming difference. No scope creep.

## Issues Encountered
- hatchling build failed on initial `uv sync` because `nano_claude/` package directory didn't exist yet. Created the directory structure before re-running `uv sync`. This is expected for a greenfield project.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Three-panel layout is ready for Plan 02 (focus management and panel resizing)
- Panel placeholders have focusable Static widgets that Plan 02 will use for focus switching
- All panel IDs (file-tree, editor, chat) are stable for keybinding targets
- BasePanel inheritance pattern established for consistent styling

## Self-Check: PASSED

All 17 created files verified present. All 4 task commits verified in git history.

---
*Phase: 01-app-shell-and-layout*
*Completed: 2026-03-22*
