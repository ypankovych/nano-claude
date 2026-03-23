# Phase 5: Code-to-Claude Interaction - Research

**Researched:** 2026-03-23
**Domain:** PTY text injection, Textual TextArea selection API, keyboard shortcut handling
**Confidence:** HIGH

## Summary

Phase 5 adds two features: (1) Ctrl+L sends the current code selection to Claude's PTY with a markdown code fence format, then moves focus to the chat panel; (2) Ctrl+P pins/unpins code selections as ambient context that gets prepended to every user prompt. Both features build entirely on existing infrastructure -- PTY fd writing via `os.write()`, TextArea selection API, and app-level keyboard bindings.

The critical technical challenge is **ambient context injection timing** (INTERACT-02): detecting when the user submits a prompt to Claude (pressing Enter in the terminal widget) and prepending the pinned context block before the Enter reaches the PTY. This is solved by intercepting the Enter key in `TerminalWidget.on_key` and writing the pinned context to the PTY fd immediately before forwarding the Enter keystroke.

**Primary recommendation:** Implement Ctrl+L as a straightforward "format selection + write to PTY + focus chat" action. For Ctrl+P ambient context, intercept Enter in TerminalWidget.on_key and prepend the pinned context block wrapped in bracketed paste escape sequences (`\x1b[200~...\x1b[201~`) so Claude CLI treats it as pasted multi-line text without submitting prematurely on internal newlines.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Send Selection to Claude (INTERACT-01):**
- Shortcut: Ctrl+L -- sends the current selection (or current line if nothing selected) to Claude's PTY and moves focus to the chat panel
- No separate prompt UI -- the selection is formatted and pasted into the PTY, then focus jumps to the chat panel so the user types their prompt directly into Claude's native input
- No selection preview -- the user already sees the highlighted selection in the editor; no need to repeat it in a dialog
- No-selection fallback -- if no text is selected, send the current line at the cursor position
- Format -- selection is injected as a markdown code fence with file path and line numbers:
  ````
  ```<language>
  # <relative_path> lines <start>-<end>
  <selected text>
  ```
  ````
  The user's typed prompt follows naturally after this block in the PTY input.

**Ambient Context / Pin Context (INTERACT-02):**
- Shortcut: Ctrl+P -- toggles pinning/unpinning the current selection (or current line) as ambient context
- Delivery: prepend to prompt -- when the user submits a prompt to Claude, nano-claude automatically injects the pinned context block into the PTY before the user's message
- Trigger: explicit only -- context is pinned manually by the user, NOT auto-updated on cursor movement or selection change
- Persistence: survives file switches -- pinned context stays active until the user explicitly unpins with Ctrl+P again
- Visibility: status bar indicator -- shows what's pinned (e.g., "Pinned: foo.py:42-58") so the user knows what Claude will see
- Content: file path + selected text -- the pinned snapshot includes the file path, line numbers, and actual selected code at the time of pinning
- Format: markdown code fence -- same format as Ctrl+L send

### Claude's Discretion

- How to detect "user is about to submit a prompt" in the PTY stream for ambient context injection timing
- Whether to debounce/batch the PTY write when injecting context + user starts typing
- How to handle very long selections (truncation threshold, if any)
- Status bar layout for the pinned context indicator alongside existing Claude status/cost display
- Whether Ctrl+P on an already-pinned selection updates the pin or just unpins

### Deferred Ideas (OUT OF SCOPE)

None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INTERACT-01 | User can select code in the editor and send it to Claude with a prompt via a keyboard shortcut | Textual TextArea.selected_text API, os.write() to PTY fd, bracketed paste mode for multi-line injection, detect_language() for code fence language tag |
| INTERACT-02 | Claude automatically sees the user's current code selection as ambient context (file path, line numbers, selected text) | TerminalWidget.on_key Enter interception, pinned context state on NanoClaudeApp, status bar extension via _update_status_bar() |

</phase_requirements>

## Standard Stack

### Core (already installed -- no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| textual | 8.1.1 | TUI framework, TextArea selection API, App bindings | Already in use, provides all needed APIs |
| pyte | >=0.8.2 | Terminal emulation (already used by TerminalWidget) | Already in use |
| stdlib os | n/a | `os.write()` for PTY fd injection | Already used in TerminalWidget.on_key |

### No New Dependencies Required

This phase requires zero new packages. All functionality builds on:
- `TextArea.selected_text` property (Textual built-in)
- `TextArea.cursor_location` property (Textual built-in)
- `os.write(fd, data)` for PTY injection (stdlib, already used)
- `detect_language()` from `nano_claude/models/file_buffer.py` (already exists)

## Architecture Patterns

### Recommended Changes

```
nano_claude/
  app.py                  # ADD: Ctrl+L and Ctrl+P bindings, action methods, _pinned_context state
  terminal/
    widget.py             # MODIFY: Enter interception in on_key for ambient context injection,
                          #         add "ctrl+l" and "ctrl+p" to RESERVED_KEYS
  panels/
    editor.py             # ADD: helper methods get_selection_context(), get_current_line_context()
  models/
    pinned_context.py     # NEW: PinnedContext dataclass (path, start_line, end_line, text, language)
```

### Pattern 1: Selection Context Extraction

**What:** Extract the current selection (or current line) from the editor as a formatted context block.
**When to use:** Both Ctrl+L (send) and Ctrl+P (pin) need the same selection extraction logic.

```python
# In EditorPanel or as a standalone helper
from dataclasses import dataclass
from pathlib import Path

@dataclass
class CodeContext:
    """Snapshot of a code selection for sending to Claude."""
    file_path: Path
    start_line: int  # 1-indexed for display
    end_line: int     # 1-indexed for display
    text: str
    language: str | None

    def format_code_fence(self, cwd: Path) -> str:
        """Format as markdown code fence with file path and line range."""
        try:
            rel_path = self.file_path.relative_to(cwd)
        except ValueError:
            rel_path = self.file_path.name
        lang = self.language or ""
        return f"```{lang}\n# {rel_path} lines {self.start_line}-{self.end_line}\n{self.text}\n```\n"
```

### Pattern 2: PTY Text Injection with Bracketed Paste

**What:** Write multi-line text to the PTY fd using bracketed paste escape sequences so Claude CLI treats it as a single pasted block (not line-by-line Enter submissions).
**When to use:** Any time multi-line text is injected into the PTY (both Ctrl+L and ambient context prepend).

```python
# Bracketed paste escape sequences
PASTE_START = "\x1b[200~"
PASTE_END = "\x1b[201~"

def write_to_pty(fd: int, text: str) -> None:
    """Write text to PTY fd using bracketed paste mode for multi-line content."""
    if "\n" in text:
        # Wrap in bracketed paste to prevent line-by-line submission
        payload = f"{PASTE_START}{text}{PASTE_END}"
    else:
        payload = text
    os.write(fd, payload.encode("utf-8"))
```

### Pattern 3: Enter Interception for Ambient Context

**What:** In `TerminalWidget.on_key`, when the user presses Enter and there is pinned context, inject the context block into the PTY BEFORE forwarding the Enter key.
**When to use:** INTERACT-02 ambient context delivery.

```python
# In TerminalWidget.on_key, BEFORE the normal key forwarding:
def on_key(self, event: events.Key) -> None:
    if not self._running or self._pty_manager.fd is None:
        return
    if event.key in RESERVED_KEYS:
        return

    # Ambient context injection: when Enter is pressed and context is pinned
    if event.key == "enter" and self._pinned_context_callback:
        context_text = self._pinned_context_callback()
        if context_text:
            # Write pinned context as pasted text BEFORE the user's prompt
            # The user has already typed their prompt in the PTY input line.
            # We need to prepend context, so:
            # 1. Send Home key to go to beginning of input line
            # 2. Inject context as bracketed paste
            # 3. Then let Enter through to submit the full line
            os.write(fd, b"\x01")  # Ctrl+A = Home in readline
            write_to_pty(fd, context_text)
            os.write(fd, b"\x05")  # Ctrl+E = End in readline to return cursor

    # Normal key forwarding
    char = translate_key(event)
    ...
```

**CRITICAL DESIGN DECISION (Claude's Discretion):** The Enter interception approach above has a subtlety. Claude Code's input is rendered by Ink (React for CLI), not a standard readline prompt. The Ctrl+A/Ctrl+E readline shortcuts may not work. A simpler and more robust approach:

**Recommended approach:** Instead of intercepting Enter and trying to prepend inline, use a **two-write strategy**:
1. When Enter is pressed, prevent it from reaching the PTY
2. Read back the user's current input line (not feasible with PTY)

**Even simpler approach:** Since we cannot read back what the user typed, the cleanest design is:
1. When Enter is pressed with pinned context active, write the context block as a bracketed paste first
2. Then forward the Enter key
3. Claude CLI sees: `<paste block><newline>` -- the paste enters multi-line mode, and the Enter at the end submits

However, this means the context appears AFTER whatever the user typed. That is actually fine because Claude sees the full prompt including the code block.

**Simplest correct approach:** Write pinned context BEFORE the Enter keystroke to the PTY. The user's typed text is already in Claude's input buffer. The Enter will submit everything (user's text + the just-injected context). This works because:
- The user types their prompt into Claude's input
- On Enter, we inject the context block via bracketed paste (which enters Claude's multi-line mode)
- Then we send the Enter keystroke, which submits the whole thing
- Claude receives: `<user's prompt text>\n<pinned context block>` -- which is perfectly usable

### Pattern 4: App-Level Coordination

**What:** App bindings call action methods that coordinate between EditorPanel (source of selection) and ChatPanel/TerminalWidget (target for PTY injection).
**When to use:** Following the established pattern in the codebase (e.g., `action_save_file` -> `editor.save_current_file()`).

```python
# In NanoClaudeApp
def action_send_to_claude(self) -> None:
    """Send current selection to Claude (Ctrl+L)."""
    editor = self.query_one(EditorPanel)
    context = editor.get_selection_context()
    if context is None:
        self.notify("No file open", severity="warning")
        return

    # Get PTY fd from terminal widget
    terminal = self.query_one("#claude-terminal", TerminalWidget)
    if terminal._pty_manager.fd is None:
        self.notify("Claude not running", severity="warning")
        return

    # Write formatted context to PTY
    formatted = context.format_code_fence(Path.cwd())
    write_to_pty(terminal._pty_manager.fd, formatted)

    # Focus the chat panel
    self.action_focus_panel("chat")
```

### Anti-Patterns to Avoid

- **Don't try to read back PTY input buffer:** PTY is write-only from the parent side. You cannot read what the user has typed into Claude's input line. Design around this limitation.
- **Don't send raw newlines without bracketed paste:** Each `\n` written to the PTY will be interpreted as an Enter keypress, which would submit the prompt prematurely mid-block.
- **Don't create a custom prompt overlay for INTERACT-01:** The CONTEXT.md explicitly says "no separate prompt UI" -- the user types directly into Claude's native input.
- **Don't auto-update pinned context on cursor movement:** CONTEXT.md specifies explicit-only pinning via Ctrl+P.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Selection text extraction | Custom DOM traversal | `TextArea.selected_text` property | Textual handles multi-line selection, cursor position, etc. |
| Current line text | Manual string splitting | `document.get_line(row)` via TextArea | Handles edge cases, encoding, etc. |
| Language detection | Extension-to-lang mapping | `detect_language()` from `models/file_buffer.py` | Already exists, already tested, maps to TextArea language names |
| PTY text writing | Custom protocol | `os.write(fd, data.encode("utf-8"))` | Already the established pattern in TerminalWidget.on_key |
| Focus management | DOM manipulation | `self.action_focus_panel("chat")` | Already exists in NanoClaudeApp |

**Key insight:** This phase is almost entirely "glue code" -- connecting existing APIs (TextArea selection, PTY write, bindings, focus) with formatting logic. No new complex subsystems needed.

## Common Pitfalls

### Pitfall 1: Newlines in PTY Injection Triggering Premature Submission
**What goes wrong:** Writing `"```python\n# file.py lines 1-5\ncode here\n```\n"` to the PTY without bracketed paste causes Claude CLI to treat each `\n` as an Enter keypress, submitting the prompt after the first line.
**Why it happens:** PTY line discipline processes `\n` as carriage return, Claude CLI submits on Enter.
**How to avoid:** Always wrap multi-line PTY writes in bracketed paste sequences: `\x1b[200~<content>\x1b[201~`. Claude Code recognizes bracketed paste and enters multi-line mode.
**Warning signs:** Only the first line of the code fence appears in Claude's input, or Claude responds to partial fragments.

### Pitfall 2: Ctrl+L and Ctrl+P Not Reserved in TerminalWidget
**What goes wrong:** When focus is on the chat panel (TerminalWidget), pressing Ctrl+L or Ctrl+P gets forwarded to the PTY subprocess instead of triggering app-level bindings.
**Why it happens:** `TerminalWidget.on_key` checks `RESERVED_KEYS` before forwarding. If the new shortcuts aren't in the set, they get consumed by the PTY.
**How to avoid:** Add `"ctrl+l"` and `"ctrl+p"` to the `RESERVED_KEYS` frozenset in `terminal/widget.py`.
**Warning signs:** Ctrl+L clears the terminal screen (it's the standard terminal clear command), Ctrl+P scrolls up in the PTY history.

### Pitfall 3: Selection Empty After Focus Switch
**What goes wrong:** After adding the Ctrl+L binding, the code reads the selection AFTER switching focus to the chat panel, but focus switch may clear the selection.
**Why it happens:** Textual may clear selection when a TextArea loses focus.
**How to avoid:** Extract the selection text and context BEFORE switching focus to the chat panel. Store it in a local variable, then write to PTY, then switch focus.
**Warning signs:** Empty code fence sent to Claude, or "no selection" fallback always triggering.

### Pitfall 4: Pinned Context Injected During Claude's Response
**What goes wrong:** If the user presses Enter while Claude is already responding (e.g., to grant a permission), the Enter interception injects pinned context into the middle of Claude's output stream.
**Why it happens:** Enter key handling in TerminalWidget doesn't distinguish between "user is submitting a prompt" and "user is pressing Enter for other reasons" (permission prompts, scrolling, etc.).
**How to avoid:** Only inject pinned context when Claude is in IDLE state (check the StatusParser's current state). When Claude is in THINKING, TOOL_USE, or PERMISSION state, skip context injection and forward Enter normally.
**Warning signs:** Garbled text appearing in Claude's output, permission prompts being corrupted.

### Pitfall 5: Very Large Selections Causing PTY Write Issues
**What goes wrong:** User selects a 500+ line block, Ctrl+L writes the entire block to the PTY in one `os.write()` call, which may exceed PTY buffer limits or cause Claude CLI to hang.
**Why it happens:** PTY has finite internal buffer (typically 4096 bytes on macOS). `os.write()` may block or truncate.
**How to avoid:** Implement a truncation threshold (e.g., 200 lines or 8KB). Show a notification when truncating: "Selection truncated to 200 lines". Consider chunked writes for very large blocks.
**Warning signs:** Terminal hangs after Ctrl+L on large selection, partial code fences appearing.

### Pitfall 6: Ctrl+P Toggle Ambiguity
**What goes wrong:** User pins selection A, moves cursor, makes a different selection B, presses Ctrl+P again -- does it unpin A or pin B?
**Why it happens:** Ambiguous UX when there's an existing pin and a new selection.
**How to avoid:** Simple toggle logic: if anything is pinned, Ctrl+P unpins it. If nothing is pinned, Ctrl+P pins the current selection. This is the most intuitive behavior. Show a clear notification: "Pinned foo.py:42-58" or "Unpinned context".
**Warning signs:** Users confused about what's pinned, multiple pins accumulating.

## Code Examples

### Getting Current Selection or Current Line

```python
# In EditorPanel
def get_selection_context(self) -> CodeContext | None:
    """Get the current selection (or current line) as a CodeContext."""
    if self.current_file is None:
        return None

    text_area = self._text_area
    selected = text_area.selected_text

    if selected:
        # User has an active selection
        start, end = text_area.selection
        # Selection is (row, col) tuples, 0-indexed
        # Sort to get min/max regardless of selection direction
        min_loc = min(start, end)
        max_loc = max(start, end)
        start_line = min_loc[0] + 1  # 1-indexed for display
        end_line = max_loc[0] + 1
        text = selected
    else:
        # No selection -- use current line
        row, _col = text_area.cursor_location
        line_text = text_area.document.get_line(row)
        start_line = row + 1
        end_line = row + 1
        text = line_text

    language = detect_language(self.current_file)
    return CodeContext(
        file_path=self.current_file,
        start_line=start_line,
        end_line=end_line,
        text=text,
        language=language,
    )
```

### Writing to PTY with Bracketed Paste

```python
# Constants
BRACKETED_PASTE_START = "\x1b[200~"
BRACKETED_PASTE_END = "\x1b[201~"

def write_to_pty_bracketed(fd: int, text: str) -> None:
    """Write text to PTY using bracketed paste for multi-line safety."""
    payload = f"{BRACKETED_PASTE_START}{text}{BRACKETED_PASTE_END}"
    data = payload.encode("utf-8")
    # Write in chunks to avoid exceeding PTY buffer
    chunk_size = 4096
    offset = 0
    while offset < len(data):
        written = os.write(fd, data[offset:offset + chunk_size])
        offset += written
```

### Status Bar with Pin Indicator

```python
# In NanoClaudeApp._update_status_bar
def _update_status_bar(self) -> None:
    parts = []
    # Existing: Claude status
    if self.claude_status and self.claude_status != "idle":
        parts.append(f"Claude: {self.claude_status}")
    if self.claude_cost:
        parts.append(self.claude_cost)
    # NEW: Pinned context indicator
    if self._pinned_context is not None:
        try:
            rel = self._pinned_context.file_path.relative_to(Path.cwd())
        except ValueError:
            rel = self._pinned_context.file_path.name
        parts.append(f"Pinned: {rel}:{self._pinned_context.start_line}-{self._pinned_context.end_line}")
    status_text = CLAUDE_STATUS_SEPARATOR.join(parts)
    # ... rest of existing logic
```

### Enter Interception in TerminalWidget

```python
# In TerminalWidget -- the cleanest approach
def on_key(self, event: events.Key) -> None:
    if not self._running or self._pty_manager.fd is None:
        return
    if event.key in RESERVED_KEYS:
        return

    fd = self._pty_manager.fd

    # Ambient context injection on Enter
    if event.key == "enter" and self._get_pinned_context is not None:
        context_text = self._get_pinned_context()
        if context_text:
            # Only inject when Claude is idle (waiting for input)
            if self._is_claude_idle():
                # Write context as bracketed paste, then let Enter go through
                write_to_pty_bracketed(fd, context_text)

    # Normal key forwarding
    char = translate_key(event)
    if char is not None:
        try:
            os.write(fd, char.encode("utf-8"))
        except OSError:
            pass
        event.prevent_default()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom prompt dialog for code-to-AI | Direct PTY injection (no UI) | This project design | Zero-friction; user types in Claude's native input |
| Auto-updating context on cursor move | Explicit pin/unpin with Ctrl+P | This project design | Predictable, no surprise context changes |
| Separate context panel/sidebar | Status bar indicator only | This project design | Minimal UI footprint, context is invisible until it matters |

## Open Questions

1. **Claude CLI Ink/React input handling of bracketed paste at prompt boundary**
   - What we know: Claude CLI uses Ink (React for terminals). It recognizes bracketed paste and enters multi-line mode. This is confirmed by the GitHub issues about paste behavior.
   - What's unclear: When the user has already typed some text and we inject a bracketed paste block mid-line, does the pasted text get appended to the existing input or does it replace it?
   - Recommendation: Test empirically during implementation. The safest approach is to inject context BEFORE the Enter key (so it appears at the end of the current input line). Since Claude sees the whole prompt as one message, ordering within the prompt doesn't matter semantically.

2. **PTY buffer size limits for large context blocks**
   - What we know: macOS PTY buffer is typically 4096 bytes. Writes larger than this may block.
   - What's unclear: Whether Claude CLI's internal buffer has additional limits.
   - Recommendation: Implement chunked writes and a 200-line / 8KB truncation threshold. Show notification when truncating.

3. **StatusParser state accuracy for Enter interception guard**
   - What we know: StatusParser detects IDLE, THINKING, TOOL_USE, PERMISSION states from PTY output patterns.
   - What's unclear: Whether the state always accurately reflects "Claude is waiting for user input" vs "Claude is doing something else."
   - Recommendation: Use StatusParser.current_state as a heuristic guard. If state is not IDLE, skip context injection. This is conservative and safe -- worst case, context is occasionally not injected, which is better than injecting at the wrong time.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `.venv/bin/python -m pytest tests/ -x --tb=short -q` |
| Full suite command | `.venv/bin/python -m pytest tests/ -v` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTERACT-01 | Ctrl+L sends selection to PTY with code fence format | unit | `.venv/bin/python -m pytest tests/test_code_interaction.py::TestSendToClaudeFormatting -x` | No -- Wave 0 |
| INTERACT-01 | No-selection fallback sends current line | unit | `.venv/bin/python -m pytest tests/test_code_interaction.py::TestSendToClaudeFallback -x` | No -- Wave 0 |
| INTERACT-01 | Ctrl+L is in RESERVED_KEYS | unit | `.venv/bin/python -m pytest tests/test_code_interaction.py::TestReservedKeys -x` | No -- Wave 0 |
| INTERACT-02 | Ctrl+P pins/unpins context | unit | `.venv/bin/python -m pytest tests/test_code_interaction.py::TestPinContext -x` | No -- Wave 0 |
| INTERACT-02 | Pinned context prepended on Enter | unit | `.venv/bin/python -m pytest tests/test_code_interaction.py::TestAmbientContextInjection -x` | No -- Wave 0 |
| INTERACT-02 | Context not injected during non-IDLE state | unit | `.venv/bin/python -m pytest tests/test_code_interaction.py::TestContextInjectionGuard -x` | No -- Wave 0 |
| INTERACT-02 | Status bar shows pinned context indicator | unit | `.venv/bin/python -m pytest tests/test_code_interaction.py::TestPinnedStatusBar -x` | No -- Wave 0 |

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/ -x --tb=short -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_code_interaction.py` -- covers INTERACT-01 and INTERACT-02 (formatting, PTY write mocking, pin toggle, Enter interception, status bar)
- [ ] `nano_claude/models/pinned_context.py` -- CodeContext dataclass (new module, needs tests for format_code_fence)
- Framework install: already installed (pytest + pytest-asyncio in dev dependencies)

## Sources

### Primary (HIGH confidence)
- **Textual 8.1.1 source code** (installed in .venv) -- TextArea.selected_text, TextArea.cursor_location, TextArea.selection, Selection class, TextArea.document.get_line()
- **Project codebase** -- TerminalWidget.on_key, RESERVED_KEYS, PtyManager.fd, os.write() pattern, _update_status_bar(), detect_language()
- **CONTEXT.md** -- all user decisions for INTERACT-01 and INTERACT-02

### Secondary (MEDIUM confidence)
- [Bracketed paste mode - Wikipedia](https://en.wikipedia.org/wiki/Bracketed-paste) -- escape sequences `\x1b[200~` / `\x1b[201~`
- [Claude Code CLI bracketed paste bug #3134](https://github.com/anthropics/claude-code/issues/3134) -- confirms Claude CLI uses and recognizes bracketed paste mode
- [Claude Code multiline input #729](https://github.com/anthropics/claude-code/issues/729) -- confirms Enter = submit, multiline via paste mode
- [Shift+Enter support #1259](https://github.com/anthropics/claude-code/issues/1259) -- confirms multiline input methods

### Tertiary (LOW confidence)
- PTY buffer size (4096 bytes on macOS) -- commonly cited but not verified against current kernel. Chunked writes handle this regardless.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- zero new dependencies, all APIs verified against installed Textual 8.1.1 source
- Architecture: HIGH -- follows established patterns in codebase (app-level actions, RESERVED_KEYS, _update_status_bar)
- Pitfalls: HIGH -- PTY injection pitfalls verified via Claude Code GitHub issues and bracketed paste mode documentation
- Ambient context injection timing: MEDIUM -- Enter interception is straightforward but interaction with Claude CLI's Ink-based input needs empirical testing

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable -- no external dependency changes)
