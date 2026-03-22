# Pitfalls Research

**Domain:** Terminal-native IDE with embedded Claude Code subprocess (TUI + AI agent)
**Researched:** 2026-03-22
**Confidence:** HIGH (verified against official docs, SDK source, real bug reports)

## Critical Pitfalls

### Pitfall 1: Using Raw Subprocess Instead of the Claude Agent SDK for Python

**What goes wrong:**
Building Claude Code integration by spawning `claude -p --output-format stream-json` as a raw subprocess and parsing stdout manually. This leads to zombie processes on initialization failure, hanging pipes when stdin/stdout buffers fill, duplicate echo from PTY allocation, and inability to interrupt mid-execution. Multiple GitHub issues document this: SDK subprocess hangs on initialize leaving zombie processes at 60-70% CPU (anthropics/claude-code#18666), and `claude -p` hanging when spawned without explicit stdin handling.

**Why it happens:**
The `--output-format stream-json` and `--input-format stream-json` flags look like a clean integration surface. Developers assume they can just pipe JSON in and out. But `--input-format stream-json` is poorly documented (anthropics/claude-code#24594), the initialization handshake can timeout, and managing the subprocess lifecycle (startup, interrupt, cleanup) requires careful orchestration that the SDK already handles.

**How to avoid:**
Use `claude-agent-sdk` Python package with `ClaudeSDKClient` for stateful, continuous sessions. This provides:
- Proper lifecycle management (connect/disconnect)
- Streaming message iteration with typed message objects (`AssistantMessage`, `ToolUseBlock`, `ResultMessage`)
- Built-in interrupt support via `await client.interrupt()`
- Hook system for intercepting tool use events (PreToolUse, PostToolUse)
- Permission callbacks for controlling what Claude can do
- Session resumption via session IDs

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

async with ClaudeSDKClient(options=ClaudeAgentOptions(
    allowed_tools=["Read", "Write", "Edit", "Bash"],
    permission_mode="acceptEdits",
    setting_sources=["project"],  # Load CLAUDE.md
    include_partial_messages=True,  # For streaming tokens
)) as client:
    await client.query("Fix the bug in auth.py")
    async for message in client.receive_response():
        # Typed, structured messages instead of raw JSON parsing
        ...
```

**Warning signs:**
- Writing JSON parsing code for Claude Code output
- Using `subprocess.Popen` or `asyncio.create_subprocess_exec` with `claude` binary directly
- Building custom process lifecycle management (restart on crash, timeout handling)
- Encountering zombie `claude` processes after errors

**Phase to address:**
Phase 1 (Foundation). This is the most fundamental architectural decision. Getting this wrong means rewriting the entire Claude Code integration layer.

---

### Pitfall 2: Blocking the Textual Event Loop with Claude Code Communication

**What goes wrong:**
Claude Code queries can run for minutes (writing files, running tests, multi-step reasoning). If any part of the communication blocks the Textual event loop, the entire UI freezes -- no panel resizing, no scrolling, no keyboard input. The app appears hung even though Claude is working.

**Why it happens:**
Textual runs on Python's asyncio event loop. Even with the SDK, developers make mistakes like:
- Calling `await client.query()` directly in a message handler without a worker
- Using synchronous file I/O while processing Claude's responses
- Forgetting that `time.sleep()` in any handler freezes everything
- Breaking out of `async for message in client.receive_response()` incorrectly (the SDK docs explicitly warn against using `break` in the async iteration as it causes asyncio cleanup issues)

**How to avoid:**
- Run all Claude Code communication in Textual Workers (either `@work` decorator or `run_worker()`)
- Use `call_from_thread()` for any widget updates from worker threads, since most Textual functions are not thread-safe (exception: `post_message` is thread-safe)
- Never use `time.sleep()` anywhere -- use `await asyncio.sleep()` in async contexts
- Let the async iteration over `receive_response()` complete naturally; use a flag variable instead of `break`
- Process streaming tokens incrementally -- update the chat panel as tokens arrive, do not buffer the entire response

**Warning signs:**
- UI becomes unresponsive during Claude operations
- Panel resize or scroll requests queue up and execute in a burst after Claude finishes
- Users cannot cancel/interrupt Claude because keyboard input is not being processed
- Test suite has `time.sleep()` calls to "wait for Claude"

**Phase to address:**
Phase 1-2 (Foundation + Claude Integration). The async architecture must be correct from day one. Retrofitting non-blocking patterns is extremely painful.

---

### Pitfall 3: Textual TextArea Cannot Handle Real-World Source Files

**What goes wrong:**
Textual's built-in `TextArea` widget has quadratic scaling in its syntax highlighting implementation. The `Query.captures` method from tree-sitter scales poorly with line count. Editing a 25,000-line Python file becomes "painfully unresponsive." Performance issues appear as early as 1,000 lines in some languages (LaTeX). Since this is a code editor, users will routinely open files of this size.

**Why it happens:**
The TextArea widget was originally querying the entire syntax tree on every keystroke. While Textual PR #5642 added lazy highlighting in 50-line blocks and PR #5645 added background incremental parsing, these are relatively recent fixes and may not fully solve the problem for all use cases. The fundamental issue is that tree-sitter's Python bindings have a suspected quadratic-or-worse bug in `Query.captures` that becomes the bottleneck at scale.

**How to avoid:**
- Pin Textual to a version that includes PR #5642 and #5645 (lazy highlighting + background parsing)
- Implement viewport-only rendering: only syntax-highlight the lines currently visible on screen, plus a small buffer above/below
- Use tree-sitter's incremental parsing (`Tree.edit()` + reparse) rather than full re-parsing on each edit -- tree-sitter shares unchanged subtrees between old and new parse trees, making updates fast
- Set a file size threshold (e.g., 50,000 lines) where syntax highlighting degrades gracefully to plain text
- Profile early with realistic file sizes (2,000-10,000 lines) -- not just 50-line test files

**Warning signs:**
- Editor feels smooth in demos with small files but lags on real codebases
- Keystroke latency exceeds 50ms on files over 1,000 lines
- Memory usage grows linearly with file size even when only viewing a portion
- Syntax highlighting flickers or partially renders during scrolling

**Phase to address:**
Phase 2-3 (Code Editor). Must be addressed when building the editor panel, not deferred as "optimization."

---

### Pitfall 4: Detecting Claude's File Edits by Parsing Output Instead of Watching the Filesystem

**What goes wrong:**
The project requires "auto-jump to edited file with changed lines highlighted when Claude makes edits." Developers try to detect edits by parsing Claude's tool use events (looking for Write/Edit tool calls in the stream). This is fragile: Claude can edit files via Bash tool (`sed`, `echo >>`), via MCP servers, or via subagent delegation. Parsing tool events misses indirect edits and creates a cat-and-mouse game with Claude's tool repertoire.

**Why it happens:**
The SDK provides structured `ToolUseBlock` messages with tool name and input, making it tempting to pattern-match on `block.name in ["Write", "Edit"]`. This works for the happy path but fails for Bash-based edits, which are common (Claude often uses `sed` for quick fixes or `cat <<EOF > file` for new files).

**How to avoid:**
Use a dual approach:
1. **Primary: Filesystem watcher** (watchdog library) monitoring the project directory for actual file changes. This catches ALL edits regardless of how Claude made them. Use `inotify` on Linux, `FSEvents` on macOS.
2. **Secondary: SDK tool events** as hints for immediate response. When a `ToolUseBlock` with `name="Write"` arrives, you know the file path before the watcher fires, enabling instant jump-to-file. But always confirm with the filesystem.
3. **SDK Hooks**: Use `PostToolUse` hooks to get notified after any tool completes, then check if files changed.

Key consideration: watchdog on macOS uses `FSEvents` which has a ~1 second latency by default. For responsive UX, use the SDK tool events for instant reaction and the watcher as a safety net.

**Warning signs:**
- "Jump to file" works when Claude uses Write but not when it uses Bash
- Files changed by MCP tools do not trigger the highlight behavior
- Users see stale file content in the editor after Claude edits
- Test coverage only covers Write/Edit tool calls, not Bash-based edits

**Phase to address:**
Phase 2-3 (Claude Integration + Editor). Must be architecturally planned when building the file edit detection system.

---

### Pitfall 5: Key Binding Collisions Between Terminal, Textual, and Custom Bindings

**What goes wrong:**
Key combinations that work in development break in different terminal emulators. Ctrl+number keys do nothing in several terminals. Shift+PageUp/PageDown trigger scrollback instead of reaching the app. Ctrl+function key combinations are intercepted by macOS. The app's custom keybindings fight with the terminal emulator's built-in shortcuts, creating a confusing experience where the same key does different things depending on which terminal you use.

**Why it happens:**
Textual can only support key combinations that the terminal emulator passes through. This varies dramatically:
- Apple Terminal: no Ctrl+function key combination works at all
- Kitty: Ctrl+Shift+Fn reserved by default
- rio: function keys emit Unicode instead of escape sequences
- macOS: Ctrl+PageUp/PageDown scroll terminal buffers
- Windows Terminal: Ctrl+Shift+Number opens new tabs
There is no way to have non-conflicting escape codes for Alt+letter, Ctrl+letter, Ctrl+Alt+letter across all terminals.

**How to avoid:**
- Only use universally-supported key combinations: unmodified letters/numbers, Ctrl+letter (a-z), basic arrow keys, Tab, Enter, Escape, unmodified F1-F12
- Avoid: Ctrl+number, Ctrl+function keys, Shift+PageUp/Down, any triple-modifier combo
- Make all keybindings configurable in a config file
- Provide a command palette (Ctrl+P or similar) as the universal fallback for all actions
- Test on at least: iTerm2, Alacritty, kitty, Apple Terminal, WezTerm before any release
- Document which terminals are fully supported vs. partially supported

**Warning signs:**
- Keybinding works on your terminal but users report "nothing happens"
- Bug reports are terminal-specific ("X doesn't work in kitty but works in iTerm2")
- Users cannot discover how to perform basic actions
- Keybinding documentation has many asterisks and caveats

**Phase to address:**
Phase 1-2 (Foundation + Layout). Define the keybinding strategy early. Changing keybindings after users develop muscle memory is extremely disruptive.

---

### Pitfall 6: Not Loading CLAUDE.md and Project Settings When Using the SDK

**What goes wrong:**
Claude Code's power comes from project-level context: CLAUDE.md files, MCP server configurations, custom hooks, and permission settings. When using the Python Agent SDK, settings sources default to `None` -- no filesystem settings are loaded. The embedded Claude Code behaves differently from the standalone CLI because it lacks the user's project customizations.

**Why it happens:**
The SDK documentation notes this explicitly: "By default, NO filesystem settings are loaded." Developers who test with `claude` in the terminal see one behavior (with CLAUDE.md loaded), then embed via SDK and get different behavior (without CLAUDE.md). Users who rely heavily on their CLAUDE.md configuration feel like the tool is broken.

**How to avoid:**
Always specify `setting_sources=["project"]` in `ClaudeAgentOptions` to load CLAUDE.md files. Additionally:
- Pass the correct working directory so Claude resolves project-relative paths correctly
- Test the embedded integration in a project that has a CLAUDE.md file
- Consider exposing a UI indicator showing which CLAUDE.md files were loaded

**Warning signs:**
- Claude in the embedded IDE gives different answers than Claude in the terminal for the same project
- Users report "my custom instructions are being ignored"
- MCP servers that work in standalone Claude Code fail in the embedded version
- Claude does not respect project-specific tool restrictions

**Phase to address:**
Phase 2 (Claude Integration). Must be correct from the first working integration.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoding panel layout ratios | Fast UI prototyping | Users cannot resize panels, fixed ratios break on different terminal sizes | Never -- implement resize from day one |
| Buffering entire Claude response before displaying | Simpler rendering logic | Users stare at blank screen for 30+ seconds on long responses; defeats the streaming UX | Never -- streaming display is table stakes |
| Polling filesystem for changes instead of using watchers | No dependency on watchdog/platform-specific APIs | CPU waste, missed rapid edits, 1-5 second delay on detecting changes | Only in early prototype, replace by Phase 3 |
| Skipping undo/redo in the editor | Avoid command pattern complexity | Users lose work on accidental edits; trust in the editor collapses | Only in MVP if editor is read-only |
| Single-threaded Claude communication | Simpler code, no concurrency bugs | UI freezes during Claude operations; users think app crashed | Never once Claude integration exists |
| No error handling for SDK connection failures | Less code to write | App crashes on network issues, auth failures, or Claude Code updates | Never |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Claude Agent SDK | Using `query()` for chat (no session state) | Use `ClaudeSDKClient` for persistent sessions with context |
| Claude Agent SDK | Breaking out of `async for` iteration with `break` | Let iteration complete; use flags to skip unwanted messages |
| Claude Agent SDK | Not handling `ResultMessage` | Always process `ResultMessage` for cost tracking, error detection, session ID |
| Filesystem watcher | Watching entire home directory | Watch only the project root; use ignore patterns for node_modules, .git, etc. |
| Tree-sitter | Re-creating `Query` objects on each keystroke | Create once in constructor; reuse across edits (94% performance improvement) |
| Tree-sitter | Full re-parse on each edit | Use `Tree.edit()` + incremental reparse; only changed ranges are processed |
| Terminal rendering | Assuming Unicode emoji widths are consistent | Different terminals disagree on character widths; avoid emoji in UI chrome |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Full syntax tree query per edit | Keystroke latency >100ms | Viewport-only highlighting in 50-line blocks | >1,000 lines (language dependent) |
| Storing full file content in memory per open tab | RAM usage grows with file count | Memory-mapped files or lazy loading; only keep visible portion + buffer in memory | >10 open files or files >1MB |
| Re-rendering entire chat panel on each token | Flicker, CPU spike during streaming | Append-only rendering; only update the last message block | Claude responses >500 tokens |
| Creating new NamedTuple per highlight range | Syntax highlighting bottleneck | Use plain tuples (NamedTuple.__new__ overhead was a known Textual perf issue) | >500 highlight ranges per viewport |
| Unthrottled filesystem watcher events | Event storm during git operations | Debounce watcher events (100-500ms window); batch related changes | Any `git checkout`, `npm install`, bulk file operations |
| Accumulating conversation history in memory | Memory grows over long sessions | Use SDK session management; compact older messages; rely on session resumption | >50 conversation turns |

## Security Mistakes

Domain-specific security issues beyond general practices.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Using `permission_mode="bypassPermissions"` for convenience | Claude can execute any shell command, delete files, make network requests without user consent | Use `"acceptEdits"` for file operations; require explicit approval for Bash commands via `can_use_tool` callback |
| Not sanitizing file paths from Claude's tool events before displaying in UI | Path traversal display confusion (showing files outside project) | Validate all file paths are within the project root before displaying or opening |
| Passing raw user input as Claude prompts without context boundaries | Prompt injection if user pastes malicious content that Claude interprets as instructions | Wrap user selections in clear delimiters; use `append_system_prompt` for instructions separate from user content |
| Exposing SDK session IDs in UI or logs | Session replay or context leakage if logs are shared | Keep session IDs internal; never display in user-facing panels |
| Unix socket access in sandbox settings | Docker socket access bypasses all containerization | Never grant Unix socket access unless explicitly configured by the user |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No visual indicator that Claude is working | User sends duplicate prompts thinking the first one failed | Show a clear "thinking..." / "executing tool X..." status with elapsed time |
| Showing raw tool use JSON in the chat panel | Users see `{"tool_name": "Write", "input": {...}}` instead of human-readable summaries | Render tool uses as collapsible cards: "Writing to auth.py" with expandable details |
| Jump-to-file replaces current editor view without undo | User loses their scroll position and context when Claude edits a different file | Remember previous file/position; provide "go back" navigation (breadcrumb or stack) |
| Modal dialogs for permission prompts | Blocks the entire UI; user cannot review code while deciding on a permission | Inline permission prompts in the chat panel; allow reviewing other panels while deciding |
| No cost/token visibility | Users unknowingly burn through API credits on long sessions | Show running cost in the status bar; alert on unusually expensive operations |
| Chat panel does not scroll to bottom on new messages | User misses Claude's responses, thinks tool is broken | Auto-scroll when user is at/near bottom; do NOT auto-scroll if user has scrolled up to review |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Chat panel:** Often missing scroll-to-bottom on new messages -- verify auto-scroll works AND that manual scroll-up is preserved
- [ ] **File edit detection:** Often missing Bash-based edits -- verify `sed`, `echo >>`, `cat <<EOF >` all trigger jump-to-file
- [ ] **Syntax highlighting:** Often missing edge cases -- verify with files >2,000 lines, mixed-language files (HTML with embedded JS), and files with Unicode
- [ ] **Panel resize:** Often missing minimum size constraints -- verify panels cannot be collapsed to 0 width/height, breaking layout recovery
- [ ] **Claude interruption:** Often missing cleanup -- verify interrupting Claude mid-edit does not leave files in a partial state (use SDK's `enable_file_checkpointing=True` + `rewind_files()`)
- [ ] **Terminal panel:** Often missing proper PTY setup -- verify terminal panel handles ANSI colors, cursor positioning, and interactive commands (vim, less, top)
- [ ] **Session persistence:** Often missing resume -- verify closing and reopening the app can continue from the last conversation
- [ ] **Error states:** Often missing recovery -- verify what happens when Claude Code crashes, API key expires, or rate limit is hit mid-conversation
- [ ] **Multi-file edits:** Often missing atomicity -- verify that when Claude edits 5 files, the editor shows all 5 changes, not just the last one

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Raw subprocess instead of SDK | HIGH | Rewrite entire Claude integration layer; keep message types/UI rendering intact |
| Blocking event loop | MEDIUM | Wrap existing sync calls in workers; add `call_from_thread()` at widget update sites |
| TextArea scaling issues | MEDIUM | Implement custom viewport-only renderer wrapping TextArea; or switch to a custom widget with manual tree-sitter integration |
| Parsing output for file edits | LOW | Add filesystem watcher alongside existing parsing; make parser a "fast hint" rather than source of truth |
| Key binding collisions | LOW | Add config file for keybindings; document terminal compatibility; no code architecture change needed |
| Missing CLAUDE.md loading | LOW | Single line fix: add `setting_sources=["project"]` to SDK options |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Raw subprocess vs SDK | Phase 1 (Foundation) | Can send a prompt and receive streaming tokens via `ClaudeSDKClient` |
| Event loop blocking | Phase 1-2 (Foundation + Claude Integration) | UI remains responsive (resizable, scrollable) during a 60-second Claude operation |
| TextArea scaling | Phase 2-3 (Code Editor) | Open a 5,000-line Python file; keystroke latency under 50ms; scroll is smooth |
| File edit detection | Phase 2-3 (Claude Integration + Editor) | Claude edits a file via Bash `sed` command; editor auto-jumps to the changed file |
| Key binding collisions | Phase 1-2 (Foundation + Layout) | Run full keybinding test in iTerm2, Alacritty, kitty, Apple Terminal |
| Missing project settings | Phase 2 (Claude Integration) | Project with CLAUDE.md; embedded Claude respects the same rules as standalone CLI |
| No streaming display | Phase 2 (Claude Integration) | Tokens appear in chat within 200ms of generation; no blank screen while waiting |
| Permission UX | Phase 2-3 (Claude Integration) | User can review code in editor while a permission prompt is visible in chat |
| Session persistence | Phase 3-4 (Polish) | Close app, reopen, continue last conversation with full context |
| Cost visibility | Phase 2-3 (Claude Integration) | Status bar shows cumulative token cost after each Claude response |

## Sources

- [Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference)
- [Claude Code headless/programmatic usage](https://code.claude.com/docs/en/headless)
- [Claude Agent SDK Python reference](https://platform.claude.com/docs/en/agent-sdk/python)
- [SDK subprocess hangs leaving zombie processes - anthropics/claude-code#18666](https://github.com/anthropics/claude-code/issues/18666)
- [ClaudeSDKClient hangs on Windows - anthropics/claude-agent-sdk-python#208](https://github.com/anthropics/claude-agent-sdk-python/issues/208)
- [--input-format stream-json undocumented - anthropics/claude-code#24594](https://github.com/anthropics/claude-code/issues/24594)
- [Claude Code -p hanging as subprocess fix](https://x.com/ClaudeCodeLog/status/2034402557980725358)
- [Textual Workers documentation](https://textual.textualize.io/guide/workers/)
- [Textual TextArea syntax highlighting scaling PR #5642](https://github.com/Textualize/textual/pull/5642)
- [Textual background incremental parsing PR #5645](https://github.com/Textualize/textual/pull/5645)
- [Textual key names and escape sequences wiki](https://github.com/Textualize/textual/wiki/Key-names-and-escape-sequences)
- [Textual FAQ - key binding limitations](https://textual.textualize.io/FAQ/)
- [7 Things learned building a modern TUI Framework](https://www.textualize.io/blog/7-things-ive-learned-building-a-modern-tui-framework/)
- [ANSI escape code standards - Julia Evans](https://jvns.ca/blog/2025/03/07/escape-code-standards/)
- [OpenCode TUI rendering bug with ANSI + memory leak - opencode#6119](https://github.com/anomalyco/opencode/issues/6119)
- [Undo/redo implementations in text editors](https://www.mattduck.com/undo-redo-text-editors)
- [Tree-sitter incremental parsing](https://tomassetti.me/incremental-parsing-using-tree-sitter/)
- [Agent Deck - terminal session manager for AI coding agents](https://github.com/asheshgoplani/agent-deck)
- [Khan/format-claude-stream - parsing Claude stream output](https://github.com/Khan/format-claude-stream)

---
*Pitfalls research for: Terminal-native IDE with embedded Claude Code*
*Researched: 2026-03-22*
