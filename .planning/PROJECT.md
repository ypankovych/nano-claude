# nano-claude

## What This Is

A terminal-native IDE that embeds Claude Code as a first-class panel alongside a code editor, file tree, and terminal. Built for developers who love Claude Code but are tired of switching between terminal and a separate editor to read, review, and navigate code. One terminal window, everything in view.

## Core Value

Eliminate context switching between Claude Code and your editor — see Claude's changes the moment they happen, and let Claude see what you're looking at.

## Requirements

### Validated

- ✓ Split-panel TUI with three-panel layout (file tree, editor, chat) — Phase 1
- ✓ Panel resizing and layout management — Phase 1
- ✓ Keyboard-driven panel navigation with focus indicators — Phase 1
- ✓ Responsive terminal resize with panel collapse — Phase 1
- ✓ File tree navigation with hidden file filtering and auto-refresh — Phase 2
- ✓ Syntax-highlighted code editor with buffer management — Phase 2
- ✓ File editing with undo/redo, save, and unsaved change tracking — Phase 2
- ✓ In-editor search with multi-match highlighting — Phase 2
- ✓ Filesystem watcher for real-time tree updates — Phase 2

### Active

- [ ] Embedded Claude Code CLI running as a subprocess in the chat panel
- [ ] Auto-jump to edited file with changed lines highlighted when Claude makes edits
- [ ] Shortcut to toggle full git-style diff view of Claude's changes
- [ ] Code selection visible to Claude as ambient context
- [ ] Explicit "send selection to Claude" action with prompt
- [ ] Toggleable terminal panel via shortcut for running commands

### Out of Scope

- Vim/Emacs modal editing modes — custom controls designed for this tool
- GUI version — terminal-only
- Own AI backend — leverages Claude Code CLI, not direct API calls
- Plugin/extension system — v1 is a focused tool, not a platform

## Context

- Target audience: terminal-preferring developers and Claude Code users
- Python-based TUI (likely using a library like Textual or similar)
- Claude Code is embedded as a subprocess, inheriting all its capabilities (tools, hooks, MCP servers, CLAUDE.md)
- The editor needs to parse Claude Code's output to detect file changes and trigger the jump-and-highlight behavior
- Syntax highlighting needs to support common languages out of the box

## Constraints

- **Runtime**: Python — user preference, good TUI library ecosystem
- **Claude integration**: Must embed actual Claude Code CLI process, not reimplement its features
- **Environment**: Terminal-based, must work in standard terminal emulators (iTerm2, Alacritty, kitty, etc.)
- **Keybindings**: Custom-designed for this tool's specific workflows

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Embed Claude Code CLI rather than use API directly | Inherits all Claude Code features (tools, hooks, MCP) without reimplementing | — Pending |
| Python for implementation | User preference, strong TUI library ecosystem (Textual, etc.) | ✓ Good |
| Custom keybindings over nano/vim conventions | Controls should be designed around the unique editor+AI+terminal workflow | ✓ Good |
| Jump-and-highlight as default diff UX | Minimal disruption; full diff available via shortcut when needed | — Pending |
| Ctrl+letter over Ctrl+number for panel shortcuts | Ctrl+number unreliable across terminals; Ctrl+b/e/r as primary, Ctrl+1/2/3 as secondary | ✓ Good |
| Textual 8.1.1 with fr-unit CSS layout | Automatic redistribution on panel toggle, responsive resize | ✓ Good |

---
*Last updated: 2026-03-22 after Phase 2 completion*
