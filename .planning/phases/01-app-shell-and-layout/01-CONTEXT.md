# Phase 1: App Shell and Layout - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Multi-panel TUI skeleton with focus management and panel resizing. User launches the application and sees a responsive three-panel layout (file tree, code editor, Claude chat) with keyboard-driven navigation. This is the foundation — every other phase mounts into this shell.

</domain>

<decisions>
## Implementation Decisions

### Panel Arrangement
- Default width split: 15% file tree / 50% editor / 35% Claude chat
- File tree is toggleable (hide/show via shortcut) — gives more editor space when browsing isn't needed
- Terminal panel (Phase 6) docks at the bottom as a horizontal split below all panels
- Small terminal collapse order: file tree hides first → editor + chat remain. Then chat hides → editor only. Each panel toggleable via shortcut.
- Layout must accommodate the bottom terminal dock even though it's not implemented until Phase 6

### Focus & Shortcuts
- Panel switching: both direct jump shortcuts (Ctrl+1 = tree, Ctrl+2 = editor, Ctrl+3 = chat, Ctrl+4 = terminal) AND Ctrl+Tab cycling
- Active panel indicated by: colored border + highlighted title bar (both)
- Primary modifier: Ctrl for all app-level shortcuts
- Panel resizing: Ctrl+Plus/Minus to grow/shrink the active panel's width
- File tree toggle: dedicated Ctrl shortcut (Claude picks which key)

### Visual Chrome
- Panel borders: thin single-line box-drawing characters (│ ─) — clean, minimal
- Top bar: app name + currently open file
- Bottom bar: cursor position, Claude status, token count, key hints
- Default color scheme: dark background, light text
- Panel titles: minimal — only the editor panel shows the filename, other panels unlabeled (the top bar provides context)

### Startup Behavior
- Project root: always use current working directory (cwd) — simple, predictable, same as Claude Code
- CLI interface: `nano-claude [optional-path]` — optional path argument to open a specific file or directory
- On launch: auto-open README.md if it exists in project root; if no README, show a welcome greeting with key shortcut reference
- Claude Code subprocess: auto-starts immediately on launch — chat panel is ready to type right away
- All three panels visible immediately on launch

### Claude's Discretion
- Exact Ctrl+key assignments for file tree toggle, diff view toggle, and other non-panel-switch shortcuts
- Welcome greeting content and formatting
- Exact active panel highlight color
- How panel resize increments work (percentage steps vs fixed character widths)
- Minimum panel width thresholds before collapse triggers

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### TUI Framework
- `.planning/research/STACK.md` — Textual 8.1.1 as TUI framework, CSS layout system, widget recommendations
- `.planning/research/ARCHITECTURE.md` — Component boundaries, Textual CSS layout patterns, app shell design

### Known Risks
- `.planning/research/PITFALLS.md` — Terminal keybinding compatibility issues (Ctrl+number unreliable in some terminals), Textual event loop considerations

### Project Context
- `.planning/PROJECT.md` — Core value, constraints, key decisions
- `.planning/REQUIREMENTS.md` — LAYOUT-01 through LAYOUT-04 requirements

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, this is the first phase

### Established Patterns
- None yet — this phase establishes the foundational patterns (app structure, CSS layout, keybinding approach)

### Integration Points
- This phase creates the mounting points for all subsequent phases:
  - Left panel placeholder → Phase 2 mounts DirectoryTree
  - Center panel placeholder → Phase 2 mounts TextArea code editor
  - Right panel placeholder → Phase 3 mounts Claude chat widget
  - Bottom dock area → Phase 6 mounts terminal panel
  - Status bar → Phase 3 adds Claude status indicator, Phase 4 adds change indicators

</code_context>

<specifics>
## Specific Ideas

- Layout should feel like a terminal-native VS Code — panels visible simultaneously, not tabbed
- The three-panel default (tree + editor + chat) is the iconic layout of the product
- Panel collapse behavior mirrors how VS Code sidebar and panel work — toggleable, not permanently removed

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-app-shell-and-layout*
*Context gathered: 2026-03-22*
