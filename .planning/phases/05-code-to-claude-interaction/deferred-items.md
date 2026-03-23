# Deferred Items - Phase 05

## Pre-existing test failure

- **File:** `tests/test_change_tracker.py::TestComputeChange::test_reports_all_added_without_snapshot`
- **Issue:** Test expects `compute_change` to return a non-None result for files without a prior snapshot, but the implementation returns None.
- **Scope:** Not related to Phase 05 changes. Pre-existing before any code-to-Claude interaction work.
