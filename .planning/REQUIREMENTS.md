# Requirements: nano-claude

**Defined:** 2026-03-22
**Core Value:** Eliminate context switching between Claude Code and your editor — see Claude's changes the moment they happen, and let Claude see what you're looking at.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Layout

- [x] **LAYOUT-01**: User sees a split-panel TUI with file tree (left), code editor (center), and Claude chat (right) on launch
- [x] **LAYOUT-02**: User can switch focus between panels using keyboard shortcuts
- [x] **LAYOUT-03**: User can resize panels using keyboard shortcuts
- [x] **LAYOUT-04**: Layout adapts gracefully when terminal is resized (panels collapse at small sizes)

### Editor

- [x] **EDIT-01**: User can open files from the file tree and view them with syntax highlighting (90+ languages via tree-sitter)
- [x] **EDIT-02**: User can edit file content with standard text editing (insert, delete, selection, cursor movement)
- [x] **EDIT-03**: User can undo and redo edits
- [x] **EDIT-04**: User can save files with a keyboard shortcut
- [x] **EDIT-05**: User sees line numbers in the editor
- [x] **EDIT-06**: User can search within the current file (find, find next)

### File Tree

- [x] **TREE-01**: User sees the project directory structure in a collapsible tree
- [x] **TREE-02**: User can navigate the file tree with keyboard (up/down, expand/collapse)
- [x] **TREE-03**: User can open a file in the editor by selecting it in the tree
- [x] **TREE-04**: File tree auto-refreshes when files are added or removed

### Claude Integration

- [x] **CLAUDE-01**: User can type prompts in the Claude chat panel and receive streaming responses from the actual Claude Code CLI running as an embedded subprocess
- [x] **CLAUDE-02**: Claude Code subprocess inherits all features (tools, hooks, MCP servers, CLAUDE.md, permissions) — no reimplementation
- [x] **CLAUDE-03**: User sees Claude's responses rendered with markdown formatting and syntax-highlighted code blocks
- [ ] **CLAUDE-04**: User sees a status indicator showing Claude's current state (idle, thinking, writing code, waiting for permission)
- [ ] **CLAUDE-05**: User sees token usage and estimated cost for the current session in the status bar

### Change Detection

- [ ] **CHNG-01**: When Claude edits a file, the editor automatically jumps to that file and highlights the changed lines
- [ ] **CHNG-02**: User can toggle a git-style diff view (green additions, red deletions) of Claude's changes via a keyboard shortcut
- [ ] **CHNG-03**: A filesystem watcher detects external file changes (git operations, other tools) and auto-reloads open files

### Code-to-Claude Interaction

- [ ] **INTERACT-01**: User can select code in the editor and send it to Claude with a prompt via a keyboard shortcut
- [ ] **INTERACT-02**: Claude automatically sees the user's current code selection as ambient context (file path, line numbers, selected text)

### Terminal

- [ ] **TERM-01**: User can toggle a terminal panel via a keyboard shortcut
- [ ] **TERM-02**: Terminal panel is a full PTY-based terminal supporting interactive commands (npm start, git, etc.)
- [ ] **TERM-03**: User can switch focus between terminal panel and other panels with keyboard shortcuts

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Persistence

- **PERSIST-01**: User's session (open files, cursor positions, panel layout) is saved and restored across app restarts
- **PERSIST-02**: Claude conversation history persists across sessions (leveraging Claude Code's built-in persistence)

### Advanced Editor

- **ADVEDIT-01**: User can search across all project files (grep/ripgrep-style)
- **ADVEDIT-02**: User can open multiple files in tabs or a buffer list
- **ADVEDIT-03**: User can customize keybindings via config file

### Visual

- **VISUAL-01**: User can select a color theme (dracula, monokai, vscode_dark, github_light)
- **VISUAL-02**: User can view git blame/status annotations in the editor gutter

## Out of Scope

| Feature | Reason |
|---------|--------|
| Vim/Emacs modal editing | Custom controls designed for this tool's unique editor+AI+terminal workflow |
| Plugin/extension system | v1 is focused and opinionated; revisit if demand emerges |
| Direct Claude API calls | Embeds actual Claude Code CLI to inherit all features (tools, hooks, MCP) |
| Multi-model support (GPT, Gemini) | Claude-only via CLI; other models have different tool-calling patterns |
| GUI version (Electron/Tauri) | Terminal-native IS the differentiator; GUI AI editors already exist |
| LSP integration (autocomplete, go-to-definition) | Claude IS the intelligence layer; LSP is a distraction from AI-first workflow |
| Inline AI autocomplete (Copilot-style) | Requires separate fast model; contradicts embed-CLI architecture |
| Real-time collaboration | Single-user tool; enormous complexity for irrelevant use case |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| LAYOUT-01 | Phase 1 | Complete |
| LAYOUT-02 | Phase 1 | Complete |
| LAYOUT-03 | Phase 1 | Complete |
| LAYOUT-04 | Phase 1 | Complete |
| EDIT-01 | Phase 2 | Complete |
| EDIT-02 | Phase 2 | Complete |
| EDIT-03 | Phase 2 | Complete |
| EDIT-04 | Phase 2 | Complete |
| EDIT-05 | Phase 2 | Complete |
| EDIT-06 | Phase 2 | Complete |
| TREE-01 | Phase 2 | Complete |
| TREE-02 | Phase 2 | Complete |
| TREE-03 | Phase 2 | Complete |
| TREE-04 | Phase 2 | Complete |
| CLAUDE-01 | Phase 3 | Complete |
| CLAUDE-02 | Phase 3 | Complete |
| CLAUDE-03 | Phase 3 | Complete |
| CLAUDE-04 | Phase 3 | Pending |
| CLAUDE-05 | Phase 3 | Pending |
| CHNG-01 | Phase 4 | Pending |
| CHNG-02 | Phase 4 | Pending |
| CHNG-03 | Phase 4 | Pending |
| INTERACT-01 | Phase 5 | Pending |
| INTERACT-02 | Phase 5 | Pending |
| TERM-01 | Phase 6 | Pending |
| TERM-02 | Phase 6 | Pending |
| TERM-03 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 27 total
- Mapped to phases: 27
- Unmapped: 0

---
*Requirements defined: 2026-03-22*
*Last updated: 2026-03-22 after roadmap creation*
