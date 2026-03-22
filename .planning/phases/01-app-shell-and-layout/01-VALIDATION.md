---
phase: 1
slug: app-shell-and-layout
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | LAYOUT-01 | integration | `uv run pytest tests/test_layout.py -x` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | LAYOUT-02 | integration | `uv run pytest tests/test_focus.py -x` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 1 | LAYOUT-03 | integration | `uv run pytest tests/test_resize.py -x` | ❌ W0 | ⬜ pending |
| 01-02-03 | 02 | 1 | LAYOUT-04 | integration | `uv run pytest tests/test_responsive.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pyproject.toml` — project configuration with test settings (asyncio_mode = "auto")
- [ ] `tests/conftest.py` — shared fixtures (app factory with configurable terminal size)
- [ ] `tests/test_layout.py` — stubs for LAYOUT-01 (three panels visible on launch)
- [ ] `tests/test_focus.py` — stubs for LAYOUT-02 (focus switching via shortcuts)
- [ ] `tests/test_resize.py` — stubs for LAYOUT-03 (panel resize via shortcuts)
- [ ] `tests/test_responsive.py` — stubs for LAYOUT-04 (terminal resize adaptation)
- [ ] Framework install: `uv add --dev pytest pytest-asyncio pytest-textual-snapshot`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Ctrl+letter shortcuts work in user's terminal | LAYOUT-02 | Terminal-specific key handling varies | Run `textual keys`, verify Ctrl+b/e/r produce events |
| Visual border highlight on active panel | LAYOUT-02 | CSS visual rendering hard to assert | Launch app, switch panels, verify border color changes |
| Layout looks correct at various terminal sizes | LAYOUT-04 | Visual proportions need human eye | Resize terminal from 200 to 40 cols, check panels adapt |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
