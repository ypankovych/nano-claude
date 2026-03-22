# Phase 2: File Tree and Code Editor - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the placeholder panels from Phase 1 with real widgets. The left panel gets a DirectoryTree for browsing project files. The center panel gets a TextArea code editor with syntax highlighting, line numbers, editing, save, undo/redo, and search-in-file. Users can browse files in the tree, open them in the editor, edit and save them.

</domain>

<decisions>
## Implementation Decisions

### File Tree Behavior
- Hide dotfiles, .git, node_modules, __pycache__, .venv by default — toggleable via shortcut to show hidden files
- Open file on Enter (keyboard) or click (mouse) — both work
- Expand root directory one level deep on launch (not fully collapsed, not deeply expanded)
- Basic unicode icons for folders/files (📁/📄 or ▶/▼ style) — nothing language-specific

### Editor Feel
- Auto-detect indentation from opened file (tabs vs spaces, indent width) — respect existing file style
- No word wrap — horizontal scroll for long lines, preserves code structure
- Unsaved changes indicated by BOTH a dot (●) in the editor title bar AND filename color change
- Unsaved changes kept in buffer when switching files — no prompt, no auto-save on file switch
- Prompt to save unsaved changes when quitting the app (Ctrl+Q) — prevent data loss on exit
- Save shortcut: standard (Ctrl+S)

### Search in File
- Search bar appears as a top overlay inside the editor panel (like VS Code Ctrl+F)
- Ctrl+F to open search, Escape to close
- All matches highlighted in the file simultaneously, current match in a different/brighter color
- Next match (Enter or Ctrl+G), previous match (Shift+Enter or Ctrl+Shift+G)
- Plain text search only for v1 — no regex support

### File Tree Refresh
- Filesystem watcher (watchfiles) for real-time auto-refresh when files are added/removed externally
- Preserve expanded directory state across refreshes — don't collapse/disorient the user
- This watcher is foundational — Phase 4 (Change Detection) will also use it for auto-reload of open files

### Claude's Discretion
- Exact hidden file patterns (beyond .git, node_modules, __pycache__, .venv)
- How indentation detection algorithm works (first N lines? EditorConfig support?)
- Search highlight colors (current match vs other matches)
- How the search overlay interacts with editor keybindings (focus management)
- Large file handling (lazy loading, size threshold warning)
- File tree sort order (alphabetical, folders first, etc.)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### TUI Framework & Widgets
- `.planning/research/STACK.md` — Textual 8.1.1, TextArea.code_editor() with tree-sitter, DirectoryTree widget
- `.planning/research/ARCHITECTURE.md` — Widget composition, panel structure, inter-panel communication
- `.planning/research/FEATURES.md` — Feature prioritization, MVP definition, dependency graph
- `.planning/research/PITFALLS.md` — TextArea performance with large files (tree-sitter quadratic scaling), watchfiles vs watchdog

### Phase 1 Implementation
- `nano_claude/panels/editor.py` — Current EditorPanel placeholder to replace
- `nano_claude/panels/file_tree.py` — Current FileTreePanel placeholder to replace
- `nano_claude/panels/base.py` — BasePanel base class with focus-within CSS
- `nano_claude/app.py` — NanoClaudeApp with keybindings and panel management
- `nano_claude/styles.tcss` — Existing CSS for panel widths and borders

### Requirements
- `.planning/REQUIREMENTS.md` — TREE-01 through TREE-04, EDIT-01 through EDIT-06

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BasePanel(Vertical)` in `panels/base.py` — All panels extend this; provides border + focus-within styling with title bar highlight
- `NanoClaudeApp` in `app.py` — Has BINDINGS with `id=` for keymap overrides, `action_focus_panel()` for direct panel jumping
- `settings.py` in `config/` — Layout constants (DEFAULT_TREE_WIDTH, COLLAPSE_TREE_THRESHOLD, etc.)
- `styles.tcss` — fr-based panel widths, `.hidden` class for toggle

### Established Patterns
- Panels extend BasePanel, override `compose()` to yield their widgets
- `panel_title` reactive attribute on BasePanel sets the border title
- All keybindings use `Binding(key, action, desc, id=..., priority=True)` pattern
- Focus management via `action_focus_panel(panel_id)` which finds first focusable child

### Integration Points
- `EditorPanel.compose()` — Currently yields a Static placeholder; replace with TextArea.code_editor()
- `FileTreePanel.compose()` — Currently yields a Static placeholder; replace with DirectoryTree
- `NanoClaudeApp.BINDINGS` — Add new bindings for save (Ctrl+S), find (Ctrl+F)
- `NanoClaudeApp.sub_title` — Already set up to show current file; wire to editor's open file
- FileTreePanel needs to communicate file selection to EditorPanel (Textual message system)

</code_context>

<specifics>
## Specific Ideas

- File tree + editor should feel like VS Code's sidebar — browse and click to open, keyboard navigation with arrows
- Unsaved indicator dot (●) mimics VS Code's modified file marker
- Search overlay should feel like Ctrl+F in any modern editor — not a modal dialog, not a separate panel
- The filesystem watcher from this phase will be reused in Phase 4 for auto-reload when Claude edits files

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-file-tree-and-code-editor*
*Context gathered: 2026-03-22*
