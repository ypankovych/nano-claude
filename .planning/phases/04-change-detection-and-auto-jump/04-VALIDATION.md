---
phase: 4
slug: change-detection-and-auto-jump
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | CHNG-01 | unit | `uv run pytest tests/test_change_tracker.py -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | CHNG-01 | integration | `uv run pytest tests/test_change_detection.py -x` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | CHNG-02 | unit | `uv run pytest tests/test_change_tracker.py::test_unified_diff -x` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | CHNG-02 | integration | `uv run pytest tests/test_change_detection.py::test_diff_toggle -x` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 2 | CHNG-03 | unit | `uv run pytest tests/test_change_detection.py::test_auto_reload -x` | ❌ W0 | ⬜ pending |
| 04-03-02 | 03 | 2 | CHNG-03 | integration | `uv run pytest tests/test_change_detection.py::test_conflict_prompt -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_change_tracker.py` — stubs for ChangeTracker unit tests (diff computation, line ranges)
- [ ] `tests/test_change_detection.py` — stubs for integration tests (notifications, highlights, jump, diff toggle, auto-reload, conflict)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Change highlight colors visible on changed lines | CHNG-01 | Visual rendering | Ask Claude to edit a file, verify green/yellow background on changed lines |
| Diff view renders readable unified diff | CHNG-02 | Visual rendering | Toggle Ctrl+D, verify green/red diff lines are legible |
| Notification toast appears when Claude edits | CHNG-01 | Timing/visual | Watch for toast after Claude edit, verify Ctrl+J jumps to file |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
