# Phase 3: Claude Code Integration - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the chat placeholder with a real embedded Claude Code session. The right panel runs the actual `claude` CLI as a PTY subprocess — full fidelity, same rendering and interaction as standalone Claude Code. Users type prompts directly into the PTY. Status and token info are parsed from PTY output and displayed in the app's status bar.

</domain>

<decisions>
## Implementation Decisions

### Chat Panel = Real Claude Code PTY
- The chat panel embeds the actual `claude` CLI running in a pseudo-terminal (PTY) — NOT a custom chat UI
- Users see Claude Code's native interface: its prompts, markdown rendering, tool use output, permission prompts, everything
- Users type directly into the PTY — no separate input bar, no custom message handling
- This means Claude Code inherits all its features automatically: tools, hooks, MCP servers, CLAUDE.md, slash commands, permission system (CLAUDE-02 satisfied by design)
- Claude Code auto-starts on app launch (carried forward from Phase 1 decision)

### Permissions
- Claude Code's built-in permission prompts appear natively in the PTY — no extra UI layer needed
- Users interact with permission prompts directly in the PTY, same as they would in a standalone terminal

### Status Indicator
- Parse the PTY output stream for status patterns (spinner characters, "Thinking...", tool use markers) and reflect Claude's state in the app's bottom status bar
- States: idle, thinking, writing code, waiting for permission
- This provides visibility even when the chat panel isn't focused

### Token & Cost Display
- Parse Claude Code's token/cost output from the PTY stream (shown at end of responses)
- Display in the app's bottom status bar alongside the status indicator
- Format: compact (e.g., "12.3k tokens · $0.04")

### Error Handling
- If the Claude Code process crashes or exits: show the error in the chat panel + offer a "Restart Claude" action (shortcut to respawn)
- Do NOT auto-restart — user should see what happened
- If `claude` CLI isn't installed or not on PATH: launch app normally, editor and tree work, chat panel shows "Claude Code not found" with install instructions
- Graceful degradation — the app is still useful as a code editor without Claude

### Claude's Discretion
- Exact PTY library choice (ptyprocess, pyte, or alternative)
- How PTY output is rendered into the Textual widget (pyte screen buffer vs raw ANSI passthrough)
- Status bar parsing patterns (regex for spinner, thinking, tool use detection)
- Token/cost parsing regex from Claude Code output
- PTY size (rows/cols) synchronization with the chat panel dimensions
- Restart shortcut key assignment

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Claude Code CLI
- `.planning/research/STACK.md` — claude-agent-sdk 0.1.50, Claude Code CLI reference, stream-json output format
- `.planning/research/ARCHITECTURE.md` — Claude bridge component design, subprocess management patterns
- `.planning/research/PITFALLS.md` — PTY + asyncio integration concerns, SDK alpha stability, subprocess lifecycle

### Phase 1 & 2 Implementation
- `nano_claude/panels/chat.py` — Current ChatPanel placeholder to replace
- `nano_claude/panels/base.py` — BasePanel base class
- `nano_claude/app.py` — NanoClaudeApp with existing keybindings, Footer status bar
- `nano_claude/services/file_watcher.py` — Example of Textual Worker pattern for async services

### Requirements
- `.planning/REQUIREMENTS.md` — CLAUDE-01 through CLAUDE-05

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BasePanel(Vertical)` — ChatPanel extends this, provides border + focus-within CSS
- `FileWatcherService` — Pattern for running async background services in Textual Workers
- `NanoClaudeApp.BINDINGS` — All bindings use `Binding(key, action, id=..., priority=True)` pattern
- `Footer` widget — Already used for key hints, can be extended for status/cost display

### Established Patterns
- Panels extend BasePanel, override `compose()` to yield their widgets
- Async services run via `self.run_worker()` in app's `on_mount`
- App-level handlers coordinate between panels (e.g., `on_directory_tree_file_selected`)
- Config constants live in `nano_claude/config/settings.py`

### Integration Points
- `ChatPanel.compose()` — Replace Static placeholder with PTY terminal widget
- `NanoClaudeApp.on_mount()` — Start Claude Code subprocess here
- `Footer` / status bar area — Add Claude status indicator and token/cost display
- PTY output → file change events: Phase 4 will need to detect when Claude edits files from this PTY output

</code_context>

<specifics>
## Specific Ideas

- The chat panel should feel like you're running `claude` in a terminal pane — not a custom chat app
- This is the same PTY embedding challenge as Phase 6 (terminal panel), but specific to the `claude` CLI
- The PTY approach means CLAUDE-02 (inherits all features) is automatically satisfied — no reimplementation needed
- Status bar info (thinking/idle/tokens) gives the user awareness without needing to look at the chat panel

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-claude-code-integration*
*Context gathered: 2026-03-22*
