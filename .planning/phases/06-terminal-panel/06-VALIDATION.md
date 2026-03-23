---
phase: 6
slug: terminal-panel
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `.venv/bin/python -m pytest tests/test_terminal_panel.py -x -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/test_terminal_panel.py -x -q`
- **After every plan wave:** Run `.venv/bin/python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | TERM-01 | unit | `.venv/bin/python -m pytest tests/test_terminal_panel.py -k "toggle" -x -q` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | TERM-02 | unit | `.venv/bin/python -m pytest tests/test_terminal_panel.py -k "pty_shell" -x -q` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 1 | TERM-03 | unit | `.venv/bin/python -m pytest tests/test_terminal_panel.py -k "focus" -x -q` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 1 | TERM-01 | unit | `.venv/bin/python -m pytest tests/test_terminal_panel.py -k "minimize" -x -q` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 1 | TERM-02 | unit | `.venv/bin/python -m pytest tests/test_terminal_panel.py -k "multi_tab" -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_terminal_panel.py` — stubs for TERM-01, TERM-02, TERM-03
- [ ] Test fixtures for TerminalPanel widget mounting and PTY lifecycle

*Existing test infrastructure (pytest, conftest.py) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ANSI color rendering | TERM-02 | Visual output verification | Run `ls --color` in terminal panel, verify colors display |
| Interactive command support | TERM-02 | Requires real PTY interaction | Run `python3` REPL, type expression, verify output |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
