# Roadmap: nano-claude

## Overview

nano-claude delivers a terminal-native IDE with embedded Claude Code in six phases. The build order follows a strict dependency chain: the layout shell must exist before panels mount into it, the file tree and editor must exist before Claude's edits can trigger auto-jump, and the Claude bridge must exist before change detection can consume its events. The terminal panel is deferred last because it is technically independent and should not gate the core value loop (ask Claude, auto-jump to changes, review).

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: App Shell and Layout** - Multi-panel TUI skeleton with focus management and panel resizing
- [ ] **Phase 2: File Tree and Code Editor** - Browsable project tree and syntax-highlighted editor with full editing capabilities
- [ ] **Phase 3: Claude Code Integration** - Embedded Claude Code CLI subprocess with streaming chat, status indicators, and token tracking
- [ ] **Phase 4: Change Detection and Auto-Jump** - Automatic navigation to Claude's edits with change highlighting and diff view
- [ ] **Phase 5: Code-to-Claude Interaction** - Send code selections to Claude and expose editor context as ambient information
- [ ] **Phase 6: Terminal Panel** - Toggleable PTY-based terminal embedded in the TUI

## Phase Details

### Phase 1: App Shell and Layout
**Goal**: User launches the application and sees a responsive multi-panel layout with keyboard-driven navigation
**Depends on**: Nothing (first phase)
**Requirements**: LAYOUT-01, LAYOUT-02, LAYOUT-03, LAYOUT-04
**Success Criteria** (what must be TRUE):
  1. User launches the app and sees a three-panel layout (left, center, right) with placeholder content
  2. User can move focus between panels using keyboard shortcuts, with the active panel visually indicated
  3. User can resize panels wider or narrower using keyboard shortcuts
  4. User can resize the terminal window and panels adapt without crashing or overlapping
**Plans**: 2 plans

Plans:
- [ ] 01-01-PLAN.md — Project scaffolding, three-panel layout with header/footer, and responsive terminal resize handling
- [ ] 01-02-PLAN.md — Keyboard focus switching, panel resizing, and file tree toggle

### Phase 2: File Tree and Code Editor
**Goal**: User can browse project files in a tree and open, view, edit, and save them with syntax highlighting
**Depends on**: Phase 1
**Requirements**: TREE-01, TREE-02, TREE-03, TREE-04, EDIT-01, EDIT-02, EDIT-03, EDIT-04, EDIT-05, EDIT-06
**Success Criteria** (what must be TRUE):
  1. User sees the project directory as a collapsible tree in the left panel and can navigate it with keyboard (expand, collapse, move up/down)
  2. User selects a file in the tree and it opens in the center editor panel with syntax highlighting and line numbers
  3. User can edit file content (insert, delete, select, move cursor), undo/redo changes, and save with a keyboard shortcut
  4. User can search within the open file (find text, jump to next match)
  5. When files are added or removed externally (e.g., by git or another tool), the file tree updates automatically
**Plans**: 3 plans

Plans:
- [ ] 02-01-PLAN.md — Install dependencies, FilteredDirectoryTree with hidden file toggle, file tree keyboard navigation
- [ ] 02-02-PLAN.md — TextArea code editor with file buffer management, file selection wiring, save, unsaved changes tracking
- [ ] 02-03-PLAN.md — Search overlay (Ctrl+F find/navigate) and filesystem watcher for tree auto-refresh

### Phase 3: Claude Code Integration
**Goal**: User can converse with Claude Code inside the TUI and see its responses streamed in real time with status feedback
**Depends on**: Phase 1
**Requirements**: CLAUDE-01, CLAUDE-02, CLAUDE-03, CLAUDE-04, CLAUDE-05
**Success Criteria** (what must be TRUE):
  1. User types a prompt in the chat panel and sees Claude's response stream in token-by-token with markdown formatting and syntax-highlighted code blocks
  2. The embedded Claude Code subprocess inherits all user features (tools, hooks, MCP servers, CLAUDE.md, permissions) without any manual configuration
  3. User sees a status indicator reflecting Claude's current state (idle, thinking, writing code, waiting for permission)
  4. User sees token usage and estimated cost for the current session in the status bar
**Plans**: 2 plans

Plans:
- [ ] 03-01-PLAN.md — PTY terminal module (pyte + pty.fork), TerminalWidget, ChatPanel replacement with graceful degradation and restart
- [ ] 03-02-PLAN.md — Status/cost parser from PTY output, status bar integration, end-to-end visual verification

### Phase 4: Change Detection and Auto-Jump
**Goal**: When Claude edits files, the editor automatically navigates to the changes so the user never has to hunt for what changed
**Depends on**: Phase 2, Phase 3
**Requirements**: CHNG-01, CHNG-02, CHNG-03
**Success Criteria** (what must be TRUE):
  1. When Claude edits a file (via Write, Edit, or Bash tools), the editor automatically opens that file and scrolls to the changed lines with visual highlighting
  2. User can toggle a git-style diff view showing green additions and red deletions of Claude's changes via a keyboard shortcut
  3. When files change externally (git checkout, other tools), open files auto-reload with updated content
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD

### Phase 5: Code-to-Claude Interaction
**Goal**: User can direct Claude's attention to specific code selections and Claude sees what the user is looking at
**Depends on**: Phase 2, Phase 3
**Requirements**: INTERACT-01, INTERACT-02
**Success Criteria** (what must be TRUE):
  1. User selects code in the editor, presses a keyboard shortcut, types a prompt, and Claude receives both the selection (with file path and line numbers) and the prompt
  2. Claude automatically sees the user's current code selection as ambient context without the user explicitly sending it
**Plans**: TBD

Plans:
- [ ] 05-01: TBD

### Phase 6: Terminal Panel
**Goal**: User can run shell commands without leaving the TUI
**Depends on**: Phase 1
**Requirements**: TERM-01, TERM-02, TERM-03
**Success Criteria** (what must be TRUE):
  1. User can toggle a terminal panel on and off using a keyboard shortcut
  2. Terminal panel runs a full PTY-based shell supporting interactive commands (npm start, git, python scripts, etc.) with ANSI color rendering
  3. User can switch focus between the terminal panel and other panels using keyboard shortcuts
**Plans**: TBD

Plans:
- [ ] 06-01: TBD
- [ ] 06-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6
(Phases 2 and 3 could execute in parallel since both depend only on Phase 1.)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. App Shell and Layout | 0/2 | Planning complete | - |
| 2. File Tree and Code Editor | 0/3 | Planning complete | - |
| 3. Claude Code Integration | 0/2 | Planning complete | - |
| 4. Change Detection and Auto-Jump | 0/2 | Not started | - |
| 5. Code-to-Claude Interaction | 0/1 | Not started | - |
| 6. Terminal Panel | 0/2 | Not started | - |
