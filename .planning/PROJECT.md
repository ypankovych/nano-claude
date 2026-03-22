# nano-claude

## What This Is

A terminal-native IDE that embeds Claude Code as a first-class panel alongside a code editor, file tree, and terminal. Built for developers who love Claude Code but are tired of switching between terminal and a separate editor to read, review, and navigate code. One terminal window, everything in view.

## Core Value

Eliminate context switching between Claude Code and your editor — see Claude's changes the moment they happen, and let Claude see what you're looking at.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Split-panel TUI with file tree, code editor, Claude Code chat, and toggleable terminal
- [ ] Syntax-highlighted code editor with custom keybindings
- [ ] Embedded Claude Code CLI running as a subprocess in the chat panel
- [ ] File tree navigation on the left panel
- [ ] Auto-jump to edited file with changed lines highlighted when Claude makes edits
- [ ] Shortcut to toggle full git-style diff view of Claude's changes
- [ ] Code selection visible to Claude as ambient context
- [ ] Explicit "send selection to Claude" action with prompt
- [ ] Toggleable terminal panel via shortcut for running commands
- [ ] Panel resizing and layout management

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
| Python for implementation | User preference, strong TUI library ecosystem (Textual, etc.) | — Pending |
| Custom keybindings over nano/vim conventions | Controls should be designed around the unique editor+AI+terminal workflow | — Pending |
| Jump-and-highlight as default diff UX | Minimal disruption; full diff available via shortcut when needed | — Pending |

---
*Last updated: 2026-03-22 after initialization*
