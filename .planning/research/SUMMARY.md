# Project Research Summary

**Project:** nano-claude (Terminal-native IDE with embedded Claude Code)
**Domain:** Terminal TUI application with embedded AI agent subprocess
**Researched:** 2026-03-22
**Confidence:** HIGH

## Executive Summary

nano-claude is a terminal-native IDE that embeds Claude Code as a first-class citizen inside a multi-panel TUI — not alongside it in tmux. The product's entire value proposition rests on eliminating the "which file did Claude change and where is it?" context-switch that plagues the dominant workflow of tmux + editor + Claude Code in separate panes. Research is unambiguous on the technical approach: Textual 8.1.1 is the only serious Python TUI framework for this task (120 FPS rendering, built-in DirectoryTree, tree-sitter TextArea, CSS layout), and `claude-agent-sdk` with `ClaudeSDKClient` is the only correct integration path for the Claude subprocess (raw subprocess management has well-documented zombie process and hang bugs that the SDK already solves). The architecture follows a message-driven, worker-isolated design where panels never touch each other directly — all coordination happens through Textual's event bus.

The killer differentiator that justifies the product's existence is auto-jump: when Claude edits a file, the editor immediately opens that file and highlights the changed lines. Without this feature working reliably, nano-claude is just a worse version of tmux. Detecting these edits requires a dual strategy — SDK `ToolUseBlock` parsing for instant response, plus `watchfiles` (Rust-backed) as a filesystem safety net that catches Bash-based edits the SDK events miss. This dual detection pattern is non-negotiable and must be designed in from Phase 1, not retrofitted.

The primary technical risks are: (1) event loop blocking during Claude operations — mitigated by running all SDK communication in Textual Workers; (2) TextArea performance degradation on large files due to a known tree-sitter `Query.captures` scaling bug — mitigated by viewport-only highlighting and the fixes in Textual PRs #5642 and #5645; and (3) terminal keybinding collisions across terminal emulators — mitigated by restricting to universally-supported key combos and providing a command palette fallback. All three must be addressed architecturally from Phase 1, not as post-launch polish.

## Key Findings

### Recommended Stack

The stack is fully determined with high confidence. Textual 8.1.1 provides the TUI framework, CSS layout engine, DirectoryTree widget, and tree-sitter-backed TextArea. It is the only serious choice — curses offers 20 FPS and no widgets; prompt_toolkit optimizes for command-line input, not full-screen layouts. The `claude-agent-sdk` 0.1.50 manages the Claude Code subprocess with typed message objects, streaming, interrupt support, and session management; it replaces the deprecated `claude-code-sdk` and avoids direct subprocess management that causes zombie processes. The `tree-sitter-language-pack` 1.0.0 is the actively maintained successor to the abandoned `tree-sitter-languages`, providing 170+ pre-compiled grammars with Python 3.12+ support. For filesystem watching, `watchfiles` 1.1.1 (Rust-backed, asyncio-native) beats `watchdog` (threaded, inconsistent debouncing). The terminal panel uses `ptyprocess` + `pyte` via a custom widget rather than `textual-terminal` (unmaintained, LGPL-3, described as "extremely slow" by the Textual maintainer). Project management uses `uv` (10-100x faster than pip, PEP 621 native).

**Core technologies:**
- `textual 8.1.1`: TUI framework, CSS layout, all built-in widgets — the only serious choice for Python TUI
- `claude-agent-sdk 0.1.50`: Claude subprocess lifecycle, typed streaming messages, interrupt, session resume — use `ClaudeSDKClient`, never raw subprocess
- `tree-sitter + tree-sitter-language-pack 1.0.0`: Incremental syntax parsing for the editor — critical for live editing performance on real-world files
- `watchfiles 1.1.1`: Rust-backed async filesystem watcher — catches file changes that SDK tool events miss (Bash-based edits)
- `ptyprocess 0.7.0 + pyte 0.8.2`: PTY management and VT100 emulation for the terminal panel only (not for Claude)
- `click 8.1.x`: CLI entry point — lighter than typer with no Rich version conflicts
- `uv 0.10.x`: Package and build management — modern standard, dramatically faster than pip

### Expected Features

The feature landscape is clear. The real competitive axis is not "does it have a file tree" but "does it eliminate the context-switch when Claude edits files." nano-claude's actual competitor is the tmux+editor+Claude setup that every terminal developer already uses — not Cursor or Windsurf, which serve a different audience entirely.

**Must have (table stakes for v1):**
- Split-panel layout (file tree + editor + Claude chat visible simultaneously) — the visual structure is the product
- Syntax-highlighted code editor with line numbers — table stakes for any code editor since the 1990s
- Embedded Claude Code subprocess with streaming display — the AI integration backbone
- Auto-jump to edited file with change highlighting — THE differentiator; without this, nano-claude loses to tmux
- File tree navigation — users must browse project structure without leaving the app
- Keyboard-driven panel navigation — terminal users expect keyboard-first control
- Basic file editing (open, edit, save, undo/redo) — users will make small edits without asking Claude

**Should have (v1.x, add after core loop is validated):**
- Git-style diff view of Claude's changes — enables accept/reject review workflow (Cursor's gold standard)
- Send selection to Claude with prompt — eliminates copy-paste when directing Claude's attention
- Terminal panel (PTY embedded) — developers need to run commands without leaving the app
- Rich Claude output rendering (markdown + syntax-highlighted code blocks) — much better than raw text
- Smart status indicator (thinking/writing/waiting states) — prevents users from sending duplicate prompts
- Token/cost display in status bar — metered API users care about this
- File change detection via filesystem watcher — prevents stale buffers after git ops and external edits
- Panel resizing — keyboard or drag resize for workflow customization

**Defer (v2+):**
- Session persistence (save/restore full editor state) — only matters after daily use is established
- Code selection as ambient context — needs careful token management research before implementing
- Multi-file tabs/buffer list, project-wide search, git integration, configurable keybindings, theme customization

**Anti-features to explicitly reject:** vim/emacs modal editing (doubles keybinding complexity without matching the tool's value), plugin system (scope explosion — a v1 plugin system will be half-baked), direct Anthropic API (loses all Claude Code features: tools, hooks, MCP, CLAUDE.md), multi-model support (scope explosion), LSP integration (Claude is the language server), inline autocomplete (requires separate fast model and different architecture).

### Architecture Approach

The architecture follows a message-driven, worker-isolated pattern. Five major UI panels communicate exclusively through Textual's message system — no panel holds a reference to another panel. The App Shell is the only coordinator. All Claude SDK interaction runs in Worker threads; widget updates from workers use `post_message` (thread-safe) or `call_from_thread()`. State lives on the App as reactive attributes; no external state management library is needed. The project structure separates `panels/`, `bridge/`, `services/`, `keybindings/`, and `config/` into clear module boundaries to allow independent development and testing of each component.

**Major components:**
1. **App Shell** (`app.py`, `styles.tcss`) — mounts panels, owns CSS layout, routes all messages, manages focus transitions
2. **Claude Code Bridge** (`bridge/`) — ClaudeSDKClient lifecycle, streaming message parsing, file edit detection from ToolUseBlocks
3. **File Tree Panel** (`panels/file_tree.py`) — DirectoryTree wrapper with .gitignore filtering and file selection events
4. **Code Editor Panel** (`panels/editor.py`) — TextArea.code_editor with diff gutter, jump-to-line, change highlighting
5. **Claude Chat Panel** (`panels/chat.py`) — RichLog output with markdown rendering, Input widget for user prompts
6. **Terminal Panel** (`panels/terminal.py`) — toggleable PTY panel using ptyprocess + pyte (custom widget, not textual-terminal)
7. **File Watcher Service** (`services/file_watcher.py`) — watchfiles in a Textual Worker, debounced change events (100-500ms window to survive git checkout/npm install storms)
8. **Diff Service** (`services/diff.py`) — before/after snapshots, difflib computation, Worker-threaded for large files

### Critical Pitfalls

1. **Raw subprocess instead of claude-agent-sdk** — Spawning `claude -p` via Popen causes zombie processes, hanging pipes, and missing streaming events (confirmed in anthropics/claude-code#18666, #24594). Use `ClaudeSDKClient` from day one. This is the most catastrophic architectural mistake (HIGH recovery cost — requires rewriting the entire integration layer).

2. **Blocking the Textual event loop** — Any synchronous call or `await` in a message handler without a Worker freezes the entire UI. All SDK communication must run in Textual Workers. Never use `time.sleep()`; use `await asyncio.sleep()`. Do not use `break` inside `async for message in client.receive_response()` — the SDK explicitly warns this causes asyncio cleanup issues; use a flag variable instead.

3. **TextArea performance on large files** — The tree-sitter `Query.captures` method has known quadratic scaling; files over 1,000 lines become unresponsive without mitigation. Requires viewport-only highlighting (50-line blocks), `Tree.edit()` incremental parsing, and Query object reuse (single construction at init, never per-keystroke). Profile with 2,000-10,000 line files during Phase 2 before assuming the Textual PR fixes (#5642, #5645) are sufficient.

4. **Detecting only Write/Edit tool events for file changes** — Claude routinely edits files via Bash (`sed`, `echo >>`, `cat <<EOF >`), which generates no Write/Edit ToolUseBlock. Tool event parsing must be a fast hint only; `watchfiles` filesystem watcher is the source of truth for all edits. Implement dual detection from the start, not as an afterthought.

5. **Missing `setting_sources=["project"]` in ClaudeAgentOptions** — SDK defaults load no filesystem settings, making embedded Claude ignore CLAUDE.md files, MCP servers, and project-level permissions. This is a one-line fix that must be in the first working integration. Without it, embedded Claude behaves differently from the standalone CLI, which breaks user trust immediately.

6. **Terminal keybinding collisions** — Apple Terminal does not pass Ctrl+function keys; macOS intercepts Ctrl+PageUp/Down; Kitty reserves Ctrl+Shift+Fn by default. Only universally safe keys are: Ctrl+letter (a-z), unmodified F1-F12, Tab, Enter, Escape, arrow keys. Provide a command palette (Ctrl+P) as universal fallback. Define the full keybinding strategy in Phase 1 before users develop muscle memory.

## Implications for Roadmap

The architecture's build-order dependency chain maps directly to phases. The App Shell must exist before anything mounts into it. Core panels can be built in parallel. The Claude Bridge is the most complex single component and gates the killer feature (auto-jump). Cross-panel features layer on top.

### Phase 1: Foundation
**Rationale:** App Shell, CSS layout, and keybinding framework are pre-requisites for everything. Every other component mounts into the shell. The keybinding strategy must be locked early — retrofitting after users develop muscle memory is disruptive — and terminal compatibility must be validated now, not at launch.
**Delivers:** Runnable application skeleton with CSS-driven 3-panel layout, focus management between panels, and a working keybinding system. No AI features yet — the structural backbone that everything else builds into.
**Addresses:** Split-panel layout, keyboard-driven navigation, panel focus switching (all table stakes)
**Avoids:** Key binding collisions (define safe key combos now and test on iTerm2, Alacritty, kitty, Apple Terminal); event loop blocking (establish Worker pattern as the default from day one)

### Phase 2: Core Panels
**Rationale:** File Tree and Code Editor are fully independent of each other and of Claude. They can be built in parallel. Both deliver immediate standalone value (browse files, view code) and are required by Phase 3's auto-jump. TextArea performance must be validated here — not deferred as "optimization."
**Delivers:** Working file tree with async directory loading and .gitignore filtering; working syntax-highlighted code editor with line numbers, basic file editing (undo/redo, save), and file loading from tree selection.
**Uses:** Textual DirectoryTree, TextArea.code_editor, tree-sitter-language-pack, watchfiles (for external file reload)
**Implements:** File Tree Panel, Code Editor Panel, FileSystem service, File Watcher service
**Avoids:** TextArea performance trap — profile with 5,000-line files during this phase; implement viewport-only highlighting; create Query objects once in constructor and reuse

### Phase 3: Claude Integration
**Rationale:** The Claude Code Bridge is the architectural centerpiece. It must be built after the App Shell (to post messages to) and after the Editor panel (to jump to files in Phase 4). This phase produces the first working AI interaction loop and is the product's core value.
**Delivers:** Functional Claude Code subprocess via ClaudeSDKClient; streaming chat display in the Claude Chat Panel with token-by-token rendering; prompt sending; smart status indicator (thinking/executing tool/waiting); token/cost display.
**Uses:** claude-agent-sdk ClaudeSDKClient with `setting_sources=["project"]` and `include_partial_messages=True`; RichLog + Input widgets; Textual Workers
**Implements:** Claude Code Bridge (client.py, messages.py), Claude Chat Panel
**Avoids:** Raw subprocess (use SDK exclusively); event loop blocking (Worker isolation throughout); missing CLAUDE.md (always set `setting_sources=["project"]`); buffering entire response before display (stream tokens immediately as they arrive)

### Phase 4: The Killer Feature — Auto-Jump and Change Detection
**Rationale:** This phase is the primary reason nano-claude exists. It requires Phase 3 (to know when Claude acts) and Phase 2 (editor must exist to jump to). The dual detection strategy (SDK ToolUseBlock hints + watchfiles source of truth) must be implemented together — SDK-only detection misses Bash-based edits, watchfiles-only detection has FSEvents latency on macOS.
**Delivers:** When Claude edits any file — via Write, Edit, or Bash tools — the editor automatically opens that file and highlights the changed lines. This is the concrete proof that nano-claude is better than tmux.
**Uses:** ToolUseBlock parsing from AssistantMessage, watchfiles filesystem watcher, difflib for change computation, navigation stack for "go back" after auto-jump
**Implements:** file_detector.py in bridge/, FileChanged message with changed_lines, EditorPanel.highlight_changes(), EditorPanel.scroll_to_change(), previous file/position stack
**Avoids:** SDK-only detection (misses Bash edits — confirmed by research); polling (event-driven only); replacing editor view without navigation undo (users lose context)

### Phase 5: Expanded Interaction
**Rationale:** Once the core loop (ask Claude -> auto-jump to edited files -> review) is validated with real users, add features that enhance that loop. All are P2 features with clear dependencies on Phase 3-4 infrastructure.
**Delivers:** Git-style diff view (before/after snapshots rendered in editor gutter or side panel); send-selection-to-Claude shortcut (compose prompt from TextArea selection with file path and line numbers); rich Claude output rendering (markdown + syntax-highlighted code blocks in chat panel).
**Implements:** services/diff.py with Worker-threaded difflib computation, diff gutter in EditorPanel, selection-to-prompt composition in ChatPanel
**Avoids:** Rendering diffs synchronously for large files (Worker thread always); exposing raw tool-use JSON in chat (render as human-readable summaries: "Writing to auth.py")

### Phase 6: Terminal Panel
**Rationale:** The terminal panel is high-value but technically independent and the single highest-complexity component. Deferring it to its own phase prevents PTY complexity from blocking Phases 1-5. Users can Ctrl+Z to a shell as a workaround. Start with RichLog+Input (Textual maintainer's recommendation for most cases) and escalate to full PTY only if users demonstrate interactive program needs (vim, htop, ssh).
**Delivers:** Toggleable bottom panel running the user's $SHELL, with ANSI color rendering.
**Uses:** ptyprocess + pyte for full PTY approach; RichLog + Input as simpler fallback
**Implements:** panels/terminal.py with custom widget
**Avoids:** Using textual-terminal library (unmaintained, described as "extremely slow" by maintainer); committing to full PTY complexity before validating simpler approach

### Phase 7: Polish and Persistence
**Rationale:** Session persistence, error recovery, and UX refinements belong after the core feature set is validated by real users. These are P3 features — important for retention but not adoption.
**Delivers:** Session state save/restore (open files, cursor positions, panel layout); error recovery for SDK failures (auth expiry, rate limits, mid-edit interruption with `rewind_files()`); configurable keybindings; improved panel resize UX.
**Implements:** config/settings.py persistence, ClaudeSDKClient interrupt + file checkpointing, keybinding config file

### Phase Ordering Rationale

- App Shell first because it is the literal mounting point for everything else — building panels without it means immediate refactoring.
- File Tree and Editor before Claude Bridge because auto-jump (Phase 4) requires an existing editor; building Bridge before the Editor means Phase 4 design is incomplete.
- Claude Integration (Phase 3) before auto-jump (Phase 4) because auto-jump consumes the message types and ToolUseBlock parsing defined in the Bridge.
- Terminal Panel deferred to Phase 6 because it is independent and technically the riskiest single component; it should not gate the core value loop.
- Persistence last because it requires all the state it preserves to already exist and be stable.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Claude Integration):** The `claude-agent-sdk` is at v0.1.50 (alpha). The exact streaming message structure for `include_partial_messages=True` and the async iteration protocol should be verified against current SDK source before writing the Bridge's message parsing code. A spike is recommended before scoping Phase 3 tasks.
- **Phase 4 (Auto-Jump):** The dual detection strategy has edge cases — MCP server edits, subagent delegation, compressed tool calls, PostToolUse hook behavior. A test matrix covering all edit paths (Write, Edit, Bash sed, Bash echo, MCP) should be built before the phase begins.
- **Phase 6 (Terminal Panel):** PTY + asyncio integration with Textual's event loop is not well-documented. The choice between RichLog+Input and full PTY should be made after attempting the simpler approach, not by assumption.

Phases with well-documented standard patterns (research likely not needed):
- **Phase 1 (Foundation):** Textual App + CSS layout + keybindings is extensively documented with official examples and guides.
- **Phase 2 (Core Panels):** DirectoryTree and TextArea.code_editor are first-class Textual widgets with comprehensive official documentation.
- **Phase 5 (Expanded Interaction):** difflib diff computation and markdown rendering with RichLog are standard patterns with no novel integration challenges.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All libraries verified on PyPI (March 2026); official SDK docs reviewed; alternatives systematically compared with documented rationale for each rejection |
| Features | HIGH | Competitive analysis against Cursor, OpenCode, Aider, Agent-Deck; feature dependency graph mapped; MVP clearly defined; anti-features explicitly argued with reasoning |
| Architecture | HIGH | Backed by official Textual docs, claude-agent-sdk streaming docs, and Toad reference implementation (Will McGugan's AI terminal TUI); message-driven pattern aligns with Textual's own recommendations |
| Pitfalls | HIGH | Pitfalls verified against filed GitHub issues (anthropics/claude-code#18666, #24594; Textual PRs #5642/#5645), official SDK docs (async iteration warning explicitly documented), and maintainer statements |

**Overall confidence:** HIGH

### Gaps to Address

- **SDK streaming protocol details:** The exact shape of `StreamEvent` objects for `include_partial_messages=True` should be cross-checked against current SDK source before writing Bridge message parsing code. The SDK is at v0.1.50 and API changes are possible.
- **Terminal panel approach decision:** The RichLog+Input vs. full PTY choice should be made after attempting the simpler approach in Phase 6. Start simple, escalate only when users demonstrate interactive program needs.
- **TextArea viewport highlighting in practice:** Textual PRs #5642/#5645 add lazy highlighting, but their interaction with large file editing needs profiling in Phase 2 rather than assuming the fixes are sufficient for all use cases.
- **watchfiles latency on macOS FSEvents:** There is a ~1 second FSEvents latency window on macOS where the editor has not yet reflected Claude's Bash-based edit. This UX gap should be measured with real usage and addressed if noticeable.
- **tree-sitter-language-pack via textual[syntax]:** The `textual[syntax]` extra may install the deprecated `tree-sitter-languages` instead of `tree-sitter-language-pack`. Verify during project setup and add explicit dependency if needed.

## Sources

### Primary (HIGH confidence)
- Textual 8.1.1 PyPI + textual.textualize.io docs — TextArea, DirectoryTree, Workers, layout, keybindings, testing
- claude-agent-sdk 0.1.50 PyPI + platform.claude.com docs — ClaudeSDKClient, ClaudeAgentOptions, streaming protocol, message types
- tree-sitter-language-pack 1.0.0 PyPI — grammar coverage, Python 3.12+ support
- watchfiles 1.1.1 PyPI — async API, platform watcher behavior
- Toad (Will McGugan, batrachianai/toad) — reference architecture for AI terminal TUI with Textual

### Secondary (MEDIUM confidence)
- ptyprocess 0.7.0 + pyte 0.8.2 — PTY and VT100 emulation for terminal panel
- click 8.1.x — CLI entry point, Rich version conflict avoidance rationale
- Textual discussion #5461 — maintainer recommendation: RichLog+Input over full terminal emulation
- Textual PRs #5642 + #5645 — lazy highlighting and background incremental parsing fixes for TextArea

### Tertiary (needs validation)
- anthropics/claude-code#18666, #24594 — zombie process and undocumented stream-json format bugs (filed issues, not official docs)
- opencode#6119 — ANSI rendering memory leak (informs terminal panel risk)
- Textual keybinding wiki — escape sequence limitations across terminal emulators
- blog.bjdean.id.au embedding guide — practical SDK embedding patterns (single author, cross-check against official docs)

---
*Research completed: 2026-03-22*
*Ready for roadmap: yes*
