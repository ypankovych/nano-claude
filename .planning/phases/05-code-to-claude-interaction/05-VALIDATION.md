---
phase: 5
slug: code-to-claude-interaction
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `.venv/bin/python -m pytest tests/ -x -q --tb=short` |
| **Full suite command** | `.venv/bin/python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `.venv/bin/python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | INTERACT-01 | unit | `.venv/bin/python -m pytest tests/test_send_to_claude.py -v` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | INTERACT-02 | unit | `.venv/bin/python -m pytest tests/test_ambient_context.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_send_to_claude.py` — stubs for INTERACT-01 (Ctrl+L send selection)
- [ ] `tests/test_ambient_context.py` — stubs for INTERACT-02 (Ctrl+P pin context, ambient injection)

*Existing infrastructure covers test framework and fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Ctrl+L sends selection to Claude PTY and focus moves to chat | INTERACT-01 | Requires live PTY + Textual app | 1. Open file, select text, press Ctrl+L 2. Verify code fence appears in Claude input 3. Verify focus is on chat panel |
| Ctrl+P pins context and status bar shows indicator | INTERACT-02 | Requires live Textual app rendering | 1. Select text, press Ctrl+P 2. Verify status bar shows "Pinned: file:lines" 3. Type prompt in Claude, verify context prepended |
| Ambient context injected before prompt on Enter | INTERACT-02 | Requires PTY interaction timing | 1. Pin context with Ctrl+P 2. Focus chat, type prompt, press Enter 3. Verify context block appears before prompt in PTY |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
