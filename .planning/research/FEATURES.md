# Feature Research

**Domain:** Terminal-native IDE with embedded AI agent (Claude Code)
**Researched:** 2026-03-22
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete. Any terminal code editor shipping without these will be dismissed immediately.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Syntax-highlighted code viewer/editor | Every code editor has this since the 1990s. Without it, users cannot read code. | MEDIUM | Textual's `TextArea.code_editor()` provides this via tree-sitter. Supports 90+ languages out of the box. Need to install `textual[syntax]` extras. |
| File tree navigation | Users expect to browse project structure visually. VS Code, Helix, Neovim all have this. | LOW | Textual ships `DirectoryTree` widget with async loading. Textual even has a `code_browser.py` example combining DirectoryTree + TextArea. |
| Split-panel layout | The entire value proposition requires seeing Claude + editor + files simultaneously. | MEDIUM | Textual's CSS-based layout system handles docking, horizontal/vertical splits, and responsive resizing. This is the structural backbone. |
| Embedded Claude Code subprocess | The product IS this. Without a working Claude Code session, there is no product. | HIGH | Must spawn Claude Code CLI as a subprocess, capture stream-json output for real-time display, and handle permission prompts. This is the hardest table-stakes feature. |
| Basic text editing (undo/redo, copy/paste, find) | Micro, nano, and every editor have these. Users will try to edit files. | LOW | Textual TextArea provides undo/redo, clipboard, and basic editing natively. Search/replace needs custom implementation on top. |
| Keyboard-driven navigation | Terminal users expect keyboard shortcuts for everything. Mouse-optional. | MEDIUM | Must design a coherent keybinding system covering panel switching, file navigation, editor actions, and Claude interaction. Custom bindings (not vim/emacs). |
| Line numbers | Every code editor shows line numbers. Claude references line numbers in its output. | LOW | Built into `TextArea.code_editor()` constructor. Enabled by default. |
| Terminal panel | Developers need to run commands (tests, builds, git). Cannot force them to leave the app. | HIGH | Textual does not have a built-in terminal emulator widget. Need to embed a PTY (pseudo-terminal) - likely using `pyte` or similar library. This is a significant implementation challenge. |
| Panel resizing | Users want control over how much screen real estate each panel gets. | LOW | Textual supports CSS-based sizing. Can add drag-to-resize or keyboard shortcuts for panel size adjustment. |
| Responsive to terminal size | Must work in different terminal sizes (80x24 minimum up to ultrawide). | LOW | Textual handles terminal resize events natively. Need to design layouts that degrade gracefully at small sizes (collapse panels). |
| File saving | Users editing files expect to save them. | LOW | Write buffer contents to disk on Ctrl+S or equivalent. Standard file I/O. |

### Differentiators (Competitive Advantage)

These are what make nano-claude worth using over tmux+editor+Claude Code in separate panes. The core value is eliminating context switching -- these features must reinforce that.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Auto-jump to edited file on Claude changes** | THE killer feature. When Claude edits a file, the editor automatically opens it and highlights changed lines. No manual navigation needed. Zero context switch. | HIGH | Requires parsing Claude Code's stream-json output for tool_use events (Write/Edit tools), detecting which files changed, loading them in the editor, and computing + displaying change highlights. This is the hardest differentiator but also the most valuable. |
| **Git-style diff view of Claude's changes** | Users want to review what Claude did before accepting. Cursor's accept/reject UX is the gold standard here. A toggleable diff view shows additions (green) and deletions (red). | HIGH | Requires maintaining "before" snapshots of files Claude touches, computing diffs, and rendering side-by-side or unified diff in the TUI. Could use Python's `difflib` for computation but rendering in terminal is complex. |
| **Code selection visible to Claude as ambient context** | Claude can "see" what you're looking at. Selected code appears in Claude's context window without explicit prompting. Eliminates copy-paste workflow. | MEDIUM | Monitor TextArea selection state, format selected code with file path and line numbers, inject into Claude's context. Need to decide: ambient (automatic) vs explicit (user triggers). Ambient is more magical but could waste tokens. |
| **Send selection to Claude with prompt** | Select code, hit shortcut, type "refactor this" -- Claude gets the selection + prompt. Cursor's Cmd+K inline edit pattern. | LOW | Compose a prompt from selection metadata (file, lines, content) + user input, pipe to Claude subprocess stdin. Straightforward once subprocess communication works. |
| **Claude output as rich TUI content** | Claude's responses rendered with markdown formatting, syntax-highlighted code blocks, and clear visual structure -- not raw terminal text. | MEDIUM | Parse Claude's stream-json output, render markdown with Rich/Textual markup. Code blocks get syntax highlighting matching the editor theme. Much better than raw Claude CLI output. |
| **File change detection (filesystem watcher)** | When Claude (or git, or external tools) modify files, the editor auto-reloads. No stale buffers. | MEDIUM | Use `watchfiles` (Python) or `watchdog` for cross-platform fs events. macOS uses FSEvents, Linux uses inotify. Must handle the case where Claude's subprocess edits files that are currently open in the editor. |
| **Session persistence** | Resume where you left off. Claude conversation history + open files + panel layout preserved. | MEDIUM | Claude Code already persists conversations. Need to save/restore editor state: open files, cursor positions, panel layout. Store in `.nano-claude/` project directory. |
| **Smart status indicator** | Visual indicator showing Claude's state: thinking, waiting for permission, writing code, idle. Similar to agent-deck's smart status detection. | LOW | Parse stream-json events to determine state. Display in status bar or panel header. Simple state machine: idle -> thinking -> tool_use -> waiting_permission -> idle. |
| **Token/cost display** | Show token usage and cost for current session. Developers on metered plans care about this. | LOW | Extract from Claude Code's stream-json output (usage field, cost_usd field). Display in status bar. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Vim/Emacs modal editing | Power users want their muscle memory | Doubles keybinding complexity. Creates two UX paradigms to maintain. Helix found that "less configuration, more editing" wins adoption. The tool's unique value is the AI integration, not text editing efficiency. | Custom keybindings designed around the editor+AI+terminal workflow. Optimize for the common actions in THIS tool (send to Claude, review diff, navigate changes) not generic text editing speed. |
| Plugin/extension system | Users want to customize everything | Massively increases surface area. VS Code's extension model took years to stabilize. Zed still struggles with extension parity. A v1 plugin system will be half-baked and create maintenance burden. | Ship a focused, opinionated tool. If users need plugins, they should use Neovim + Claude Code separately. Revisit in v2 if there's demand. |
| Direct API calls (bypass Claude Code CLI) | Lower latency, more control over prompts | Loses ALL of Claude Code's features: tools, hooks, MCP servers, CLAUDE.md, slash commands, permission system, extended thinking. Reimplementing even 20% of this is months of work. | Embed the real Claude Code CLI. Accept its UX constraints. The --output-format stream-json flag gives sufficient programmatic control. |
| Multi-model support (GPT, Gemini, etc.) | "What if I want to use a different model?" | Scope explosion. Each model has different capabilities, output formats, and tool-calling patterns. OpenCode supports 8+ providers and the complexity is enormous. | Claude Code is the product. It supports Opus, Sonnet, and Haiku model selection already. If users want other models, they should use OpenCode or Aider. |
| Real-time collaboration (multiplayer editing) | Zed has it, Google Docs has it | Enormous complexity (CRDTs, conflict resolution, networking). Irrelevant to the core use case of a single developer working with AI. | Not applicable. This is a single-user tool. Pair programming happens through screen sharing or separate sessions. |
| LSP integration (autocomplete, go-to-definition) | "Real" IDEs have this | Significant implementation effort. Each language needs a separate LSP server. Claude Code itself provides better code intelligence through whole-codebase understanding. LSP is a distraction from the AI-first workflow. | Claude IS the language server. "Go to definition" = ask Claude. "What does this function do?" = ask Claude. For users who need LSP, they should use their existing editor. |
| GUI version (Electron/Tauri wrapper) | Broader audience, prettier UI | Terminal-native IS the differentiator. GUI IDEs with AI already exist (Cursor, Windsurf, Zed). There is no gap in the GUI market. The gap is in the terminal. | Stay terminal-only. The target audience explicitly prefers terminals. |
| Auto-accept Claude's changes | "I trust Claude, just apply everything" | Removes the review step that catches errors. Cursor users reported bugs when auto-accept was introduced. Code review is not overhead -- it's the developer's job. | Default to showing changes with easy accept/reject. Offer a "YOLO mode" flag for experienced users who want auto-accept, but don't make it the default. |
| Inline AI autocomplete (Copilot-style) | Every AI editor has tab-complete | Requires a separate, fast model for completions (not Claude Code's agentic model). Latency requirements are <100ms. Would need direct API integration, contradicting the "embed Claude Code CLI" architecture. | Claude Code's agentic approach (ask -> review -> accept) is fundamentally different from inline autocomplete. Don't try to be Copilot. Let Claude do whole-function and whole-file edits through the chat panel. |

## Feature Dependencies

```
[Split-panel layout]
    |-- requires --> [Panel resizing]
    |-- requires --> [Keyboard-driven navigation]
    |-- contains --> [File tree navigation]
    |-- contains --> [Code editor (syntax highlighting, line numbers)]
    |-- contains --> [Claude Code panel (subprocess)]
    |-- contains --> [Terminal panel]

[Embedded Claude Code subprocess]
    |-- enables --> [Auto-jump to edited file]
    |-- enables --> [Git-style diff view]
    |-- enables --> [Smart status indicator]
    |-- enables --> [Token/cost display]
    |-- enables --> [Claude output as rich TUI content]

[Auto-jump to edited file]
    |-- requires --> [Embedded Claude Code subprocess] (stream-json parsing)
    |-- requires --> [Code editor] (file loading, highlight rendering)
    |-- requires --> [File change detection] (filesystem watcher as fallback)

[Git-style diff view]
    |-- requires --> [Auto-jump to edited file] (knows which files changed)
    |-- requires --> [Code editor] (renders diff content)

[Send selection to Claude]
    |-- requires --> [Code editor] (selection state)
    |-- requires --> [Embedded Claude Code subprocess] (prompt injection)

[Code selection as ambient context]
    |-- requires --> [Send selection to Claude] (same mechanism, different trigger)
    |-- enhances --> [Embedded Claude Code subprocess]

[Session persistence]
    |-- requires --> [Split-panel layout] (layout state to save)
    |-- requires --> [Code editor] (file/cursor state to save)
    |-- enhances --> [Embedded Claude Code subprocess] (Claude already persists)

[File change detection]
    |-- enhances --> [Code editor] (auto-reload stale buffers)
    |-- enhances --> [Auto-jump to edited file] (fallback detection method)
    |-- enhances --> [File tree navigation] (refresh tree on changes)
```

### Dependency Notes

- **Auto-jump requires Claude subprocess parsing:** The entire auto-jump feature depends on successfully parsing Claude Code's stream-json output to detect file_edit/Write tool invocations. This is the critical path.
- **Diff view requires auto-jump infrastructure:** Diff view builds on auto-jump by adding "before" snapshots. Implement auto-jump first, then layer diff on top.
- **Terminal panel is independent but high-complexity:** The PTY embedding is technically independent of other features but is a significant implementation challenge. Can be deferred to v1.1 if needed -- users can Ctrl+Z to a shell temporarily.
- **Session persistence enhances everything:** It depends on most other features existing first (to have state worth saving), so it naturally comes last.
- **File change detection is a safety net:** Even if stream-json parsing catches most Claude edits, filesystem watching catches edits from external tools, git operations, and edge cases where parsing fails.

## MVP Definition

### Launch With (v1 - Proof of Concept)

The minimum to validate that "Claude Code embedded in an editor" is better than "Claude Code + separate editor."

- [ ] **Split-panel layout with file tree + editor + Claude panel** -- The core visual structure. Without all three visible simultaneously, there is no product.
- [ ] **Syntax-highlighted code editor** -- Must be able to read code comfortably. Textual's TextArea.code_editor() gets us 80% there.
- [ ] **Embedded Claude Code subprocess with stream-json parsing** -- The AI integration backbone. Must send prompts and receive streaming responses.
- [ ] **Auto-jump to edited file with change highlighting** -- THE differentiator. If this doesn't work well, the product has no reason to exist versus tmux.
- [ ] **Keyboard-driven panel navigation** -- Users must be able to switch between panels, navigate files, and interact with Claude without reaching for the mouse.
- [ ] **Basic file editing (open, edit, save)** -- Users will want to make small edits without asking Claude. Undo/redo, basic editing.
- [ ] **File tree browsing and file opening** -- Navigate project structure and open files in the editor.

### Add After Validation (v1.x)

Features to add once the core loop (ask Claude -> see changes -> review -> continue) is proven.

- [ ] **Git-style diff view** -- Add when users report wanting more review detail before accepting changes.
- [ ] **Send selection to Claude** -- Add when users report wanting to direct Claude's attention to specific code.
- [ ] **Terminal panel** -- Add when users report needing to run commands without leaving the app. PTY embedding is complex; may require a dedicated sprint.
- [ ] **Rich Claude output rendering** -- Upgrade from raw text to formatted markdown with syntax-highlighted code blocks.
- [ ] **Smart status indicator** -- Show Claude's state (thinking/writing/waiting) in the status bar.
- [ ] **Token/cost display** -- Surface usage data from stream-json output.
- [ ] **File change detection (filesystem watcher)** -- Add when users report stale buffers after git operations or external edits.
- [ ] **Panel resizing** -- Let users drag or keyboard-resize panels. Important for different workflows and screen sizes.

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Session persistence** -- Save/restore full editor state across sessions. Only matters once people use it daily.
- [ ] **Code selection as ambient context** -- Automatic context injection is powerful but needs careful token management. Research optimal UX first.
- [ ] **Multi-file tabs or buffer list** -- When users work with many files, they'll want tabs or a buffer switcher.
- [ ] **Search across project (grep/ripgrep)** -- Project-wide search. Claude can do this, but sometimes you just want grep.
- [ ] **Git integration (status, blame, log)** -- Visual git info in the editor. Lazygit-style UI could be embedded later.
- [ ] **Configurable keybindings** -- Let users remap keys. Only after the default keybindings are battle-tested.
- [ ] **Theme/color scheme customization** -- Textual supports themes (dracula, monokai, vscode_dark, github_light). Expose selection to users.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Split-panel layout | HIGH | MEDIUM | P1 |
| Syntax-highlighted editor | HIGH | LOW | P1 |
| Embedded Claude Code subprocess | HIGH | HIGH | P1 |
| Auto-jump to edited file | HIGH | HIGH | P1 |
| File tree navigation | HIGH | LOW | P1 |
| Keyboard-driven navigation | HIGH | MEDIUM | P1 |
| Basic file editing | HIGH | LOW | P1 |
| Git-style diff view | HIGH | HIGH | P2 |
| Send selection to Claude | HIGH | LOW | P2 |
| Terminal panel (PTY) | HIGH | HIGH | P2 |
| Rich Claude output rendering | MEDIUM | MEDIUM | P2 |
| Smart status indicator | MEDIUM | LOW | P2 |
| Token/cost display | LOW | LOW | P2 |
| File change detection | MEDIUM | MEDIUM | P2 |
| Panel resizing | MEDIUM | LOW | P2 |
| Session persistence | MEDIUM | MEDIUM | P3 |
| Ambient context from selection | MEDIUM | MEDIUM | P3 |
| Multi-file tabs/buffers | MEDIUM | MEDIUM | P3 |
| Project-wide search | LOW | MEDIUM | P3 |
| Git integration | LOW | HIGH | P3 |
| Configurable keybindings | LOW | MEDIUM | P3 |
| Theme customization | LOW | LOW | P3 |

**Priority key:**
- P1: Must have for launch -- the product does not function without these
- P2: Should have, add in v1.x -- each one noticeably improves the experience
- P3: Nice to have, future consideration -- important for retention but not adoption

## Competitor Feature Analysis

| Feature | Cursor (GUI IDE) | OpenCode (Terminal AI) | Aider (Terminal AI) | Agent-Deck (Session Mgr) | tmux + editor (DIY) | nano-claude (Our Approach) |
|---------|-------------------|------------------------|---------------------|---------------------------|----------------------|----------------------------|
| Code editor | Full VS Code editor | None (external editor) | None (external editor) | None (tmux panes) | Separate tool (vim/helix) | Built-in Textual TextArea |
| AI chat panel | Sidebar chat | Full TUI chat | Terminal chat | Session management only | Separate terminal pane | Integrated panel |
| Auto-jump on AI edit | Inline diff appears automatically | N/A | N/A | N/A | Manual navigation | Auto-jump + highlight |
| Diff review | Inline accept/reject per change | N/A | Shows colored diffs in terminal | N/A | Manual git diff | Toggleable diff view |
| File tree | Full VS Code explorer | N/A | N/A | N/A | Separate tool (ranger/lf) | Built-in DirectoryTree |
| Terminal | Integrated terminal | Is a terminal | Is a terminal | Manages terminals | Is tmux | Embedded PTY panel |
| Selection -> AI | Cmd+K inline edit, Cmd+L chat | N/A | /add files to context | N/A | Copy-paste | Select + shortcut + prompt |
| Multi-model | Yes (many providers) | Yes (8+ providers) | Yes (many providers) | Whatever agent uses | N/A | Claude only (via CLI) |
| Cost tracking | In settings | N/A | Shows costs | Token/cost tracking | N/A | Status bar display |
| Session persistence | VS Code workspace | SQLite sessions | Git commits | Session forking | tmux sessions | Planned v2 |
| Collaboration | N/A | N/A | N/A | Multi-agent orchestration | tmux sharing | N/A (single user) |
| Price | $20/month + AI costs | Free + AI costs | Free + AI costs | Free + AI costs | Free | Free + Claude Code sub |

### Competitive Positioning

**vs. Cursor/Windsurf (GUI IDEs):** nano-claude is NOT competing with these. They serve GUI-preferring developers. nano-claude serves terminal-preferring developers who find Electron-based editors unacceptable. Different audience, no feature parity needed.

**vs. OpenCode/Aider (Terminal AI tools):** These are chat-only -- they have no code editor. You still need a separate editor. nano-claude's differentiator is that the editor IS built in and reacts to AI changes in real-time.

**vs. Agent-Deck (Session manager):** Agent-Deck manages multiple Claude sessions but provides no code editing. It is complementary, not competitive. Agent-Deck could theoretically manage nano-claude sessions.

**vs. tmux + editor + Claude Code (DIY):** This is the REAL competitor. Every terminal developer already does this. nano-claude must be demonstrably better than three separate tmux panes. The auto-jump-on-edit feature is the key advantage -- it eliminates the manual "which file did Claude change? let me find it and open it" workflow.

## Sources

- [OpenCode TUI documentation](https://opencode.ai/docs/tui/)
- [Textual TextArea widget](https://textual.textualize.io/widgets/text_area/)
- [Textual DirectoryTree widget](https://textual.textualize.io/widgets/directory_tree/)
- [Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference)
- [Claude Code output styles](https://code.claude.com/docs/en/output-styles)
- [Claude Code headless mode](https://code.claude.com/docs/en/headless)
- [Helix editor](https://helix-editor.com/)
- [Agent-Deck GitHub](https://github.com/asheshgoplani/agent-deck)
- [Cursor diff discussion](https://forum.cursor.com/t/regression-ai-edits-applying-automatically-without-diff-approval-ui/154887)
- [Windsurf Cascade features](https://windsurf.com/cascade)
- [Claude Code vs Cursor vs Copilot comparison (DEV Community)](https://dev.to/alexcloudstar/claude-code-vs-cursor-vs-github-copilot-the-2026-ai-coding-tool-showdown-53n4)
- [Aider AI pair programming](https://aider.chat/)
- [Zed vs Cursor comparison](https://www.f22labs.com/blogs/zed-vs-cursor-ai-the-ultimate-2025-comparison-guide/)
- [Claude Code IDE integration guide](https://www.eesel.ai/blog/claude-code-ide-integration)
- [Best Claude Code GUI tools 2026](https://nimbalyst.com/blog/best-claude-code-gui-tools-2026/)

---
*Feature research for: Terminal-native IDE with embedded Claude Code*
*Researched: 2026-03-22*
