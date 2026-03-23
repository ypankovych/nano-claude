# Phase 6: Terminal Panel - Research

**Researched:** 2026-03-23
**Domain:** TUI terminal panel with PTY, tabbed sessions, Textual layout integration
**Confidence:** HIGH

## Summary

Phase 6 adds a toggleable terminal panel to nano-claude so users can run shell commands without leaving the TUI. The existing codebase already has all the infrastructure needed: `TerminalWidget` with pyte-backed PTY rendering, `PtyManager` for subprocess lifecycle, `BasePanel` for container styling, and established patterns for panel toggling (add_class/remove_class with "hidden"), focus management (Tab/Shift+Tab cycling, Ctrl+letter direct focus), and PTY exit handling (PtyExited message).

The core implementation involves: (1) wrapping the existing three-panel `Horizontal` in a `Vertical` container with the new terminal panel below, (2) creating a `TerminalPanel` that manages multiple TerminalWidget instances via Textual's `ContentSwitcher`, (3) implementing the "minimize to status line" behavior by toggling between a full terminal view and a 1-row status bar, and (4) integrating with the existing focus system by adding `ctrl+t` to RESERVED_KEYS and the app BINDINGS.

**Primary recommendation:** Reuse TerminalWidget directly (no subclass needed), compose TerminalPanel as BasePanel with a custom tab bar (Static-based, not Textual's Tabs widget) + ContentSwitcher for multiple sessions. Use CSS height toggling for minimize/restore behavior.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Bottom panel** -- full-width horizontal panel below the editor/chat row, like VS Code's integrated terminal
- **Fixed height** -- not resizable via Ctrl+=/- (simpler implementation, consistent terminal experience)
- **Hidden by default** -- app launches with the clean three-panel layout; user toggles terminal open when needed
- **Minimize to status line** -- when toggled off, collapses to a thin bar showing "Terminal (running)" instead of hiding completely; shell process keeps running in background
- **Layout structure** -- main layout becomes vertical: top row (Horizontal with tree/editor/chat) + bottom (terminal panel or status line)
- **Spawn user's $SHELL** -- respects user's shell preference; falls back to /bin/sh if $SHELL is unset
- **Start in project root** -- terminal cwd is Path.cwd(); no automatic sync with file tree navigation
- **On shell exit** -- show exit status and restart hint (same pattern as ChatPanel's PtyExited handling)
- **Multiple tabs** -- tab bar at top of terminal panel; each tab is independent shell session with own PTY
- **New tab: Ctrl+N** (only when terminal panel is focused); spawns fresh $SHELL in project root
- **Close tab: Ctrl+W** (only when terminal is focused); closes active tab and its PTY; if last tab, minimize
- **Ctrl+T** -- toggle terminal visibility AND focus; if hidden: show + focus; if visible but not focused: focus; if focused: minimize to status line
- **Tab/Shift+Tab** cycling includes terminal panel when visible
- **Ctrl+T must be added to RESERVED_KEYS** in TerminalWidget (both Claude terminal and shell terminal)

### Claude's Discretion
- Tab bar visual design (how tabs are displayed, active tab indicator, tab naming)
- Terminal panel height (fixed value -- suggest ~30% of terminal height or a reasonable row count)
- Status line appearance when minimized (thin bar styling, colors)
- How to handle PTY resize when terminal panel height changes (e.g., window resize)
- Whether to reuse TerminalWidget directly or create a ShellTerminalWidget subclass
- Tab switching shortcut (if any beyond clicking tabs)
- Maximum number of tabs (if any limit)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TERM-01 | User can toggle a terminal panel via a keyboard shortcut | Ctrl+T binding with three-state toggle (hidden->show+focus, visible-unfocused->focus, focused->minimize). Layout restructured as Vertical(main-panels, terminal-panel). CSS .hidden/.minimized classes for state. |
| TERM-02 | Terminal panel is a full PTY-based terminal supporting interactive commands | Reuse existing TerminalWidget + PtyManager unchanged. Spawn $SHELL (or /bin/sh fallback). pyte handles ANSI colors. Multiple tabs via ContentSwitcher with independent TerminalWidget per tab. |
| TERM-03 | User can switch focus between terminal panel and other panels with keyboard shortcuts | Terminal added to Tab/Shift+Tab focus chain automatically (Textual focus_chain includes all displayed focusable widgets in DOM order). Ctrl+T for direct terminal focus. RESERVED_KEYS updated to prevent PTY from consuming app shortcuts. |
</phase_requirements>

## Standard Stack

### Core (already in project -- no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| textual | 8.1.1 | TUI framework | Already installed; provides ContentSwitcher, Widget, focus management |
| pyte | 0.8.2+ | Terminal emulation | Already used by TerminalWidget; handles ANSI parsing for shell output |

### Supporting (Textual built-ins, no install)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| ContentSwitcher | (textual built-in) | Switch between multiple TerminalWidgets | Manages tab content; uses display=True/False so only active tab is focusable |
| Static | (textual built-in) | Tab bar rendering | Lightweight tab bar display; no focus capture issues |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ContentSwitcher + custom tab bar | TabbedContent | TabbedContent's Tabs widget is focusable and uses left/right arrows, which conflicts with TerminalWidget's need to capture arrow keys. Custom approach is simpler. |
| Custom tab bar (Static) | Textual Tabs widget | Tabs widget has can_focus=True; would appear in focus chain and intercept arrow keys. Static tab bar avoids focus issues. |
| Reuse TerminalWidget | Subclass ShellTerminalWidget | TerminalWidget already accepts any command parameter. The only Claude-specific code is StatusParser (used but harmless on non-Claude output) and input buffer (no effect without pinned context). Direct reuse is cleaner. |

**Installation:**
```bash
# No new dependencies needed -- all infrastructure already exists
```

## Architecture Patterns

### Recommended Project Structure
```
nano_claude/
  panels/
    terminal.py          # NEW: TerminalPanel with tab management
  terminal/
    widget.py            # MODIFY: add ctrl+t, ctrl+n, ctrl+w to RESERVED_KEYS
  app.py                 # MODIFY: layout, bindings, focus, shutdown
  styles.tcss            # MODIFY: terminal panel CSS
  config/
    settings.py          # MODIFY: terminal constants
```

### Pattern 1: Layout Restructure (Vertical Wrapper)
**What:** Wrap existing Horizontal (main-panels) + TerminalPanel in a Vertical
**When to use:** Always -- this is the structural change for the terminal panel
**Example:**
```python
# In NanoClaudeApp.compose():
def compose(self) -> ComposeResult:
    yield Header()
    with Vertical(id="app-layout"):
        with Horizontal(id="main-panels"):
            yield FileTreePanel(id="file-tree")
            yield EditorPanel(id="editor")
            yield ChatPanel(id="chat")
        yield TerminalPanel(id="terminal-panel")
    yield Footer()
```
**Source:** Existing compose() pattern in app.py + CONTEXT.md layout decision

### Pattern 2: TerminalPanel with ContentSwitcher
**What:** TerminalPanel manages multiple shell sessions via ContentSwitcher
**When to use:** Core pattern for multi-tab terminal
**Example:**
```python
class TerminalPanel(BasePanel):
    """Bottom panel: shell terminal with tabbed sessions."""

    _tab_counter: int = 0

    def compose(self) -> ComposeResult:
        self.panel_title = "Terminal"
        yield Static("", id="terminal-tab-bar", classes="tab-bar")
        yield ContentSwitcher(id="terminal-switcher")
        # Status line shown when minimized
        yield Static("Terminal (idle)", id="terminal-status-line")

    def add_tab(self) -> None:
        """Create a new terminal tab with fresh shell session."""
        self._tab_counter += 1
        tab_id = f"shell-{self._tab_counter}"
        shell = os.environ.get("SHELL", "/bin/sh")
        terminal = TerminalWidget(command=shell, id=tab_id)
        switcher = self.query_one("#terminal-switcher", ContentSwitcher)
        switcher.mount(terminal)
        switcher.current = tab_id
        self._update_tab_bar()
        terminal.focus()

    def close_active_tab(self) -> None:
        """Close the active terminal tab."""
        switcher = self.query_one("#terminal-switcher", ContentSwitcher)
        if switcher.current is None:
            return
        current_id = switcher.current
        # Stop PTY before removing
        try:
            terminal = switcher.get_child_by_id(current_id)
            if isinstance(terminal, TerminalWidget):
                terminal.stop_pty()
        except Exception:
            pass
        # Switch to another tab or minimize
        remaining = [c for c in switcher.children if c.id != current_id]
        if remaining:
            switcher.current = remaining[-1].id
        else:
            switcher.current = None
        terminal.remove()
        self._update_tab_bar()
        if not remaining:
            self._minimize()
```
**Source:** ContentSwitcher API (display=True/False for active child), ChatPanel exit pattern

### Pattern 3: Three-State Toggle (Ctrl+T)
**What:** Ctrl+T has three behaviors depending on terminal state
**When to use:** The toggle action handler in app.py
**Example:**
```python
def action_toggle_terminal(self) -> None:
    """Toggle terminal: hidden->show+focus, visible-unfocused->focus, focused->minimize."""
    try:
        panel = self.query_one("#terminal-panel", TerminalPanel)
    except Exception:
        return

    if panel.is_minimized:
        # Show + focus
        panel.restore()
        self._focus_terminal()
    elif not self._panel_has_focus(panel):
        # Visible but not focused: just focus
        self._focus_terminal()
    else:
        # Focused: minimize
        panel.minimize()

def _focus_terminal(self) -> None:
    """Focus the active terminal widget in the terminal panel."""
    try:
        panel = self.query_one("#terminal-panel", TerminalPanel)
        switcher = panel.query_one("#terminal-switcher", ContentSwitcher)
        if switcher.current:
            terminal = switcher.get_child_by_id(switcher.current)
            terminal.focus()
    except Exception:
        pass
```
**Source:** CONTEXT.md Ctrl+T behavior spec, existing action_toggle_file_tree() pattern

### Pattern 4: Minimize to Status Line
**What:** Instead of display:none, collapse terminal to a 1-row status indicator
**When to use:** When terminal is toggled off with running sessions
**Example:**
```python
# In TerminalPanel:
is_minimized = reactive(True)  # Start minimized (hidden by default)

def minimize(self) -> None:
    """Collapse to status line, keeping PTY processes alive."""
    self.is_minimized = True

def restore(self) -> None:
    """Expand to full terminal view."""
    self.is_minimized = True
    # Ensure at least one tab exists
    switcher = self.query_one("#terminal-switcher", ContentSwitcher)
    if not switcher.children:
        self.add_tab()
    self.is_minimized = False

def watch_is_minimized(self, minimized: bool) -> None:
    """Toggle between full view and status line."""
    tab_bar = self.query_one("#terminal-tab-bar")
    switcher = self.query_one("#terminal-switcher")
    status = self.query_one("#terminal-status-line")
    if minimized:
        tab_bar.display = False
        switcher.display = False
        status.display = True
        self.styles.height = "auto"  # Shrink to status line height
    else:
        tab_bar.display = True
        switcher.display = True
        status.display = False
        self.styles.height = "30%"  # Or fixed row count
```
**Source:** CONTEXT.md minimize decision, existing toggle pattern (add_class/remove_class)

### Pattern 5: RESERVED_KEYS Update
**What:** Add new shortcuts to RESERVED_KEYS so PTY doesn't consume them
**When to use:** Must be done for both Claude terminal and shell terminals
**Example:**
```python
# In terminal/widget.py:
RESERVED_KEYS: frozenset[str] = frozenset({
    # ... existing keys ...
    "ctrl+t",   # Toggle terminal panel
    "ctrl+n",   # New terminal tab (when terminal focused)
    "ctrl+w",   # Close terminal tab (when terminal focused)
})
```
**Source:** CONTEXT.md requirement, existing RESERVED_KEYS pattern

### Anti-Patterns to Avoid
- **Using TabbedContent for terminal tabs:** The Tabs widget (part of TabbedContent) is focusable and uses left/right arrows for tab switching. This conflicts with TerminalWidget needing to capture arrow keys for shell navigation. Use ContentSwitcher with a custom non-focusable tab bar instead.
- **Subclassing TerminalWidget for shell:** TerminalWidget already takes a `command` parameter. The StatusParser runs on non-Claude output harmlessly (no patterns match). The input buffer for ambient context injection requires both `_get_pinned_context` being set AND `ClaudeState.IDLE` -- neither happens with shell output. Direct reuse is correct.
- **Using display:none for minimize:** The CONTEXT.md explicitly says "collapses to a thin bar showing Terminal (running)". Full hide loses the visual indicator. Use height collapse instead.
- **Spawning shell with login flag (-l):** The pty.fork() child already inherits the parent's environment. Interactive shells (zsh, bash) load .zshrc/.bashrc by default when run from a PTY. Adding -l could cause double-sourcing of profile files.
- **Making the tab bar focusable:** If the tab bar takes focus, Tab/Shift+Tab cycling will stop at the tab bar instead of the terminal content. The tab bar should be non-focusable (Static/custom widget with can_focus=False).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PTY subprocess management | Custom PTY code | Existing PtyManager | Already handles spawn, resize, stop, signal handling |
| Terminal emulation | Custom ANSI parser | Existing TerminalWidget + pyte | 30fps throttle, ANSI colors, resize, key translation already working |
| Multi-content switching | Manual display toggling | ContentSwitcher | Built-in display=True/False management, focus chain exclusion for hidden content |
| Panel exit handling | Custom exit flow | PtyExited message pattern | ChatPanel already demonstrates the pattern; reuse for shell exit |
| Shell command resolution | Custom PATH lookup | `os.environ.get("SHELL", "/bin/sh")` | Standard Unix convention; shutil.which() unnecessary for $SHELL |

**Key insight:** Phase 6 is almost entirely a composition phase -- the hard problems (PTY management, terminal emulation, key translation, ANSI rendering) are already solved. The work is composing existing pieces into a new container with tab management and toggle behavior.

## Common Pitfalls

### Pitfall 1: Focus Trap in Tab Bar
**What goes wrong:** If using Textual's Tabs widget for the tab bar, it captures focus and arrow keys. Users get stuck in the tab bar when they want to type in the terminal.
**Why it happens:** Textual's Tabs widget has `can_focus=True` and binds left/right for tab navigation.
**How to avoid:** Use a non-focusable Static widget for the tab bar. Tab switching via Ctrl+PageUp/PageDown or app-level action.
**Warning signs:** Arrow keys stop working in the terminal; focus gets stuck on tab labels.

### Pitfall 2: Ctrl+N/Ctrl+W Leaking to Non-Terminal Contexts
**What goes wrong:** Ctrl+N creates a terminal tab when the editor or file tree is focused. Ctrl+W closes a tab from the wrong context.
**Why it happens:** App-level bindings fire regardless of which panel is focused.
**How to avoid:** Guard the action handlers with a focus check -- only act when focus is inside the terminal panel.
**Warning signs:** Unexpected terminal tabs appearing or shells closing when working in the editor.
**Example guard:**
```python
def action_new_terminal_tab(self) -> None:
    panel = self.query_one("#terminal-panel", TerminalPanel)
    if not self._panel_has_focus(panel):
        return  # Not focused on terminal -- ignore
    panel.add_tab()
```

### Pitfall 3: PTY Resize on Panel Height Change
**What goes wrong:** Terminal content wraps or clips incorrectly after window resize because the PTY dimensions don't match the widget dimensions.
**Why it happens:** The terminal panel's height changes when the host terminal resizes, but the TerminalWidget's `on_resize` only fires if the widget itself detects a size change.
**How to avoid:** TerminalWidget already has `on_resize` that calls `_screen.resize()` and `_pty_manager.resize()`. As long as the widget's size changes propagate correctly through Textual's layout system (which they do), this is handled automatically.
**Warning signs:** Text wrapping at wrong column widths after resize.

### Pitfall 4: Multiple PTY Read Threads on Tab Close/Create
**What goes wrong:** Memory leak or ghost threads from closed terminals that weren't properly stopped.
**Why it happens:** Each TerminalWidget spawns a daemon read thread. If the widget is removed from DOM without calling stop_pty(), the thread keeps running until the fd is closed.
**How to avoid:** Always call `terminal.stop_pty()` before removing a TerminalWidget from the DOM.
**Warning signs:** CPU usage slowly increasing; zombie processes in process table.

### Pitfall 5: Minimize Loses Focus to Nowhere
**What goes wrong:** When terminal is minimized while focused, focus becomes None, and keyboard input stops working.
**Why it happens:** The focused widget becomes non-displayed (hidden by ContentSwitcher or height collapse), but no other widget is given focus.
**How to avoid:** Move focus to another panel BEFORE minimizing, same as the existing action_toggle_file_tree() pattern.
**Example:** `self.action_focus_panel("editor")` before `panel.minimize()`

### Pitfall 6: ContentSwitcher.mount() vs add_content()
**What goes wrong:** Using `mount()` on ContentSwitcher doesn't automatically set the display property correctly.
**Why it happens:** ContentSwitcher's `_on_mount` sets initial display states. Later-mounted children may not have display set correctly.
**How to avoid:** After mounting a new TerminalWidget, explicitly set `switcher.current = new_tab_id` to trigger the `watch_current` handler that manages display states.

### Pitfall 7: Shell Exit Leaves Tab Open with Dead PTY
**What goes wrong:** User exits shell (types `exit`), but tab stays open with a dead terminal that can't accept input.
**Why it happens:** PtyExited message fires but nobody handles it in the terminal panel.
**How to avoid:** Handle `on_pty_exited` in TerminalPanel -- show exit message in the tab with restart hint, similar to ChatPanel's pattern.

## Code Examples

### TerminalPanel compose() Structure
```python
# Source: Derived from BasePanel pattern (nano_claude/panels/base.py)
# and ContentSwitcher API (textual docs)
class TerminalPanel(BasePanel):
    is_minimized = reactive(True)
    _tab_counter: int = 0

    DEFAULT_CSS = """
    TerminalPanel {
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        self.panel_title = "Terminal"
        yield Static("", id="terminal-tab-bar")
        yield ContentSwitcher(id="terminal-switcher")
        yield Static(
            " Terminal (idle) | Ctrl+T to open ",
            id="terminal-status-line",
        )
```

### Updated App.compose() Layout
```python
# Source: Existing compose() in app.py line 286-293
def compose(self) -> ComposeResult:
    yield Header()
    with Vertical(id="app-layout"):
        with Horizontal(id="main-panels"):
            yield FileTreePanel(id="file-tree")
            yield EditorPanel(id="editor")
            yield ChatPanel(id="chat")
        yield TerminalPanel(id="terminal-panel")
    yield Footer()
```

### Spawning User Shell
```python
# Source: PtyManager.spawn() + CONTEXT.md shell decision
import os
shell = os.environ.get("SHELL", "/bin/sh")
terminal = TerminalWidget(command=shell, id=f"shell-{counter}")
```

### Tab Bar Rendering (Custom Static)
```python
# Source: Design decision -- non-focusable tab bar
def _update_tab_bar(self) -> None:
    """Render tab bar as styled text in a Static widget."""
    switcher = self.query_one("#terminal-switcher", ContentSwitcher)
    tab_bar = self.query_one("#terminal-tab-bar", Static)

    parts = []
    for i, child in enumerate(switcher.children):
        tab_num = i + 1
        is_active = child.id == switcher.current
        if is_active:
            parts.append(f" [{tab_num}] ")  # Active tab indicator
        else:
            parts.append(f"  {tab_num}  ")

    tab_bar.update(" ".join(parts) if parts else "")
```

### RESERVED_KEYS Update
```python
# Source: Existing RESERVED_KEYS in terminal/widget.py line 35-57
RESERVED_KEYS: frozenset[str] = frozenset({
    "ctrl+b",
    "ctrl+d",
    "ctrl+e",
    "ctrl+j",
    "ctrl+l",
    "ctrl+n",        # NEW: new terminal tab
    "ctrl+p",
    "ctrl+r",
    "ctrl+q",
    "ctrl+t",        # NEW: toggle terminal panel
    "ctrl+w",        # NEW: close terminal tab
    "ctrl+equal",
    "ctrl+minus",
    "ctrl+backslash",
    "ctrl+h",
    "ctrl+s",
    "ctrl+f",
    "ctrl+1",
    "ctrl+2",
    "ctrl+3",
    "ctrl+shift+r",
    "tab",
    "shift+tab",
    "ctrl+tab",
})
```

### Graceful Shutdown with Terminal Cleanup
```python
# Source: Existing _do_final_exit() in app.py
def _do_final_exit(self) -> None:
    """Called by ShutdownScreen after it renders."""
    self._stop_claude_pty()
    # Stop all shell terminal PTYs
    self._stop_shell_ptys()
    if hasattr(self, "_file_watcher"):
        self._file_watcher.stop()
    for worker in self.workers:
        worker.cancel()
    self.exit()

def _stop_shell_ptys(self) -> None:
    """Stop all shell PTY subprocesses."""
    try:
        panel = self.query_one("#terminal-panel", TerminalPanel)
        switcher = panel.query_one("#terminal-switcher", ContentSwitcher)
        for child in switcher.children:
            if isinstance(child, TerminalWidget):
                child.stop_pty()
    except Exception:
        pass
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom tab widget | ContentSwitcher + custom tab bar | Textual 0.16+ | ContentSwitcher handles display toggling; avoids focus issues with Tabs widget |
| TabbedContent for dynamic tabs | TabbedContent.add_pane() / remove_pane() | Textual PR #2751 | API exists but introduces focus complications for terminal use case |
| pty.openpty() manual | pty.fork() in PtyManager | Already in codebase | Simpler child process management; already proven |

**Deprecated/outdated:**
- None relevant -- all project dependencies are current

## Open Questions

1. **Terminal panel height value**
   - What we know: CONTEXT.md says fixed height, suggests ~30% or reasonable row count
   - What's unclear: Exact value; 30% vs fixed 12-15 rows
   - Recommendation: Use percentage-based (30%) for responsiveness across different terminal sizes. Fall back to minimum of 8 rows.

2. **Tab switching shortcut**
   - What we know: CONTEXT.md lists as Claude's discretion. Ctrl+PageUp/PageDown is VS Code convention.
   - What's unclear: Whether to add tab cycling shortcuts at all for v1
   - Recommendation: Start without explicit tab switching shortcut. Users click tabs or use Ctrl+N/Ctrl+W. Add Ctrl+PageUp/PageDown if needed later. Keep the binding surface small.

3. **Maximum number of tabs**
   - What we know: Each tab is a TerminalWidget + PtyManager + read thread + pyte screen
   - What's unclear: Memory/performance ceiling
   - Recommendation: Cap at 8 tabs (generous for TUI usage). Show notification when limit reached.

4. **StatusParser on shell output**
   - What we know: TerminalWidget instantiates StatusParser regardless of command. For non-Claude output, regex patterns won't match so it's a no-op performance-wise.
   - What's unclear: Whether to skip StatusParser entirely for shell terminals
   - Recommendation: Skip StatusParser for shell terminals by adding a `parse_status=False` parameter to TerminalWidget constructor, or just accept the minor overhead. The overhead is negligible (regex on every chunk), so leaving it is fine for v1.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `.venv/bin/python -m pytest tests/test_terminal_panel.py -x` |
| Full suite command | `.venv/bin/python -m pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TERM-01 | Ctrl+T toggles terminal panel visibility | integration | `.venv/bin/python -m pytest tests/test_terminal_panel.py::test_ctrl_t_shows_terminal -x` | Wave 0 |
| TERM-01 | Ctrl+T minimizes when focused | integration | `.venv/bin/python -m pytest tests/test_terminal_panel.py::test_ctrl_t_minimizes_when_focused -x` | Wave 0 |
| TERM-01 | Ctrl+T focuses when visible but unfocused | integration | `.venv/bin/python -m pytest tests/test_terminal_panel.py::test_ctrl_t_focuses_visible_terminal -x` | Wave 0 |
| TERM-02 | Terminal spawns user $SHELL | unit | `.venv/bin/python -m pytest tests/test_terminal_panel.py::test_terminal_spawns_shell -x` | Wave 0 |
| TERM-02 | Multiple tabs with independent sessions | integration | `.venv/bin/python -m pytest tests/test_terminal_panel.py::test_multiple_terminal_tabs -x` | Wave 0 |
| TERM-02 | Close tab stops PTY | unit | `.venv/bin/python -m pytest tests/test_terminal_panel.py::test_close_tab_stops_pty -x` | Wave 0 |
| TERM-03 | Tab/Shift+Tab includes terminal when visible | integration | `.venv/bin/python -m pytest tests/test_terminal_panel.py::test_focus_cycling_includes_terminal -x` | Wave 0 |
| TERM-03 | Terminal excluded from focus chain when minimized | integration | `.venv/bin/python -m pytest tests/test_terminal_panel.py::test_minimized_terminal_excluded_from_focus -x` | Wave 0 |
| TERM-03 | RESERVED_KEYS includes ctrl+t, ctrl+n, ctrl+w | unit | `.venv/bin/python -m pytest tests/test_terminal_panel.py::test_reserved_keys_updated -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/python -m pytest tests/test_terminal_panel.py -x`
- **Per wave merge:** `.venv/bin/python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_terminal_panel.py` -- covers TERM-01, TERM-02, TERM-03
- [ ] No new fixtures needed -- existing conftest.py app fixture pattern is sufficient

## Sources

### Primary (HIGH confidence)
- Existing codebase: `nano_claude/terminal/widget.py` -- TerminalWidget API, RESERVED_KEYS, PtyExited
- Existing codebase: `nano_claude/terminal/pty_manager.py` -- PtyManager.spawn/stop/resize
- Existing codebase: `nano_claude/app.py` -- compose(), BINDINGS, focus management, toggle patterns
- Existing codebase: `nano_claude/panels/chat.py` -- PtyExited handling pattern
- Existing codebase: `nano_claude/panels/base.py` -- BasePanel composition
- Textual source (verified via inspect): Screen.focus_chain uses displayed_children (DOM order)
- Textual source (verified via inspect): ContentSwitcher uses display=True/False for switching
- Textual source (verified via inspect): TabbedContent.add_pane/remove_pane exist with correct signatures
- Textual source (verified via inspect): Tabs.can_focus=True, Tab.can_focus=False

### Secondary (MEDIUM confidence)
- [Textual TabbedContent docs](https://textual.textualize.io/widgets/tabbed_content/) -- API reference, messages, CSS styling
- [Textual ContentSwitcher docs](https://textual.textualize.io/widgets/content_switcher/) -- add_content, current property, visibility
- [Textual Screen API](https://textual.textualize.io/api/screen/) -- focus_next, focus_previous, focus_chain

### Tertiary (LOW confidence)
- None -- all findings verified against source code or official docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies; all components already in codebase or Textual built-ins, verified via source inspection
- Architecture: HIGH -- patterns directly derived from existing codebase (ChatPanel, toggle_file_tree, RESERVED_KEYS) and verified Textual APIs
- Pitfalls: HIGH -- most derived from direct code reading (focus_chain source, ContentSwitcher source) and existing project decisions

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable -- no fast-moving dependencies)
