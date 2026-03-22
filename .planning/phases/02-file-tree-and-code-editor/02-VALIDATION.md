---
phase: 2
slug: file-tree-and-code-editor
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 2 — Validation Strategy

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
| 02-01-01 | 01 | 1 | TREE-01 | integration | `uv run pytest tests/test_file_tree.py::test_directory_tree_renders -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | TREE-02 | integration | `uv run pytest tests/test_file_tree.py::test_tree_keyboard_navigation -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | TREE-03 | integration | `uv run pytest tests/test_file_tree.py::test_file_selection_opens_editor -x` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | EDIT-01 | integration | `uv run pytest tests/test_editor.py::test_open_file_with_highlighting -x` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | EDIT-02 | integration | `uv run pytest tests/test_editor.py::test_text_editing_operations -x` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 1 | EDIT-03 | integration | `uv run pytest tests/test_editor.py::test_undo_redo -x` | ❌ W0 | ⬜ pending |
| 02-02-04 | 02 | 1 | EDIT-04 | integration | `uv run pytest tests/test_editor.py::test_save_file -x` | ❌ W0 | ⬜ pending |
| 02-02-05 | 02 | 1 | EDIT-05 | integration | `uv run pytest tests/test_editor.py::test_line_numbers_visible -x` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | EDIT-06 | integration | `uv run pytest tests/test_search.py::test_search_find_and_navigate -x` | ❌ W0 | ⬜ pending |
| 02-04-01 | 04 | 2 | TREE-04 | integration | `uv run pytest tests/test_file_watcher.py::test_tree_refresh_on_external_change -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_file_tree.py` — stubs for TREE-01, TREE-02, TREE-03
- [ ] `tests/test_editor.py` — stubs for EDIT-01..05
- [ ] `tests/test_search.py` — stubs for EDIT-06
- [ ] `tests/test_file_watcher.py` — stubs for TREE-04
- [ ] Dependencies: `uv add "textual[syntax]" watchfiles`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Syntax highlighting renders correct colors | EDIT-01 | Visual rendering hard to assert | Open a .py file, verify Python keywords are colored |
| Line numbers align with content | EDIT-05 | Visual alignment | Open file, scroll, verify numbers match lines |
| Search highlights all matches simultaneously | EDIT-06 | Visual styling | Open file, Ctrl+F, type common word, verify all instances highlighted |
| File tree icons render correctly | TREE-01 | Unicode rendering varies by terminal | Launch app, check folder/file icons |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
