# Architecture Research

**Domain:** Terminal-native IDE with embedded AI subprocess (Claude Code)
**Researched:** 2026-03-22
**Confidence:** HIGH

## System Overview

```
+-----------------------------------------------------------------------+
|                          NanoClaude App (Textual)                      |
|                                                                       |
|  +------------+  +-------------------------+  +--------------------+  |
|  |            |  |                         |  |                    |  |
|  | File Tree  |  |     Code Editor         |  |   Claude Chat     |  |
|  | Panel      |  |     Panel               |  |   Panel           |  |
|  |            |  |                         |  |                    |  |
|  | Directory  |  |  TextArea(code_editor)  |  | Markdown output    |  |
|  | Tree       |  |  + syntax highlighting  |  | + streaming text   |  |
|  |            |  |  + line numbers         |  | + tool status      |  |
|  |            |  |  + diff gutter          |  | + input box        |  |
|  |            |  |                         |  |                    |  |
|  +-----+------+  +----------+--------------+  +---------+----------+  |
|        |                    |                            |             |
|  +-----+--------------------+----------------------------+----------+  |
|  |                    Event Bus (Textual Messages)                  |  |
|  +-----+--------------------+----------------------------+----------+  |
|        |                    |                            |             |
|  +-----+------+  +----------+--------------+  +---------+----------+  |
|  | File       |  |  File Watcher           |  | Claude Code        |  |
|  | System     |  |  (watchfiles)           |  | Bridge             |  |
|  | Service    |  |  Detects edits from     |  | (claude-agent-sdk) |  |
|  |            |  |  Claude or user         |  |                    |  |
|  +------------+  +-------------------------+  +--------+-----------+  |
|                                                        |              |
+--------------------------------------------------------|--------------|
                                                         | stdin/stdout
                                                         | NDJSON
                                                +--------+-----------+
                                                | Claude Code CLI    |
                                                | (subprocess)       |
                                                | via Agent SDK      |
                                                +--------------------+
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **App Shell** | Top-level layout, keybinding dispatch, panel focus management | Textual `App` subclass with CSS layout |
| **File Tree Panel** | Browse project files, select files to open | Textual `DirectoryTree` widget |
| **Code Editor Panel** | Display/edit code with syntax highlighting, show diffs | Textual `TextArea.code_editor()` with tree-sitter |
| **Claude Chat Panel** | Display Claude's streaming output, accept user prompts | Custom widget: `RichLog` for output + `Input` for prompts |
| **Terminal Panel** | Toggleable embedded terminal for running commands | Custom widget using PTY + pyte, or Log + Input fallback |
| **Claude Code Bridge** | Manage Claude Code subprocess lifecycle, parse messages | `claude-agent-sdk` `ClaudeSDKClient` wrapper |
| **File Watcher** | Detect filesystem changes from Claude or external edits | `watchfiles` library running in Textual Worker |
| **Event Bus** | Route events between components (file selected, file changed, Claude output) | Textual's built-in message/event system |

## Recommended Project Structure

```
nano_claude/
+-- app.py                  # App entrypoint, layout composition
+-- styles.tcss             # Textual CSS stylesheet
+-- panels/                 # UI panel widgets
|   +-- __init__.py
|   +-- file_tree.py        # DirectoryTree wrapper with filtering
|   +-- editor.py           # Code editor with diff highlighting
|   +-- chat.py             # Claude chat display + input
|   +-- terminal.py         # Toggleable terminal panel
+-- bridge/                 # Claude Code integration
|   +-- __init__.py
|   +-- client.py           # ClaudeSDKClient lifecycle management
|   +-- messages.py         # Message type parsing and routing
|   +-- file_detector.py    # Detect file edits from tool_use blocks
+-- services/               # Background services
|   +-- __init__.py
|   +-- file_watcher.py     # watchfiles integration
|   +-- file_system.py      # File read/write operations
|   +-- diff.py             # Diff computation and highlighting
+-- keybindings/            # Keybinding definitions
|   +-- __init__.py
|   +-- bindings.py         # All keybinding definitions
|   +-- actions.py          # Action handlers
+-- config/                 # Configuration
|   +-- __init__.py
|   +-- settings.py         # User preferences, layout defaults
+-- __main__.py             # CLI entry point
```

### Structure Rationale

- **panels/:** Each UI panel is a self-contained Textual widget. Panels communicate through the event bus, never directly. This allows independent development and testing.
- **bridge/:** Isolates all Claude Code subprocess logic. The rest of the app never touches stdin/stdout directly -- it sends messages to the bridge and receives parsed events back.
- **services/:** Background tasks that run in Textual Workers. File watching and diff computation happen off the main thread to keep the UI responsive.
- **keybindings/:** Centralized keybinding registry. Since nano-claude uses custom keybindings (not vim/emacs), keeping them in one place prevents conflicts.

## Architectural Patterns

### Pattern 1: Message-Driven Panel Communication

**What:** Panels communicate exclusively through Textual's message system (custom `Message` subclasses posted to the app). No panel holds a reference to another panel.

**When to use:** Always -- this is the foundational pattern for the entire app.

**Trade-offs:** Slightly more boilerplate than direct references, but enables loose coupling, testability, and prevents circular dependencies between panels.

**Example:**
```python
from textual.message import Message

class FileSelected(Message):
    """Posted when user selects a file in the tree."""
    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path

class FileChanged(Message):
    """Posted when a file is modified (by Claude or externally)."""
    def __init__(self, path: str, changed_lines: list[int]) -> None:
        super().__init__()
        self.path = path
        self.changed_lines = changed_lines

class ClaudeOutput(Message):
    """Posted when Claude produces streaming text."""
    def __init__(self, text: str, is_tool: bool = False) -> None:
        super().__init__()
        self.text = text
        self.is_tool = is_tool

# In app.py -- handle messages to coordinate panels
class NanoClaudeApp(App):
    def on_file_selected(self, event: FileSelected) -> None:
        editor = self.query_one(EditorPanel)
        editor.open_file(event.path)

    def on_file_changed(self, event: FileChanged) -> None:
        editor = self.query_one(EditorPanel)
        editor.highlight_changes(event.path, event.changed_lines)
```

### Pattern 2: Async Bridge with Worker Isolation

**What:** The Claude Code subprocess runs in a dedicated Textual Worker. The bridge translates between the SDK's async iterator protocol and Textual messages, keeping the UI thread free.

**When to use:** For all Claude Code communication. Never call the SDK from the main thread.

**Trade-offs:** Adds a layer of indirection, but prevents the UI from freezing during long Claude responses or tool executions.

**Example:**
```python
from textual.worker import Worker, work

class ClaudeBridge:
    def __init__(self, app: App) -> None:
        self.app = app
        self.client: ClaudeSDKClient | None = None

    @work(thread=True)
    async def send_message(self, prompt: str) -> None:
        if self.client is None:
            self.client = ClaudeSDKClient(options=self.options)
            await self.client.connect()

        await self.client.query(prompt)
        async for message in self.client.receive_response():
            if isinstance(message, StreamEvent):
                event = message.event
                if event.get("type") == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        self.app.post_message(ClaudeOutput(delta["text"]))
            elif isinstance(message, AssistantMessage):
                self._detect_file_edits(message)
            elif isinstance(message, ResultMessage):
                self.app.post_message(ClaudeComplete(message))

    def _detect_file_edits(self, message: AssistantMessage) -> None:
        for block in message.content:
            if isinstance(block, ToolUseBlock) and block.name == "Edit":
                path = block.input.get("file_path", "")
                self.app.post_message(FileChanged(path, []))
```

### Pattern 3: CSS-Driven Layout with Panel Toggling

**What:** Use Textual CSS for panel layout (grid/dock), with panel visibility controlled by adding/removing CSS classes. Panel sizing uses CSS fr units or percentages.

**When to use:** For all layout management. CSS is the single source of truth for panel arrangement.

**Trade-offs:** Textual CSS is a subset of web CSS and has some quirks (no splitter/drag-resize natively), but it keeps layout logic declarative and separate from Python code.

**Example:**
```python
# styles.tcss
Screen {
    layout: grid;
    grid-size: 3 1;
    grid-columns: 1fr 3fr 2fr;
}

#file-tree {
    dock: left;
    width: 20%;
    min-width: 15;
}

#editor {
    width: 1fr;
}

#chat {
    width: 1fr;
}

#terminal {
    display: none;  /* hidden by default */
    dock: bottom;
    height: 30%;
}

#terminal.visible {
    display: block;
}
```

```python
# Toggle terminal panel
class NanoClaudeApp(App):
    BINDINGS = [("ctrl+t", "toggle_terminal", "Toggle Terminal")]

    def action_toggle_terminal(self) -> None:
        terminal = self.query_one("#terminal")
        terminal.toggle_class("visible")
```

## Data Flow

### Core Data Flows

```
1. User types in Claude Chat Input
        |
        v
   ChatPanel.on_input_submitted()
        |
        v
   ClaudeBridge.send_message(prompt)    [Worker thread]
        |
        v
   ClaudeSDKClient.query(prompt)        [subprocess stdin]
        |
        v
   Claude Code CLI processes            [external process]
        |
        v
   StreamEvent / AssistantMessage       [subprocess stdout, NDJSON]
        |
        v
   ClaudeBridge parses messages         [Worker thread]
        |
        +---> ClaudeOutput(text)  -------> ChatPanel renders streaming markdown
        |
        +---> FileChanged(path)  -------> EditorPanel jumps to file, highlights
        |
        +---> ClaudeComplete()   -------> ChatPanel shows completion indicator
```

```
2. User selects file in File Tree
        |
        v
   DirectoryTree.FileSelected event
        |
        v
   App.on_file_selected() handler
        |
        v
   EditorPanel.open_file(path)
        |
        v
   FileSystemService.read_file(path)   [Worker thread]
        |
        v
   TextArea.load_text(content)
   TextArea.language = detected_lang
```

```
3. Claude edits a file (detected from tool_use blocks)
        |
        v
   ClaudeBridge detects Edit/Write tool_use in AssistantMessage
        |
        v
   FileChanged message posted with path + changed_lines
        |
        v
   App.on_file_changed() handler
        |
        +---> If file is open in editor:
        |       EditorPanel.highlight_changes(changed_lines)
        |       EditorPanel.scroll_to_change()
        |
        +---> If file is NOT open:
                EditorPanel.open_file(path)
                EditorPanel.highlight_changes(changed_lines)
```

```
4. File Watcher detects external change
        |
        v
   watchfiles detects modification      [Worker thread]
        |
        v
   FileWatcher posts FileChanged message
        |
        v
   If file is open in editor:
       EditorPanel reloads content
       Preserves cursor position if possible
```

### State Management

```
App State (Textual reactive attributes)
    |
    +-- current_file: str | None          (which file is open in editor)
    +-- claude_session_active: bool       (is Claude working?)
    +-- terminal_visible: bool            (is terminal panel shown?)
    +-- changed_files: set[str]           (files modified by Claude in current turn)
    +-- panel_focus: str                  (which panel has focus)
```

Textual's reactive attribute system handles state. When `current_file` changes, the editor panel automatically updates. When `claude_session_active` changes, the chat panel shows/hides the loading indicator. No external state management library is needed -- Textual's reactivity is sufficient for this scope.

### Key Data Flows

1. **User prompt to Claude response:** ChatPanel input -> ClaudeBridge worker -> Claude Code subprocess -> NDJSON stream -> parsed messages -> UI updates
2. **File selection to editor display:** DirectoryTree event -> App handler -> FileSystem worker -> TextArea content load
3. **Claude file edit to editor highlight:** AssistantMessage tool_use -> FileChanged message -> EditorPanel jump + highlight
4. **User code selection to Claude context:** EditorPanel selection -> "Send to Claude" action -> ChatPanel auto-fills prompt with selected code

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Claude Code CLI | `claude-agent-sdk` `ClaudeSDKClient` over subprocess stdin/stdout | Use `include_partial_messages=True` for streaming. The SDK bundles the CLI -- no separate install needed. Multi-turn via `ClaudeSDKClient` preserves conversation context. |
| File System | `watchfiles` for monitoring + standard `pathlib` for read/write | watchfiles is Rust-backed, efficient for large projects. Run in Textual Worker to avoid blocking UI. |
| Git | Subprocess calls to `git diff` for change visualization | Only needed for the full diff view feature. Not needed for the jump-and-highlight flow. |
| tree-sitter | Via Textual's `TextArea` syntax highlighting | Install `textual[syntax]` to get tree-sitter. Supports Python, JS, TS, Rust, Go, and more out of the box. Custom languages can be registered. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| ChatPanel <-> ClaudeBridge | Textual Messages (ClaudeOutput, ClaudeComplete) | Bridge runs in Worker, posts messages to app. ChatPanel never touches the SDK directly. |
| EditorPanel <-> FileTree | Textual Messages (FileSelected) | Editor receives file path, handles loading independently. |
| EditorPanel <-> ClaudeBridge | Textual Messages (FileChanged) | Bridge detects edits from tool_use blocks, editor receives change notifications. Completely decoupled. |
| EditorPanel <-> FileWatcher | Textual Messages (FileChanged) | Same message type whether change comes from Claude or external. Editor does not care about the source. |
| All Panels <-> App Shell | Focus management via keybindings | App Shell owns panel focus switching. Panels declare `can_focus=True` but don't manage their own focus transitions. |

### Claude Code Bridge Protocol Detail

The bridge uses `claude-agent-sdk`'s `ClaudeSDKClient` for multi-turn interaction. This is the recommended integration path because:

1. **Multi-turn conversations:** `ClaudeSDKClient` maintains session state across multiple user messages, matching the interactive chat UX.
2. **Streaming:** With `include_partial_messages=True`, the SDK yields `StreamEvent` objects containing raw API deltas for real-time text rendering.
3. **Tool detection:** `AssistantMessage` objects contain `ToolUseBlock` content blocks. When `block.name` is `Edit`, `Write`, or `Bash`, the bridge can infer file changes.
4. **Interrupt support:** `ClaudeSDKClient.interrupt()` allows the user to cancel a running Claude operation.
5. **Session resume:** Sessions can be continued with `continue_conversation=True` or resumed by ID.

**Message flow through the bridge:**

```
StreamEvent(content_block_start, tool_use)   -> "Claude is using [Tool]..." status
StreamEvent(content_block_delta, text_delta)  -> Append text to chat display
StreamEvent(content_block_delta, input_json)  -> (internal) accumulate tool input
StreamEvent(content_block_stop)               -> Tool finished, check for file edits
AssistantMessage                              -> Complete turn, extract all tool_use blocks
ResultMessage                                 -> Session complete, show cost/usage
```

## Scaling Considerations

This is a single-user desktop application, not a server. "Scaling" means handling large codebases and long Claude sessions gracefully.

| Concern | Small Project (< 100 files) | Large Project (10K+ files) | Very Large (monorepo) |
|---------|------------------------------|---------------------------|----------------------|
| File Tree | Load eagerly, no issue | Lazy-load with `DirectoryTree` (already async) | Add `.gitignore` filtering, virtual scrolling |
| Editor | Load entire file | Load entire file (TextArea handles this) | May need file size limits for very large files (> 10MB) |
| File Watcher | Watch project root | Filter to relevant directories | Must respect `.gitignore`, use watchfiles filtering |
| Claude Session | Short conversations | Long conversations may accumulate tokens | SDK handles compaction internally (CompactBoundaryMessage) |
| Diff Highlighting | Trivial | May involve large diffs | Compute diffs in Worker thread, show summary first |

### Performance Priorities

1. **First bottleneck: UI responsiveness during Claude streaming.** Solution: All SDK interaction in Worker threads. Stream text deltas to the chat panel character-by-character. Never block the Textual event loop.
2. **Second bottleneck: File tree loading in large projects.** Solution: `DirectoryTree` already loads asynchronously. Add `.gitignore` filtering to reduce node count. Lazy-expand directories.
3. **Third bottleneck: Syntax highlighting on large files.** Solution: tree-sitter is fast (written in C). But initial parse of very large files may lag. Consider disabling highlighting above a file size threshold.

## Anti-Patterns

### Anti-Pattern 1: Direct Subprocess Management

**What people do:** Spawn `claude -p` via `subprocess.Popen()` and manually manage stdin/stdout pipes, parsing raw JSON output.

**Why it's wrong:** The raw CLI in `--print` mode only returns the final result, missing intermediate tool calls and streaming. Managing the subprocess lifecycle (startup, shutdown, error recovery, session state) is complex and error-prone. The `--input-format stream-json` protocol is undocumented and has known bugs (duplicate session entries).

**Do this instead:** Use the `claude-agent-sdk` Python package. It bundles the CLI, manages the subprocess internally, provides typed message objects, and handles streaming, sessions, and error recovery. `ClaudeSDKClient` gives multi-turn support out of the box.

### Anti-Pattern 2: Full Terminal Emulator for the Terminal Panel

**What people do:** Embed a complete terminal emulator (via `pyte` + `textual-terminal`) for the toggleable terminal panel.

**Why it's wrong:** Python-based terminal emulation via pyte is extremely slow. The `textual-terminal` library is poorly maintained (16 commits total, single contributor). A full terminal emulator is overkill for the use case -- users need to run occasional commands, not a full interactive shell.

**Do this instead:** Start with a `RichLog` + `Input` combination (as Textual's maintainer recommends). Log displays command output with ANSI color support, Input accepts commands. If full PTY support is later needed, consider the Rust-backed `par-term-emu-core-rust` approach, but only after validating the simpler approach is insufficient.

### Anti-Pattern 3: Polling for File Changes

**What people do:** Use a timer to periodically check if files have changed on disk, especially after Claude edits.

**Why it's wrong:** Polling is wasteful and introduces latency. With a 1-second poll interval, the user sees a 0-1 second delay after Claude's edit before the editor updates. Shorter intervals waste CPU.

**Do this instead:** Use two complementary approaches: (1) Detect file edits proactively by parsing `ToolUseBlock` content from `AssistantMessage` -- this gives instant notification when Claude finishes an edit. (2) Use `watchfiles` (Rust-backed filesystem watcher) as a safety net for changes the bridge might miss.

### Anti-Pattern 4: Shared Mutable State Between Panels

**What people do:** Give panels direct references to each other or to shared state objects, with panels modifying state that other panels read.

**Why it's wrong:** Creates tight coupling, race conditions, and makes it impossible to test panels in isolation. Textual's async nature means two panels could modify shared state from different call contexts.

**Do this instead:** Use Textual's message system exclusively. Each panel posts messages describing what happened (not what should happen). The App Shell handles coordination. State lives on the App as reactive attributes, which trigger watchers when changed.

## Build Order (Dependency Chain)

Components should be built in this order based on dependencies:

```
Phase 1: Foundation
   App Shell + CSS Layout + Keybinding Framework
   (everything else mounts into this)

Phase 2: Core Panels (can be parallel)
   +-- File Tree Panel (standalone, uses DirectoryTree)
   +-- Code Editor Panel (standalone, uses TextArea.code_editor)

Phase 3: Claude Integration
   Claude Code Bridge (depends on App Shell for message posting)
   +-- Chat Panel (depends on Bridge for message types)

Phase 4: Cross-Panel Integration
   File Change Detection (depends on Bridge + Editor)
   +-- Jump-and-highlight (depends on Editor + Bridge + FileWatcher)
   +-- Send selection to Claude (depends on Editor + Chat)

Phase 5: Enhancement
   +-- Terminal Panel (depends on App Shell layout)
   +-- Full Diff View (depends on Editor + git subprocess)
   +-- Panel Resizing (depends on all panels existing)
```

**Rationale:** The App Shell must exist first as the mounting point. File Tree and Editor are independent widgets that can be built in parallel. The Claude Bridge is the most complex component and should be built before the Chat Panel (which depends on its message types). Cross-panel features like jump-and-highlight require both the editor and bridge to be working. Terminal and diff view are enhancement features that build on the foundation.

## Sources

- [Toad announcement - Will McGugan](https://willmcgugan.github.io/announcing-toad/) - Architecture of Textual-based AI terminal UI (front-end/back-end separation, JSON over stdin/stdout)
- [Toad GitHub](https://github.com/batrachianai/toad) - Reference implementation of AI-in-terminal TUI
- [Claude Code CLI Reference](https://code.claude.com/docs/en/cli-reference) - Authoritative CLI flags for subprocess embedding
- [Claude Code Headless Mode](https://code.claude.com/docs/en/headless) - Programmatic usage documentation
- [Claude Agent SDK - Streaming Output](https://platform.claude.com/docs/en/agent-sdk/streaming-output) - StreamEvent protocol, message types, streaming patterns (HIGH confidence)
- [Claude Agent SDK - Python Reference](https://platform.claude.com/docs/en/agent-sdk/python) - ClaudeSDKClient API, ClaudeAgentOptions, message types (HIGH confidence)
- [Embedding Claude Code SDK](https://blog.bjdean.id.au/2025/11/embedding-claide-code-sdk-in-applications/) - Practical SDK embedding guide
- [Textual TextArea Widget](https://textual.textualize.io/widgets/text_area/) - Code editor widget with tree-sitter syntax highlighting (HIGH confidence)
- [Textual DirectoryTree Widget](https://textual.textualize.io/widgets/directory_tree/) - File browser widget with async loading (HIGH confidence)
- [Textual Layout Guide](https://textual.textualize.io/how-to/design-a-layout/) - CSS-based layout, docking, containers
- [Textual Input Guide](https://textual.textualize.io/guide/input/) - Keybindings, focus management, actions
- [textual-terminal GitHub](https://github.com/mitosch/textual-terminal) - Terminal emulator widget (LOW confidence - poorly maintained)
- [Textual Discussion #5461](https://github.com/Textualize/textual/discussions/5461) - Maintainer recommendation against full terminal emulation
- [watchfiles GitHub](https://github.com/samuelcolvin/watchfiles) - Rust-backed file watcher for Python
- [claude-agent-sdk PyPI](https://pypi.org/project/claude-agent-sdk/) - Python SDK package

---
*Architecture research for: Terminal-native IDE with embedded Claude Code*
*Researched: 2026-03-22*
