---
phase: 3
slug: claude-code-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_chat.py tests/test_status_parser.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_chat.py tests/test_status_parser.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | CLAUDE-01 | integration | `uv run pytest tests/test_chat.py::test_pty_spawn_and_render -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | CLAUDE-01 | integration | `uv run pytest tests/test_chat.py::test_key_forwarding -x` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | CLAUDE-03 | integration | `uv run pytest tests/test_chat.py::test_ansi_color_rendering -x` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | CLAUDE-04 | unit | `uv run pytest tests/test_status_parser.py -x` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | CLAUDE-05 | unit | `uv run pytest tests/test_status_parser.py::test_cost_parsing -x` | ❌ W0 | ⬜ pending |
| 03-02-03 | 02 | 2 | GRACEFUL | integration | `uv run pytest tests/test_chat.py::test_graceful_no_claude -x` | ❌ W0 | ⬜ pending |
| 03-02-04 | 02 | 2 | RESTART | integration | `uv run pytest tests/test_chat.py::test_crash_recovery -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_chat.py` — stubs for CLAUDE-01, CLAUDE-03, graceful degradation, restart
- [ ] `tests/test_status_parser.py` — stubs for CLAUDE-04, CLAUDE-05 (unit tests for parsing)
- [ ] Dependencies: `uv add pyte ptyprocess`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Claude Code renders with full fidelity (markdown, colors, spinners) | CLAUDE-01, CLAUDE-03 | Visual fidelity of ANSI rendering | Run app, type a prompt, verify output matches standalone `claude` |
| Claude inherits all features (tools, hooks, MCP, CLAUDE.md) | CLAUDE-02 | Requires real Claude API access | Verify CLAUDE.md is respected, tools work, MCP servers connect |
| Status indicator updates in real-time | CLAUDE-04 | Timing-dependent visual behavior | Watch status bar while Claude is thinking/writing |
| Permission prompts work in PTY | CLAUDE-02 | Requires real tool invocation | Ask Claude to edit a file, verify permission prompt appears |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
