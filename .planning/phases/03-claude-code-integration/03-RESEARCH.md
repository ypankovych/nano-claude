# Phase 3: Claude Code Integration - Research

**Researched:** 2026-03-22
**Domain:** PTY-embedded Claude Code CLI in Textual TUI
**Confidence:** HIGH

## Summary

Phase 3 replaces the ChatPanel placeholder with a real PTY running the `claude` CLI. This is fundamentally different from the SDK-based approach recommended in the earlier STACK.md and ARCHITECTURE.md -- the user has made a locked decision that the chat panel IS a terminal running the real `claude` command. The approach is sound: Claude Code renders into the normal terminal buffer (not alternate screen), uses Ink/React for its TUI, and outputs ANSI escape sequences for formatting. The PTY approach means users get the exact same experience as standalone Claude Code -- same rendering, same permission prompts, same keyboard interaction -- with zero reimplementation.

The core technical challenge is: spawn `claude` in a PTY, feed its output through pyte (an in-memory VT100 emulator) to maintain a screen buffer, render that buffer into a Textual widget using Rich `Text.from_ansi()`, and simultaneously parse the raw PTY output stream for status/cost information to display in the app's status bar. The pyte terminal emulator example for Textual (from the pyte repository itself) provides a proven reference architecture using asyncio queues and `loop.add_reader()` for non-blocking PTY I/O.

**Primary recommendation:** Use `ptyprocess` (0.7.0) for PTY subprocess management and `pyte` (0.8.2) for VT100 terminal emulation. Build a custom `TerminalWidget` extending Textual's `Widget` with `render()` returning a Rich renderable built from pyte's screen buffer. Run PTY I/O in a Textual Worker thread. Parse status/cost from Claude Code's statusline JSON (available via the `--statusline` mechanism or by scraping terminal output patterns).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- The chat panel embeds the actual `claude` CLI running in a pseudo-terminal (PTY) -- NOT a custom chat UI
- Users see Claude Code's native interface: its prompts, markdown rendering, tool use output, permission prompts, everything
- Users type directly into the PTY -- no separate input bar, no custom message handling
- Claude Code inherits all its features automatically: tools, hooks, MCP servers, CLAUDE.md, slash commands, permission system (CLAUDE-02 satisfied by design)
- Claude Code auto-starts on app launch (carried forward from Phase 1 decision)
- Claude Code's built-in permission prompts appear natively in the PTY -- no extra UI layer needed
- Users interact with permission prompts directly in the PTY, same as they would in a standalone terminal
- Parse the PTY output stream for status patterns (spinner characters, "Thinking...", tool use markers) and reflect Claude's state in the app's bottom status bar
- States: idle, thinking, writing code, waiting for permission
- Parse Claude Code's token/cost output from the PTY stream (shown at end of responses)
- Display in the app's bottom status bar alongside the status indicator
- Format: compact (e.g., "12.3k tokens * $0.04")
- If the Claude Code process crashes or exits: show the error in the chat panel + offer a "Restart Claude" action (shortcut to respawn)
- Do NOT auto-restart -- user should see what happened
- If `claude` CLI isn't installed or not on PATH: launch app normally, editor and tree work, chat panel shows "Claude Code not found" with install instructions
- Graceful degradation -- the app is still useful as a code editor without Claude

### Claude's Discretion
- Exact PTY library choice (ptyprocess, pyte, or alternative)
- How PTY output is rendered into the Textual widget (pyte screen buffer vs raw ANSI passthrough)
- Status bar parsing patterns (regex for spinner, thinking, tool use detection)
- Token/cost parsing regex from Claude Code output
- PTY size (rows/cols) synchronization with the chat panel dimensions
- Restart shortcut key assignment

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CLAUDE-01 | User can type prompts in the Claude chat panel and receive streaming responses from the actual Claude Code CLI running as an embedded subprocess | PTY embedding via ptyprocess + pyte provides full bidirectional I/O. User types directly into PTY (keyboard events forwarded). Claude's streaming output rendered through pyte screen buffer into Textual widget. |
| CLAUDE-02 | Claude Code subprocess inherits all features (tools, hooks, MCP servers, CLAUDE.md, permissions) -- no reimplementation | Satisfied by design: running the real `claude` CLI in a PTY inherits everything. No SDK options, no configuration needed -- it is the real CLI. |
| CLAUDE-03 | User sees Claude's responses rendered with markdown formatting and syntax-highlighted code blocks | Claude Code renders its own markdown and syntax highlighting via Ink. The PTY captures the full ANSI output. pyte processes escape sequences -> Rich `Text.from_ansi()` preserves all styling. |
| CLAUDE-04 | User sees a status indicator showing Claude's current state (idle, thinking, writing code, waiting for permission) | Parse PTY output for Claude's spinner characters (6 flower-like Unicode chars cycling), "Thinking" text, tool use markers. Claude Code also has a statusline mechanism that outputs JSON with session metadata. |
| CLAUDE-05 | User sees token usage and estimated cost for the current session in the status bar | Claude Code's statusline JSON includes `cost.total_cost_usd`, `context_window.total_input_tokens`, `context_window.total_output_tokens`. Can be extracted from PTY output or via a parallel statusline script mechanism. |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ptyprocess | 0.7.0 | PTY subprocess management | Wraps `pty.fork()` with proper lifecycle management (spawn, read, write, setwinsize, isalive, close). Used internally by pexpect. Handles SIGWINCH for terminal resize. Cross-platform on Unix/macOS. |
| pyte | 0.8.2 | In-memory VT100/VT220 terminal emulator | Processes ANSI escape sequences into a screen buffer with character attributes, cursor position, and dirty-line tracking. The official pyte repository includes a Textual terminal emulator example. |
| textual | 8.1.1 | TUI framework (already installed) | Already the project's core framework. Provides Widget base class, render() method, Rich integration, Worker threads, and asyncio event loop. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rich (Text, Style) | 14.3.3 (textual dep) | Convert pyte screen buffer to styled text | `Text.from_ansi()` converts ANSI-escaped strings to Rich Text objects. Already installed as Textual dependency. |
| asyncio (stdlib) | 3.12+ | Non-blocking PTY I/O via loop.add_reader() | Register PTY file descriptor for async reads without blocking Textual's event loop. |
| shutil | stdlib | Check if `claude` CLI exists on PATH | `shutil.which("claude")` for graceful degradation check. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ptyprocess | stdlib `pty.fork()` | Lower-level, no setwinsize convenience, no isalive(), no proper cleanup. ptyprocess wraps this with a clean API. |
| pyte | Raw ANSI passthrough | Would skip terminal emulation, losing cursor tracking, scroll regions, and screen-buffer state. Claude Code uses cursor positioning for its spinner/status, which requires proper VT100 emulation. |
| pyte | textual-terminal | Unmaintained (16 commits, single contributor), LGPL-3 license, described as "extremely slow" by Textual maintainer. Build custom widget using pyte directly. |
| Worker thread | asyncio add_reader | add_reader works but Textual Workers provide better integration with the framework's lifecycle (cancel, exclusive, error handling). PTY reads are blocking I/O -- thread=True is the correct pattern. |

**Installation:**
```bash
uv add ptyprocess pyte
```

**Version verification:** ptyprocess 0.7.0 (latest on PyPI, stable since 2020), pyte 0.8.2 (latest on PyPI, stable since 2023). Both are mature, stable libraries with no expected breaking changes.

## Architecture Patterns

### Recommended Project Structure
```
nano_claude/
+-- panels/
|   +-- chat.py              # ChatPanel with embedded TerminalWidget (REPLACE existing placeholder)
+-- terminal/                 # NEW: Terminal emulation components
|   +-- __init__.py
|   +-- widget.py             # TerminalWidget -- pyte-backed Textual Widget
|   +-- pty_manager.py        # PTY lifecycle management (spawn, read, write, resize, cleanup)
|   +-- status_parser.py      # Parse PTY output for Claude status/cost/tokens
+-- services/
|   +-- claude_service.py     # NEW: Claude Code subprocess lifecycle (start, restart, check availability)
+-- config/
|   +-- settings.py           # Add Claude-related constants (restart key, status patterns)
```

### Pattern 1: PTY-in-Widget Architecture
**What:** The TerminalWidget owns a pyte.Screen and renders it via Rich. A background Worker thread reads from the PTY fd and feeds data to the pyte Stream. Keyboard events are forwarded as writes to the PTY.

**When to use:** This is THE pattern for the entire Phase 3 implementation.

**Example:**
```python
# Source: pyte terminal_emulator.py example + Textual Worker pattern
import asyncio
import os
import pty
import struct
import fcntl
import termios

import pyte
from rich.text import Text
from textual.widget import Widget
from textual.worker import work
from textual import events

class TerminalWidget(Widget, can_focus=True):
    """Renders a PTY subprocess via pyte terminal emulation."""

    DEFAULT_CSS = """
    TerminalWidget {
        overflow-y: auto;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._screen: pyte.Screen | None = None
        self._stream: pyte.Stream | None = None
        self._pty_fd: int | None = None
        self._pty_pid: int | None = None
        self._running = False

    def on_mount(self) -> None:
        """Start the PTY subprocess when widget is mounted."""
        # Defer to allow layout to determine size
        self.call_later(self._start_pty)

    def _start_pty(self) -> None:
        """Spawn the claude CLI in a PTY."""
        cols = self.size.width
        rows = self.size.height
        self._screen = pyte.Screen(cols, rows)
        self._stream = pyte.Stream(self._screen)

        pid, fd = pty.fork()
        if pid == 0:
            # Child process -- exec claude
            env = os.environ.copy()
            env["TERM"] = "xterm-256color"
            env["COLUMNS"] = str(cols)
            env["LINES"] = str(rows)
            os.execvpe("claude", ["claude"], env)
        else:
            self._pty_pid = pid
            self._pty_fd = fd
            self._running = True
            # Set initial window size
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
            # Start reading in background
            self._read_worker()

    @work(thread=True)
    def _read_worker(self) -> None:
        """Background worker reading PTY output."""
        fd = self._pty_fd
        while self._running and fd is not None:
            try:
                data = os.read(fd, 65536)
                if not data:
                    break
                decoded = data.decode("utf-8", errors="replace")
                # Feed to pyte on the main thread
                self.app.call_from_thread(self._feed_data, decoded)
            except OSError:
                break
        self.app.call_from_thread(self._on_pty_exit)

    def _feed_data(self, data: str) -> None:
        """Feed PTY output to pyte stream and refresh display."""
        if self._stream:
            self._stream.feed(data)
            self.refresh()
            # Also parse for status/cost
            self.post_message(PtyOutput(data))

    def on_key(self, event: events.Key) -> None:
        """Forward keyboard input to PTY."""
        if self._pty_fd is None or not self._running:
            return
        char = self._translate_key(event)
        if char:
            os.write(self._pty_fd, char.encode("utf-8"))
            event.prevent_default()

    def render(self):
        """Render pyte screen buffer as Rich Text."""
        if self._screen is None:
            return Text("Starting Claude Code...")
        lines = []
        for i, line in enumerate(self._screen.display):
            text = Text.from_ansi(line)
            # Show cursor position
            if i == self._screen.cursor.y:
                x = self._screen.cursor.x
                if x < len(line):
                    text.stylize("reverse", x, x + 1)
            lines.append(text)
        # Join lines with newlines
        result = Text("\n").join(lines)
        return result
```

### Pattern 2: Status/Cost Extraction from PTY Output
**What:** A status parser monitors raw PTY output (before pyte processing) for Claude-specific patterns: spinner characters, "Thinking" text, tool use output, and token/cost summaries.

**When to use:** For CLAUDE-04 (status indicator) and CLAUDE-05 (token/cost display).

**Key insight:** Claude Code's statusline feature outputs JSON with session metadata including `cost.total_cost_usd`, `context_window.total_input_tokens`, etc. However, this is a separate mechanism (a shell script that receives JSON on stdin) -- not embedded in the PTY output stream itself. For the PTY approach, we need to parse the visible terminal output.

**What the PTY output contains:**
- Spinner characters cycling: middle dot, teardrop-spoked asterisk, heavy teardrop-spoked asterisk, six pointed black star, eight spoked asterisk, four balloon-spoked asterisk
- Text patterns: "Thinking", tool names in brackets (e.g., "[Read]", "[Edit]", "[Bash]", "[Write]")
- Token/cost summary at end of responses (visible in the terminal output)
- Permission prompts with Y/n text

**Example:**
```python
import re
from dataclasses import dataclass
from enum import Enum, auto
from textual.message import Message

class ClaudeState(Enum):
    IDLE = auto()
    THINKING = auto()
    TOOL_USE = auto()
    PERMISSION = auto()
    DISCONNECTED = auto()

@dataclass
class StatusUpdate(Message):
    state: ClaudeState
    detail: str = ""

@dataclass
class CostUpdate(Message):
    total_tokens: int = 0
    total_cost_usd: float = 0.0

class StatusParser:
    """Parse raw PTY output for Claude Code status patterns."""

    # Claude's spinner characters
    SPINNER_CHARS = frozenset("*+")  # Simplified; actual chars are Unicode flower-like
    THINKING_PATTERN = re.compile(r"Thinking")
    TOOL_PATTERN = re.compile(r"\[(Read|Write|Edit|Bash|Glob|Grep|WebSearch|WebFetch)\]")
    PERMISSION_PATTERN = re.compile(r"\b(Allow|Deny|Yes|No)\b.*\?")
    # Token/cost pattern from Claude's output (e.g., "12.3k tokens * $0.04")
    COST_PATTERN = re.compile(
        r"(\d+\.?\d*[kK]?)\s*tokens?\s*[\*\xb7]\s*\$(\d+\.?\d*)"
    )

    def __init__(self):
        self._state = ClaudeState.IDLE
        self._buffer = ""

    def feed(self, data: str) -> list[Message]:
        """Analyze PTY output chunk and return any status/cost messages."""
        messages = []
        self._buffer += data

        # Check for state transitions
        if self.TOOL_PATTERN.search(data):
            match = self.TOOL_PATTERN.search(data)
            new_state = ClaudeState.TOOL_USE
            messages.append(StatusUpdate(new_state, detail=match.group(1)))
        elif self.THINKING_PATTERN.search(data):
            messages.append(StatusUpdate(ClaudeState.THINKING))
        elif self.PERMISSION_PATTERN.search(data):
            messages.append(StatusUpdate(ClaudeState.PERMISSION))

        # Check for cost info
        cost_match = self.COST_PATTERN.search(data)
        if cost_match:
            tokens_str = cost_match.group(1)
            cost_str = cost_match.group(2)
            tokens = self._parse_token_count(tokens_str)
            messages.append(CostUpdate(
                total_tokens=tokens,
                total_cost_usd=float(cost_str)
            ))

        # Trim buffer to prevent unbounded growth
        if len(self._buffer) > 4096:
            self._buffer = self._buffer[-2048:]

        return messages

    @staticmethod
    def _parse_token_count(s: str) -> int:
        s = s.lower()
        if s.endswith("k"):
            return int(float(s[:-1]) * 1000)
        return int(float(s))
```

### Pattern 3: Graceful Degradation
**What:** Check for `claude` CLI availability at startup. If not found, show an informative message in the chat panel instead of a terminal widget. If the process crashes, show the error and offer restart.

**When to use:** Always -- this is a hard requirement from CONTEXT.md.

**Example:**
```python
import shutil

class ChatPanel(BasePanel):
    def compose(self):
        if shutil.which("claude") is None:
            yield Static(
                "Claude Code not found\n\n"
                "Install Claude Code CLI:\n"
                "  npm install -g @anthropic-ai/claude-code\n\n"
                "The editor and file tree still work without Claude.",
                id="claude-not-found",
            )
        else:
            yield TerminalWidget(id="claude-terminal")
```

### Pattern 4: PTY Resize Synchronization
**What:** When the Textual widget resizes (user resizes panel or terminal), notify the PTY subprocess via SIGWINCH so Claude Code adjusts its rendering.

**When to use:** Every time the chat panel's dimensions change.

**Example:**
```python
def on_resize(self, event: events.Resize) -> None:
    """Sync PTY dimensions with widget size."""
    if self._pty_fd is not None and self._running:
        cols = event.size.width
        rows = event.size.height
        # Update pyte screen
        if self._screen:
            self._screen.resize(rows, cols)
        # Notify PTY subprocess
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(self._pty_fd, termios.TIOCSWINSZ, winsize)
```

### Anti-Patterns to Avoid

- **Using claude-agent-sdk for the chat panel:** The locked decision is PTY, not SDK. The SDK gives structured data but loses Claude's native rendering, permission UX, and interactive features. The SDK is appropriate for Phase 4+ file detection, but NOT for the chat panel.
- **Building a custom chat UI (RichLog + Input):** This would reimplement what Claude Code already renders. The PTY approach gets all of Claude's formatting for free.
- **Blocking the event loop with PTY reads:** `os.read()` on the PTY fd blocks. MUST run in a Worker thread with `thread=True`, using `call_from_thread()` for widget updates.
- **Ignoring pyte and passing raw ANSI to Rich:** Claude Code uses cursor positioning, erase-in-display, and other VT100 sequences that Rich cannot process. pyte is required to maintain proper screen state.
- **Auto-restarting on crash:** User decision says NO auto-restart. Show the error, offer manual restart.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| VT100 terminal emulation | Custom ANSI parser | pyte (0.8.2) | VT100/VT220 is enormously complex (cursor modes, scroll regions, character sets, graphics rendition). pyte handles 95%+ of escape sequences. |
| PTY subprocess management | Raw `pty.fork()` + manual fd management | ptyprocess (0.7.0) | Handles fork/exec, setwinsize, isalive, proper cleanup. Raw pty.fork() leaks fds and doesn't handle edge cases. |
| Claude's markdown rendering | Custom markdown renderer in the chat panel | Claude Code's own Ink-based rendering (via PTY) | Claude Code renders its own output beautifully. The PTY captures this rendering faithfully through pyte. Zero additional rendering code needed. |
| Permission prompt UI | Custom permission dialog | Claude Code's built-in prompts (via PTY) | Users interact with Claude's native Y/n prompts directly in the PTY. No custom UI layer needed. |
| Key translation (arrows, Ctrl combos) | Manual escape code lookup table | Well-known ANSI escape sequences + Textual's event.key | Standard mapping: arrows -> ESC[A/B/C/D, Ctrl+C -> \x03, etc. Small lookup table, not a library. |

**Key insight:** The PTY approach means we don't hand-roll Claude's entire UX. We embed the real thing.

## Common Pitfalls

### Pitfall 1: PTY Read Blocking the Textual Event Loop
**What goes wrong:** Calling `os.read(fd, ...)` on the PTY file descriptor blocks until data is available. If done on the main thread, the entire TUI freezes.
**Why it happens:** Developers use `async def` but forget that `os.read()` is a blocking syscall, not an async operation.
**How to avoid:** Use `@work(thread=True)` to run the read loop in a dedicated thread. Use `self.app.call_from_thread()` to safely update widgets from the worker thread. `post_message()` is thread-safe and can be used directly.
**Warning signs:** UI freezes during Claude's thinking/streaming. Panel resize doesn't work while Claude is responding. User can't switch focus.

### Pitfall 2: pyte Screen Size Mismatch
**What goes wrong:** The pyte Screen is initialized with (80, 24) but the Textual widget is 120x35. Claude Code renders for 80 columns but the widget shows 120 columns of content, causing misaligned text and wrapping artifacts.
**Why it happens:** The pyte Screen dimensions and the PTY's TIOCSWINSZ must match the widget's actual character dimensions. If they diverge, the subprocess renders for the wrong size.
**How to avoid:** Initialize pyte Screen with the widget's actual size. On every widget resize, update both the pyte Screen (`screen.resize()`) and the PTY (`TIOCSWINSZ` ioctl). Defer initial PTY spawn until the widget is mounted and has a known size.
**Warning signs:** Text wraps at wrong column. Claude's formatted output looks broken. Spinner appears at wrong position.

### Pitfall 3: Keyboard Input Not Reaching the PTY
**What goes wrong:** Some keys work (regular characters) but arrows, Ctrl sequences, Enter, Backspace, Tab, and Escape don't. Claude Code's input appears broken.
**Why it happens:** Textual captures key events and doesn't pass them through by default. Arrow keys need to be translated to ANSI escape sequences. Ctrl+C should send SIGINT (byte 0x03), not trigger Textual's action.
**How to avoid:** Override `on_key()` in the TerminalWidget. Translate Textual key names to ANSI escape sequences. Call `event.prevent_default()` to stop Textual from handling the key. Build a comprehensive key map: arrows, home/end, page up/down, function keys, Ctrl+letter.
**Warning signs:** Can type text but can't press Enter to submit. Arrow keys do nothing. Can't Ctrl+C to interrupt Claude. Tab completion doesn't work.

### Pitfall 4: Claude Code Process Zombie After App Exit
**What goes wrong:** Closing the nano-claude app leaves the `claude` subprocess running as a zombie, consuming CPU and API credits.
**Why it happens:** Python's `pty.fork()` creates a child process that must be explicitly waited on. If the parent exits without killing the child and calling `os.waitpid()`, the process becomes a zombie.
**How to avoid:** In the app's `action_quit()`, explicitly kill the PTY process (send SIGTERM, then SIGKILL after timeout) and wait for it. Also handle unexpected exits (SIGTERM to the app itself) with signal handlers or `atexit` cleanup.
**Warning signs:** `ps aux | grep claude` shows orphaned processes after closing nano-claude. CPU usage stays high after exit.

### Pitfall 5: ANSI Color Fidelity Loss
**What goes wrong:** Claude Code uses 256-color and true-color ANSI escape sequences for syntax highlighting. pyte's `Screen.display` property returns plain text strings without embedded ANSI codes, losing all color information.
**Why it happens:** `Screen.display` is a convenience property that strips attributes. The actual character data with colors lives in `Screen.buffer`, which stores `Char` namedtuples with `fg`, `bg`, and style attributes.
**How to avoid:** Don't use `Screen.display` for rendering. Instead, iterate `Screen.buffer` to build Rich `Text` objects with proper `Style` applied per character. Map pyte's color names/numbers to Rich Style objects.
**Warning signs:** Claude's output appears as plain white text. Syntax highlighting in code blocks is lost. Tool use headers have no color.

### Pitfall 6: Status Parsing Regex Fragility
**What goes wrong:** The regex patterns for detecting Claude's thinking state, tool use, and cost break when Claude Code updates its output format (which happens frequently -- Claude Code is updated weekly).
**Why it happens:** Scraping terminal output is inherently fragile. ANSI escape codes are interspersed with the text, making naive regex unreliable.
**How to avoid:** Parse the pyte screen buffer (after ANSI processing) rather than raw PTY output. Keep patterns simple and defensive. Use heuristics rather than exact matching. Accept that status parsing may occasionally miss or misclassify -- better to show "idle" than crash. Consider using Claude Code's `--statusline` mechanism if it can be configured to write to a file.
**Warning signs:** Status indicator shows "thinking" when Claude is idle. Cost display never updates. State gets stuck.

## Code Examples

Verified patterns from official sources:

### PTY Spawn with Environment Setup
```python
# Source: ptyprocess docs + pyte terminal_emulator.py example
import os
import pty
import struct
import fcntl
import termios
import shutil

def spawn_claude_pty(cols: int, rows: int) -> tuple[int, int] | None:
    """Spawn claude CLI in a PTY. Returns (pid, fd) or None if claude not found."""
    if shutil.which("claude") is None:
        return None

    pid, fd = pty.fork()
    if pid == 0:
        # Child process
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env["COLUMNS"] = str(cols)
        env["LINES"] = str(rows)
        env["COLORTERM"] = "truecolor"
        # Exec claude -- inherits all env (PATH, ANTHROPIC_API_KEY, etc.)
        os.execvpe("claude", ["claude"], env)
    else:
        # Parent process -- set window size
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
        return pid, fd
```

### pyte Screen Buffer to Rich Text (with Color Fidelity)
```python
# Source: pyte API docs + Rich Text/Style docs
import pyte
from rich.text import Text
from rich.style import Style

# pyte color names -> Rich color names (subset)
PYTE_COLOR_MAP = {
    "black": "black",
    "red": "red",
    "green": "green",
    "brown": "yellow",
    "blue": "blue",
    "magenta": "magenta",
    "cyan": "cyan",
    "white": "white",
    "default": "default",
}

def render_pyte_screen(screen: pyte.Screen) -> list[Text]:
    """Convert pyte screen buffer to Rich Text lines with full color support."""
    lines = []
    for y in range(screen.lines):
        line = Text()
        buffer_line = screen.buffer[y]
        for x in range(screen.columns):
            char = buffer_line[x]
            # Build Rich Style from pyte Char attributes
            style_kwargs = {}
            if char.fg != "default":
                style_kwargs["color"] = PYTE_COLOR_MAP.get(char.fg, char.fg)
            if char.bg != "default":
                style_kwargs["bgcolor"] = PYTE_COLOR_MAP.get(char.bg, char.bg)
            if char.bold:
                style_kwargs["bold"] = True
            if char.italics:
                style_kwargs["italic"] = True
            if char.underscore:
                style_kwargs["underline"] = True
            if char.reverse:
                style_kwargs["reverse"] = True

            style = Style(**style_kwargs) if style_kwargs else Style.null()
            line.append(char.data, style=style)

        lines.append(line)
    return lines
```

### Key Translation Map
```python
# Source: VT100/xterm escape sequence standards
KEY_MAP = {
    # Arrow keys
    "up": "\x1b[A",
    "down": "\x1b[B",
    "right": "\x1b[C",
    "left": "\x1b[D",
    # Navigation
    "home": "\x1b[H",
    "end": "\x1b[F",
    "pageup": "\x1b[5~",
    "pagedown": "\x1b[6~",
    "insert": "\x1b[2~",
    "delete": "\x1b[3~",
    # Control keys
    "enter": "\r",
    "backspace": "\x7f",
    "tab": "\t",
    "escape": "\x1b",
    # Function keys
    "f1": "\x1bOP",
    "f2": "\x1bOQ",
    "f3": "\x1bOR",
    "f4": "\x1bOS",
    "f5": "\x1b[15~",
    "f6": "\x1b[17~",
    "f7": "\x1b[18~",
    "f8": "\x1b[19~",
    "f9": "\x1b[20~",
    "f10": "\x1b[21~",
    "f11": "\x1b[23~",
    "f12": "\x1b[24~",
}

def translate_key(event) -> str | None:
    """Translate Textual key event to PTY-compatible byte sequence."""
    key = event.key
    # Check key map first
    if key in KEY_MAP:
        return KEY_MAP[key]
    # Ctrl+letter -> control character
    if key.startswith("ctrl+") and len(key) == 6:
        letter = key[5]
        if letter.isalpha():
            return chr(ord(letter.upper()) - 64)
    # Regular character
    if event.character and len(event.character) == 1:
        return event.character
    return None
```

### Worker-Based PTY Read Loop
```python
# Source: Textual Workers docs + pyte terminal_emulator.py
from textual.worker import work

class TerminalWidget(Widget, can_focus=True):

    @work(thread=True, exclusive=True)
    def _start_read_loop(self) -> None:
        """Read from PTY in a dedicated thread."""
        while self._running:
            try:
                data = os.read(self._pty_fd, 65536)
                if not data:
                    # PTY closed
                    self.app.call_from_thread(self._handle_pty_exit)
                    break
                decoded = data.decode("utf-8", errors="replace")
                # Thread-safe: post_message is safe from any thread
                self.post_message(PtyDataReceived(decoded))
            except OSError:
                self.app.call_from_thread(self._handle_pty_exit)
                break

    def on_pty_data_received(self, message: PtyDataReceived) -> None:
        """Process PTY data on the main thread."""
        if self._stream:
            self._stream.feed(message.data)
        self.refresh()
        # Parse for status/cost
        self._status_parser.feed(message.data)
```

### Claude Process Lifecycle (Restart Support)
```python
# Source: Textual patterns + CONTEXT.md requirements
import os
import signal

class ClaudeService:
    """Manages the Claude Code subprocess lifecycle."""

    def __init__(self):
        self._pid: int | None = None
        self._fd: int | None = None

    def is_available(self) -> bool:
        """Check if claude CLI is on PATH."""
        return shutil.which("claude") is not None

    def start(self, cols: int, rows: int) -> tuple[int, int]:
        """Start claude in a PTY. Raises RuntimeError if not available."""
        if not self.is_available():
            raise RuntimeError("Claude Code CLI not found on PATH")
        result = spawn_claude_pty(cols, rows)
        if result is None:
            raise RuntimeError("Failed to spawn Claude Code PTY")
        self._pid, self._fd = result
        return self._pid, self._fd

    def stop(self) -> None:
        """Gracefully stop the Claude process."""
        if self._pid is not None:
            try:
                os.kill(self._pid, signal.SIGTERM)
                # Wait with timeout
                for _ in range(10):
                    pid, status = os.waitpid(self._pid, os.WNOHANG)
                    if pid != 0:
                        break
                    import time
                    time.sleep(0.1)
                else:
                    os.kill(self._pid, signal.SIGKILL)
                    os.waitpid(self._pid, 0)
            except (OSError, ChildProcessError):
                pass
            finally:
                self._pid = None
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            finally:
                self._fd = None

    def is_running(self) -> bool:
        """Check if the Claude process is still alive."""
        if self._pid is None:
            return False
        try:
            pid, status = os.waitpid(self._pid, os.WNOHANG)
            return pid == 0  # 0 means still running
        except ChildProcessError:
            return False
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| claude-agent-sdk for chat UI | PTY embedding of real CLI | User decision (Phase 3 CONTEXT.md) | Chat panel IS a terminal -- no custom UI, no SDK. Full fidelity. |
| textual-terminal for PTY widgets | Custom widget with pyte directly | 2024-2025 (textual-terminal abandoned) | Build our own TerminalWidget -- more control, better performance, no LGPL dependency. |
| pyte DiffScreen (separate class) | pyte Screen.dirty (merged in 0.7.0) | pyte 0.7.0 | Use Screen.dirty set to track changed lines for incremental refresh. |
| Claude Code raw ANSI output | Claude Code differential renderer | Late 2025 | Claude Code now emits minimal escape sequences, reducing PTY bandwidth. Good for our embedding. |
| Manually parsing Claude's cost | Claude Code statusline JSON | 2025-2026 | Statusline provides structured JSON with cost/tokens/context. However, this is a sideband mechanism, not in PTY output. |

**Deprecated/outdated:**
- `claude-code-sdk`: Deprecated, replaced by `claude-agent-sdk`. Neither is used in this phase (PTY approach).
- `textual-terminal`: Unmaintained, LGPL-3, described as "extremely slow" by Textual maintainer.
- `pyte.DiffScreen`: Deprecated since pyte 0.7.0, functionality merged into `Screen`.

## Open Questions

1. **Screen.buffer vs Screen.display for rendering**
   - What we know: `Screen.display` returns plain text strings (loses color). `Screen.buffer` has full `Char` objects with fg/bg/bold/etc.
   - What's unclear: Performance of iterating buffer cell-by-cell for every refresh vs. using `Screen.display` with `Text.from_ansi()`. The display property strips ANSI but Screen doesn't put ANSI codes into display -- it processes them into buffer attributes.
   - Recommendation: Start with `Screen.buffer` iteration for full color fidelity. Optimize later if profiling shows it's a bottleneck. Consider only re-rendering dirty lines (using `Screen.dirty` set).

2. **Claude Code's statusline JSON for cost/token data**
   - What we know: Claude Code has a `statusLine` mechanism that pipes JSON (with `cost.total_cost_usd`, `context_window.total_input_tokens`, etc.) to a configured script after each assistant message.
   - What's unclear: Can we configure a statusline script that writes to a pipe/file that our app reads? Or do we need to parse cost from the terminal output visually? The statusline runs INSIDE the Claude process -- not accessible from the parent.
   - Recommendation: Use a two-pronged approach: (1) Configure Claude Code's statusline to write to a known temp file, then read that file. (2) Also parse visible PTY output as a fallback. The statusline JSON is far more reliable than regex scraping.

3. **Key binding conflicts between Textual and PTY**
   - What we know: When the TerminalWidget has focus, most keys should go to the PTY. But some keys (Ctrl+B/E/R for panel switching, Ctrl+Q for quit) must be intercepted by Textual.
   - What's unclear: The exact boundary between "forward to PTY" and "handle in Textual". Claude Code itself uses Ctrl+C (interrupt), Ctrl+D (end of input), Escape (cancel).
   - Recommendation: Use `priority=True` on app-level bindings for panel focus (Ctrl+B/E/R) and quit (Ctrl+Q). Everything else forwarded to PTY when TerminalWidget has focus. Document this clearly.

4. **ptyprocess vs stdlib pty.fork()**
   - What we know: ptyprocess wraps pty.fork() with setwinsize, isalive, close. The pyte example uses raw pty.fork().
   - What's unclear: Whether ptyprocess adds meaningful value vs a thin wrapper around stdlib pty.
   - Recommendation: Start with stdlib `pty.fork()` + manual `setwinsize`/cleanup (following the proven pyte example). Add ptyprocess only if we need its additional lifecycle management features. This avoids an extra dependency.

5. **Scrollback in the terminal widget**
   - What we know: pyte's `HistoryScreen` supports scrollback with `prev_page()`/`next_page()`. Claude Code does NOT use the alternate screen buffer, so scrollback is expected.
   - What's unclear: How much scrollback to maintain. pyte's HistoryScreen default is 100 lines. User may want to scroll up to review earlier Claude output.
   - Recommendation: Use `pyte.HistoryScreen` with a generous history (e.g., 10000 lines). Map scroll events (mouse wheel, Shift+PageUp/Down) to pyte's `prev_page()`/`next_page()`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24.x |
| Config file | pyproject.toml `[tool.pytest.ini_options]` with `asyncio_mode = "auto"` |
| Quick run command | `uv run pytest tests/test_chat.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLAUDE-01 | Chat panel spawns claude PTY and renders output | integration | `uv run pytest tests/test_chat.py::test_pty_spawn_and_render -x` | Wave 0 |
| CLAUDE-01 | Keyboard input forwarded to PTY | integration | `uv run pytest tests/test_chat.py::test_key_forwarding -x` | Wave 0 |
| CLAUDE-02 | Claude inherits features (satisfied by design -- PTY) | manual-only | N/A (verify by running `claude` in PTY with CLAUDE.md present) | N/A |
| CLAUDE-03 | Claude output has markdown/syntax highlighting (ANSI) | integration | `uv run pytest tests/test_chat.py::test_ansi_color_rendering -x` | Wave 0 |
| CLAUDE-04 | Status indicator reflects Claude state | unit | `uv run pytest tests/test_status_parser.py -x` | Wave 0 |
| CLAUDE-05 | Token/cost display in status bar | unit | `uv run pytest tests/test_status_parser.py::test_cost_parsing -x` | Wave 0 |
| GRACEFUL | App works without claude CLI installed | integration | `uv run pytest tests/test_chat.py::test_graceful_no_claude -x` | Wave 0 |
| RESTART | Crash shows error + restart action | integration | `uv run pytest tests/test_chat.py::test_crash_recovery -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_chat.py tests/test_status_parser.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_chat.py` -- covers CLAUDE-01, CLAUDE-03, graceful degradation, restart
- [ ] `tests/test_status_parser.py` -- covers CLAUDE-04, CLAUDE-05 (unit tests for parsing)
- [ ] `tests/test_terminal_widget.py` -- covers PTY lifecycle, resize, key forwarding (may merge with test_chat.py)
- [ ] Note: Testing actual PTY spawning of `claude` is difficult in CI (requires the binary). Mock the PTY fd for unit tests; integration tests require claude installed.

## Sources

### Primary (HIGH confidence)
- [pyte terminal_emulator.py example](https://github.com/selectel/pyte/blob/master/examples/terminal_emulator.py) - Official pyte Textual terminal example with full PTY integration pattern
- [pyte API reference](https://pyte.readthedocs.io/en/latest/api.html) - Screen, DiffScreen, HistoryScreen, Stream, Char, Cursor API
- [ptyprocess API](https://ptyprocess.readthedocs.io/en/latest/api.html) - PtyProcess.spawn, read, write, setwinsize, isalive, close
- [Claude Code statusline docs](https://code.claude.com/docs/en/statusline) - JSON fields: cost, context_window, model, token counts
- [Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference) - CLI flags, --version (2.1.81 installed locally)
- [Textual Workers docs](https://textual.textualize.io/guide/workers/) - @work decorator, thread=True, call_from_thread
- [Textual Widget API](https://textual.textualize.io/api/widget/) - render(), render_line(), refresh(), events
- [Rich Text.from_ansi](https://rich.readthedocs.io/en/stable/reference/text.html) - Text.from_ansi() for ANSI -> Rich conversion

### Secondary (MEDIUM confidence)
- [Textual Discussion #5461](https://github.com/Textualize/textual/discussions/5461) - Will McGugan's recommendation: Log+Input for simple cases, pyte for full terminal
- [textual-terminal GitHub](https://github.com/mitosch/textual-terminal) - Reference implementation (rejected due to maintenance/performance/license issues)
- [Claude Code spinner animation reverse engineering](https://medium.com/@kyletmartinez/reverse-engineering-claudes-ascii-spinner-animation-eec2804626e0) - Spinner character set for status detection
- [Claude Code terminal rendering thread](https://www.threads.com/@boris_cherny/post/DSZbZatiIvJ/) - Differential renderer, no alternate screen buffer, Ink architecture

### Tertiary (LOW confidence)
- [ccstatusline](https://github.com/sirmalloc/ccstatusline) - Community statusline project (for pattern reference only)
- Status parsing regex patterns -- LOW confidence because Claude Code's output format changes frequently. These WILL need ongoing maintenance.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - ptyprocess 0.7.0 and pyte 0.8.2 are mature, stable, well-documented libraries with proven Textual integration (official pyte example)
- Architecture: HIGH - PTY-in-Widget pattern is proven by the pyte Textual example and textual-terminal. The approach is straightforward: spawn PTY, read in thread, feed to pyte, render via Rich.
- Status/cost parsing: MEDIUM - Claude Code's statusline JSON is well-documented, but extracting it from within the PTY is an open question. Terminal output scraping is inherently fragile. May need iteration.
- Key binding conflict resolution: MEDIUM - The boundary between Textual keys and PTY keys needs careful testing. Some edge cases may emerge.
- Pitfalls: HIGH - Well-understood from prior research, pyte/ptyprocess docs, and Textual discussion patterns

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (ptyprocess/pyte are stable; Claude Code CLI output format may change with weekly updates)

---
*Phase: 03-claude-code-integration*
*Research completed: 2026-03-22*
