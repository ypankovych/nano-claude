# Phase 1: App Shell and Layout - Research

**Researched:** 2026-03-22
**Domain:** Textual TUI framework -- multi-panel layout, focus management, keyboard navigation, responsive resize
**Confidence:** HIGH

## Summary

Phase 1 builds the foundational app shell: a three-panel layout (file tree, editor, chat) with a top bar, bottom status bar, keyboard-driven focus switching, keyboard panel resizing, and graceful terminal resize handling. This is a greenfield project -- no existing code to integrate with.

Textual 8.1.1 is the TUI framework. Its CSS-based layout system supports `fr` units, percentages, docking, and dynamic style modification from Python. The layout uses a `Horizontal` container for the three main panels with `fr`-based widths, plus docked `Header`/`Footer` widgets for the chrome. Focus is managed via Textual's built-in focus system with custom actions to jump focus to specific panels. Panel resizing is achieved by modifying `widget.styles.width` at runtime in response to keybindings.

**Critical finding:** The CONTEXT.md specifies `Ctrl+1/2/3/4` for direct panel switching, but `Ctrl+number` keys are NOT reliably passed through by most terminal emulators. This is a known, documented Textual limitation. The implementation MUST provide fallback bindings (e.g., `Ctrl+b/e/c/t` or `Alt+1/2/3/4`) and should test with `textual keys` across target terminals.

**Primary recommendation:** Use `Horizontal` container with `fr`-unit widths for the three-panel layout, `dock: top/bottom` for header/footer, `:focus-within` pseudo-class for active panel highlighting, and `Binding` with `id` parameters for keymap-overridable shortcuts.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Default width split: 15% file tree / 50% editor / 35% Claude chat
- File tree is toggleable (hide/show via shortcut) -- gives more editor space when browsing isn't needed
- Terminal panel (Phase 6) docks at the bottom as a horizontal split below all panels
- Small terminal collapse order: file tree hides first -> editor + chat remain. Then chat hides -> editor only. Each panel toggleable via shortcut.
- Layout must accommodate the bottom terminal dock even though it's not implemented until Phase 6
- Panel switching: both direct jump shortcuts (Ctrl+1 = tree, Ctrl+2 = editor, Ctrl+3 = chat, Ctrl+4 = terminal) AND Ctrl+Tab cycling
- Active panel indicated by: colored border + highlighted title bar (both)
- Primary modifier: Ctrl for all app-level shortcuts
- Panel resizing: Ctrl+Plus/Minus to grow/shrink the active panel's width
- File tree toggle: dedicated Ctrl shortcut (Claude picks which key)
- Panel borders: thin single-line box-drawing characters -- clean, minimal
- Top bar: app name + currently open file
- Bottom bar: cursor position, Claude status, token count, key hints
- Default color scheme: dark background, light text
- Panel titles: minimal -- only the editor panel shows the filename, other panels unlabeled (the top bar provides context)
- Project root: always use current working directory (cwd)
- CLI interface: `nano-claude [optional-path]`
- On launch: auto-open README.md if it exists in project root; if no README, show a welcome greeting with key shortcut reference
- Claude Code subprocess: auto-starts immediately on launch -- chat panel is ready to type right away
- All three panels visible immediately on launch

### Claude's Discretion
- Exact Ctrl+key assignments for file tree toggle, diff view toggle, and other non-panel-switch shortcuts
- Welcome greeting content and formatting
- Exact active panel highlight color
- How panel resize increments work (percentage steps vs fixed character widths)
- Minimum panel width thresholds before collapse triggers

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LAYOUT-01 | User sees a split-panel TUI with file tree (left), code editor (center), and Claude chat (right) on launch | Textual `Horizontal` container with `fr`-unit widths (1fr/3.3fr/2.3fr approximating 15/50/35%), `Placeholder` widgets for panel content, CSS-driven layout |
| LAYOUT-02 | User can switch focus between panels using keyboard shortcuts | Textual `BINDINGS` with `priority=True`, `widget.focus()` method for direct jump, `action_focus_next/previous` for Tab cycling, `:focus-within` pseudo-class for visual indication |
| LAYOUT-03 | User can resize panels using keyboard shortcuts | Dynamic `widget.styles.width` modification from Python action handlers, percentage-step increments (e.g., 5% per keypress), enforce min-width constraints |
| LAYOUT-04 | Layout adapts gracefully when terminal is resized (panels collapse at small sizes) | `fr` units auto-redistribute on resize, `on_resize` event handler for collapse logic, `display: none` CSS class toggling for panel hiding |
</phase_requirements>

## Standard Stack

### Core (Phase 1 only)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| textual | 8.1.1 | TUI application framework | CSS layout, widget composition, focus management, keybinding system, async event loop. The only viable choice for a modern Python TUI of this complexity. |
| rich | 14.3.3 | Terminal rendering (Textual dependency) | Installed automatically with Textual. Provides styled text, color support. |
| click | 8.3.1 | CLI entry point | Parses `nano-claude [optional-path]` argument. Lightweight, no Rich dependency conflict. |

### Development

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.2 | Test framework | All tests |
| pytest-asyncio | 1.3.0 | Async test support | All Textual app tests (run_test() is async) |
| pytest-textual-snapshot | latest | Visual regression testing | Verifying layout does not regress after changes |
| textual-dev | latest | Dev console, live reload | Debugging layout, inspecting events, CSS hot-reload |
| ruff | latest | Linter + formatter | All Python code |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Horizontal container | Grid layout | Grid is more powerful but overkill for a simple three-column split. Horizontal + fr units is simpler and more intuitive for this layout. Grid would be needed if panels spanned rows/columns, which they don't. |
| Percentage widths | Fixed character widths | Fixed widths don't adapt to terminal size. Percentage/fr is essential for responsive layout. |
| click | argparse | argparse works but is verbose. click provides better help formatting with less code. |
| click | typer | Typer depends on Rich, risking version conflicts with Textual's Rich dependency. |

**Installation:**
```bash
uv add textual click
uv add --dev textual-dev pytest pytest-asyncio pytest-textual-snapshot ruff
```

**Version verification:** Textual 8.1.1 confirmed as latest on PyPI (2026-03-22). Click 8.3.1 confirmed. pytest 9.0.2 confirmed. pytest-asyncio 1.3.0 confirmed.

## Architecture Patterns

### Recommended Project Structure (Phase 1)

```
nano_claude/
+-- __init__.py
+-- __main__.py             # `python -m nano_claude` entry point
+-- app.py                  # NanoClaudeApp(App) -- layout composition, keybindings, focus management
+-- styles.tcss             # All Textual CSS -- panel widths, borders, colors, focus styles
+-- panels/
|   +-- __init__.py
|   +-- base.py             # BasePanel -- common panel container with border-title, focus-within styling
|   +-- file_tree.py        # FileTreePanel(BasePanel) -- placeholder for Phase 2
|   +-- editor.py           # EditorPanel(BasePanel) -- placeholder for Phase 2
|   +-- chat.py             # ChatPanel(BasePanel) -- placeholder for Phase 3
+-- config/
|   +-- __init__.py
|   +-- settings.py         # Layout defaults (width ratios, min widths, collapse thresholds)
+-- cli.py                  # click entry point: `nano-claude [path]`
tests/
+-- conftest.py             # Shared fixtures (app factory, pilot helpers)
+-- test_layout.py          # LAYOUT-01: three panels visible, correct proportions
+-- test_focus.py           # LAYOUT-02: focus switching via shortcuts
+-- test_resize.py          # LAYOUT-03: panel resizing via shortcuts
+-- test_responsive.py      # LAYOUT-04: terminal resize adaptation
```

### Pattern 1: CSS-Driven Layout with Horizontal Container

**What:** Use a `Horizontal` container holding three panel widgets, with `fr`-based widths defined in TCSS. Header and Footer are docked.

**When to use:** This is the foundational layout pattern for the entire app.

**Example:**
```python
# app.py
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Header, Footer

from nano_claude.panels.file_tree import FileTreePanel
from nano_claude.panels.editor import EditorPanel
from nano_claude.panels.chat import ChatPanel

class NanoClaudeApp(App):
    CSS_PATH = "styles.tcss"
    TITLE = "nano-claude"

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-panels"):
            yield FileTreePanel(id="file-tree")
            yield EditorPanel(id="editor")
            yield ChatPanel(id="chat")
        yield Footer()
```

```css
/* styles.tcss */
#main-panels {
    height: 1fr;
}

#file-tree {
    width: 15%;
    min-width: 15;
    border: round $secondary;
}

#editor {
    width: 50%;
    min-width: 20;
    border: round $secondary;
}

#chat {
    width: 35%;
    min-width: 20;
    border: round $secondary;
}

/* Active panel highlight */
#file-tree:focus-within {
    border: round $accent;
}

#editor:focus-within {
    border: round $accent;
}

#chat:focus-within {
    border: round $accent;
}
```

Source: [Textual Layout Guide](https://textual.textualize.io/guide/layout/), [Textual CSS Guide](https://textual.textualize.io/guide/CSS/)

### Pattern 2: BasePanel Container for Consistent Panel Chrome

**What:** A reusable base panel widget that provides consistent border styling, title bar, and focus-within highlighting for all panels.

**When to use:** For every panel (file tree, editor, chat, and later terminal).

**Example:**
```python
# panels/base.py
from textual.containers import Vertical
from textual.reactive import reactive

class BasePanel(Vertical):
    """Base container for all nano-claude panels.
    Provides consistent border, title, and focus-within styling."""

    DEFAULT_CSS = """
    BasePanel {
        border: round $secondary;
    }
    BasePanel:focus-within {
        border: round $accent;
    }
    """

    panel_title = reactive("")

    def watch_panel_title(self, title: str) -> None:
        self.border_title = title
```

Source: [Textual Widgets Guide](https://textual.textualize.io/guide/widgets/), [Textual CSS pseudo-classes](https://textual.textualize.io/guide/CSS/)

### Pattern 3: Direct-Jump Focus with Priority Bindings

**What:** App-level keybindings that directly focus a specific panel by querying for it and calling `.focus()`. Uses `priority=True` so these bindings work even when a child widget has focus.

**When to use:** For `Ctrl+1/2/3/4` (or fallback keys) panel switching.

**Example:**
```python
from textual.binding import Binding

class NanoClaudeApp(App):
    BINDINGS = [
        # Direct panel jump -- priority=True so they override child bindings
        Binding("ctrl+b", "focus_panel('file-tree')", "File Tree", id="focus.file_tree", priority=True),
        Binding("ctrl+e", "focus_panel('editor')", "Editor", id="focus.editor", priority=True),
        Binding("ctrl+r", "focus_panel('chat')", "Chat", id="focus.chat", priority=True),
        # Cycling
        Binding("ctrl+tab", "focus_next", "Next Panel", id="focus.next", priority=True),
        Binding("ctrl+shift+tab", "focus_previous", "Prev Panel", id="focus.previous", priority=True),
        # Resize active panel
        Binding("ctrl+plus", "resize_panel(5)", "Grow Panel", id="resize.grow", priority=True),
        Binding("ctrl+minus", "resize_panel(-5)", "Shrink Panel", id="resize.shrink", priority=True),
    ]

    def action_focus_panel(self, panel_id: str) -> None:
        """Focus a specific panel by its DOM id."""
        try:
            panel = self.query_one(f"#{panel_id}")
            # Focus the first focusable child within the panel
            focusable = panel.query("*:can-focus").first()
            focusable.focus()
        except Exception:
            pass

    def action_resize_panel(self, delta: int) -> None:
        """Resize the currently focused panel's width by delta percentage points."""
        focused = self.focused
        if focused is None:
            return
        # Walk up to find the panel container
        panel = focused
        while panel and panel.id not in ("file-tree", "editor", "chat"):
            panel = panel.parent
        if panel is None:
            return
        # Get current percentage width and adjust
        # Implementation detail: read current width, add delta, enforce min/max
        current = _get_panel_width_pct(panel)
        new_width = max(10, min(80, current + delta))
        panel.styles.width = f"{new_width}%"
        # Redistribute remaining space to adjacent panels
        self._rebalance_panels(panel, delta)
```

Source: [Textual Input Guide](https://textual.textualize.io/guide/input/), [Textual Actions Guide](https://textual.textualize.io/guide/actions/)

### Pattern 4: Panel Toggle via CSS Class

**What:** Toggle panel visibility by adding/removing a CSS class that sets `display: none`. When a panel hides, its width is redistributed to remaining panels.

**When to use:** For file tree toggle and collapse behavior at small terminal sizes.

**Example:**
```python
# In styles.tcss
.hidden {
    display: none;
}

# In app.py
class NanoClaudeApp(App):
    BINDINGS = [
        Binding("ctrl+backslash", "toggle_file_tree", "Toggle Tree", id="toggle.file_tree", priority=True),
    ]

    def action_toggle_file_tree(self) -> None:
        tree = self.query_one("#file-tree")
        tree.toggle_class("hidden")
        # Rebalance remaining panel widths
        self._rebalance_panels_after_toggle()
```

Source: [Textual CSS Guide](https://textual.textualize.io/guide/CSS/)

### Pattern 5: Keymap-Overridable Bindings

**What:** Every binding has an `id` parameter, enabling runtime keymap overrides. This future-proofs keybindings for user customization (v2 requirement ADVEDIT-03).

**When to use:** For ALL bindings from day one. The `id` parameter costs nothing but enables keymap overrides later.

**Example:**
```python
# All bindings MUST have id= parameter
BINDINGS = [
    Binding("ctrl+b", "focus_panel('file-tree')", "File Tree", id="focus.file_tree", priority=True),
    # Later, user config can remap: {"focus.file_tree": "ctrl+1,ctrl+b"}
]

# In on_mount, optionally apply user keymap
def on_mount(self) -> None:
    user_keymap = self._load_user_keymap()
    if user_keymap:
        self.set_keymap(user_keymap)
```

Source: [Textual Keymaps](https://darren.codes/posts/textual-keymaps/)

### Anti-Patterns to Avoid

- **Grid layout for simple columns:** Grid adds complexity (grid-size, grid-columns, cell spanning) when `Horizontal` + `fr`/`%` widths suffice. Only use Grid if you need row-spanning.
- **Direct panel references between widgets:** Panels must NOT hold references to each other. Use Textual's message system for inter-panel communication.
- **Hardcoded pixel widths:** Never use fixed character widths for panels. Always use `%` or `fr` so layout adapts to terminal size.
- **`display: block` instead of `display: none` for toggle:** Textual uses `display: block` as default. Toggle via class with `display: none` rule.
- **Synchronous resize handlers:** Never do heavy computation in `on_resize`. If collapse logic is complex, post a message and handle it async.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Three-column layout | Manual character-counting and terminal coordinate math | Textual `Horizontal` container + CSS `width` | Textual handles terminal resize, scrolling, overflow automatically |
| Focus cycling | Manual focus index tracking with modular arithmetic | Textual `action_focus_next` / `action_focus_previous` | Built-in, handles edge cases (disabled widgets, hidden panels) |
| Status bar with key hints | Manual string formatting of keybinding hints | Textual `Footer` widget | Auto-displays BINDINGS with `show=True`, auto-updates when focus changes |
| Header with title | Manual top-row rendering | Textual `Header` widget | Docks to top, reactive `title`/`sub_title` from App |
| Panel borders | Manual box-drawing with print statements | Textual CSS `border` property | Supports 16 border styles, colored, with title/subtitle |
| Active panel highlighting | Manual border color switching in event handlers | CSS `:focus-within` pseudo-class | Automatic -- fires when any child of the container has focus |
| Terminal resize handling | Manual SIGWINCH signal handler | Textual `Resize` event + CSS `fr`/`%` units | Layout engine automatically recalculates on resize |

**Key insight:** Textual's CSS system handles 90% of what Phase 1 needs declaratively. The Python code should only handle keybinding actions and dynamic width adjustments -- everything else is CSS.

## Common Pitfalls

### Pitfall 1: Ctrl+Number Keys Don't Work in Most Terminals

**What goes wrong:** CONTEXT.md specifies `Ctrl+1 = tree, Ctrl+2 = editor, Ctrl+3 = chat, Ctrl+4 = terminal`. These key combinations are NOT reliably passed through by terminal emulators. Ctrl+number produces unpredictable results (nothing, a raw number, or a terminal-specific action).

**Why it happens:** Terminal emulators translate key presses into escape sequences. Ctrl+letter has standard ANSI mappings (Ctrl+A = 0x01, etc.) but Ctrl+number has no standard mapping. Each terminal handles it differently or not at all.

**How to avoid:**
1. Use `Ctrl+letter` as the PRIMARY binding: `Ctrl+b` (tree), `Ctrl+e` (editor), `Ctrl+r` (chat), `Ctrl+t` (terminal).
2. Add `Ctrl+1/2/3/4` as SECONDARY bindings for terminals that support it.
3. Provide `Ctrl+Tab` cycling as the universal fallback.
4. Give all bindings `id=` parameters so users can remap via keymap config.
5. Test with `textual keys` in target terminals.

**Warning signs:** "Panel switch doesn't work" bug reports that are terminal-specific.

### Pitfall 2: Panel Width Rebalancing After Resize or Toggle

**What goes wrong:** When the user resizes one panel wider, the other panels don't automatically shrink to compensate. When a panel is toggled hidden, the remaining panels don't expand to fill the space. The layout either overflows or has gaps.

**Why it happens:** Textual CSS `%` widths are relative to the container, not to each other. If panel A is 15%, panel B is 50%, and panel C is 35%, hiding panel A does not automatically redistribute its 15% to B and C. You get 85% used space with a gap.

**How to avoid:**
1. Use `fr` units instead of `%` for the main columns: `1fr / 3.3fr / 2.3fr` gives approximately 15/50/35%.
2. When a panel is hidden (`display: none`), the remaining `fr` panels automatically expand to fill available space. No manual rebalancing needed.
3. For keyboard resizing, modify the `fr` values rather than `%` values. Increase one panel's `fr` and decrease another's.
4. Store the current `fr` values as reactive attributes on the App so they survive toggle/untoggle cycles.

**Warning signs:** Gaps or overflow after hiding/showing panels; panels don't fill screen after resize.

### Pitfall 3: Focus Lost When Panel is Hidden

**What goes wrong:** User hides the currently focused panel (e.g., toggles file tree while it has focus). Focus goes to... nowhere. The app appears unresponsive because no panel has focus.

**Why it happens:** Textual removes hidden widgets from the focus chain. If the focused widget becomes hidden, focus is not automatically transferred.

**How to avoid:**
1. Before hiding a panel, check if it (or its children) have focus.
2. If so, move focus to the next visible panel before hiding.
3. After unhiding a panel, focus its first focusable child to make it immediately usable.

**Warning signs:** App stops responding to keybindings after toggling a panel.

### Pitfall 4: `on_resize` Fires Before Layout Redraws

**What goes wrong:** Code in `on_resize` that reads widget dimensions gets stale values because the layout hasn't been recalculated yet.

**Why it happens:** Textual's `Resize` event fires before the layout engine runs the new calculation. This is documented in [Textual Discussion #3527](https://github.com/Textualize/textual/discussions/3527).

**How to avoid:**
1. For simple responsive behavior, rely entirely on CSS `fr`/`%` units -- they auto-adapt without any Python code.
2. If you need to run collapse logic based on terminal size, use `call_later()` or `set_timer(0.05, handler)` to defer the check until after layout completes.
3. Alternatively, override `watch_size()` on the App (reactive watcher) instead of handling `on_resize`.

**Warning signs:** Collapse logic triggers at wrong terminal sizes; panels flicker during resize.

### Pitfall 5: `Ctrl+Tab` May Not Work in All Terminals

**What goes wrong:** `Ctrl+Tab` is intercepted by some terminal emulators (e.g., for tab switching in tabbed terminals).

**Why it happens:** Same as Pitfall 1 -- terminal emulators consume certain key combinations before they reach the application.

**How to avoid:**
1. Test `Ctrl+Tab` with `textual keys` on target terminals.
2. If problematic, use `Tab` (without Ctrl) for forward cycling and `Shift+Tab` for backward cycling. These are universally supported.
3. Keep direct-jump shortcuts as the primary mechanism; cycling is secondary.

**Warning signs:** Focus cycling works in some terminals but not others.

## Code Examples

### Complete App Shell (Phase 1 Skeleton)

```python
# nano_claude/app.py
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Header, Footer, Static


class PanelPlaceholder(Static):
    """Placeholder content for panels before Phase 2+ implementation."""

    DEFAULT_CSS = """
    PanelPlaceholder {
        width: 1fr;
        height: 1fr;
        content-align: center middle;
        color: $text-muted;
    }
    """

    def __init__(self, text: str, **kwargs) -> None:
        super().__init__(text, **kwargs)


class BasePanel(Vertical):
    """Base container for all panels. Provides border + focus-within highlight."""

    DEFAULT_CSS = """
    BasePanel {
        border: round $secondary;
    }
    BasePanel:focus-within {
        border: round $accent;
    }
    """


class NanoClaudeApp(App):
    CSS_PATH = "styles.tcss"
    TITLE = "nano-claude"
    SUB_TITLE = ""  # Updated to show current file

    # Panel width state (fr units)
    tree_width = reactive(1.0)
    editor_width = reactive(3.3)
    chat_width = reactive(2.3)
    tree_visible = reactive(True)

    BINDINGS = [
        # Panel focus -- Ctrl+letter as primary (universally supported)
        Binding("ctrl+b", "focus_panel('file-tree')", "Tree", id="focus.tree", priority=True, show=False),
        Binding("ctrl+e", "focus_panel('editor')", "Editor", id="focus.editor", priority=True, show=False),
        Binding("ctrl+r", "focus_panel('chat')", "Chat", id="focus.chat", priority=True, show=False),
        # Focus cycling
        Binding("ctrl+i", "focus_next", "Next", id="focus.next", priority=True, show=False),  # ctrl+i = Tab in terminals
        # Panel resize
        Binding("ctrl+equal", "resize_panel(1)", "Grow", id="resize.grow", priority=True, show=True),
        Binding("ctrl+minus", "resize_panel(-1)", "Shrink", id="resize.shrink", priority=True, show=True),
        # Toggle file tree
        Binding("ctrl+backslash", "toggle_file_tree", "Toggle Tree", id="toggle.tree", priority=True),
        # Quit
        Binding("ctrl+q", "quit", "Quit", id="app.quit", priority=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-panels"):
            yield FileTreePanel(id="file-tree")
            yield EditorPanel(id="editor")
            yield ChatPanel(id="chat")
        yield Footer()

    def action_focus_panel(self, panel_id: str) -> None:
        """Focus a specific panel by its DOM id."""
        try:
            panel = self.query_one(f"#{panel_id}")
            if panel.has_class("hidden"):
                return
            focusable = list(panel.query("*").results())
            for widget in focusable:
                if widget.can_focus:
                    widget.focus()
                    return
            # If no focusable child, focus the panel itself if possible
            panel.focus()
        except Exception:
            pass

    def action_resize_panel(self, delta: int) -> None:
        """Grow or shrink the active panel width."""
        # Find which panel is focused
        focused = self.focused
        if focused is None:
            return
        panel = focused
        while panel is not None and panel.id not in ("file-tree", "editor", "chat"):
            panel = panel.parent
        if panel is None:
            return
        # Adjust fr value for the focused panel
        # Delta of 1 = roughly 5% visual change
        attr_map = {
            "file-tree": "tree_width",
            "editor": "editor_width",
            "chat": "chat_width",
        }
        attr = attr_map.get(panel.id)
        if attr is None:
            return
        current = getattr(self, attr)
        new_val = max(0.5, current + delta * 0.5)  # 0.5fr step, minimum 0.5fr
        setattr(self, attr, new_val)
        self._apply_panel_widths()

    def _apply_panel_widths(self) -> None:
        """Apply current fr-based widths to all panels."""
        panels = {
            "file-tree": self.tree_width,
            "editor": self.editor_width,
            "chat": self.chat_width,
        }
        for panel_id, fr_val in panels.items():
            try:
                panel = self.query_one(f"#{panel_id}")
                if not panel.has_class("hidden"):
                    panel.styles.width = f"{fr_val}fr"
            except Exception:
                pass

    def action_toggle_file_tree(self) -> None:
        """Toggle file tree panel visibility."""
        tree = self.query_one("#file-tree")
        is_hiding = not tree.has_class("hidden")
        if is_hiding:
            # Move focus away before hiding
            if self._panel_has_focus(tree):
                self.action_focus_panel("editor")
            tree.add_class("hidden")
        else:
            tree.remove_class("hidden")
            self._apply_panel_widths()

    def _panel_has_focus(self, panel) -> bool:
        """Check if the panel or any of its children have focus."""
        focused = self.focused
        if focused is None:
            return False
        node = focused
        while node is not None:
            if node is panel:
                return True
            node = node.parent
        return False
```

Source: Composed from [Textual Layout Guide](https://textual.textualize.io/guide/layout/), [Textual Input Guide](https://textual.textualize.io/guide/input/), [Textual CSS Guide](https://textual.textualize.io/guide/CSS/)

### TCSS Stylesheet

```css
/* nano_claude/styles.tcss */

/* Main panel container -- fills space between header and footer */
#main-panels {
    height: 1fr;
}

/* Panel defaults */
#file-tree {
    width: 1fr;       /* ~15% relative to 1 + 3.3 + 2.3 = 6.6 total */
    min-width: 15;
    border: round $secondary;
}

#editor {
    width: 3.3fr;     /* ~50% */
    min-width: 20;
    border: round $secondary;
}

#chat {
    width: 2.3fr;     /* ~35% */
    min-width: 20;
    border: round $secondary;
}

/* Active panel highlighting via focus-within */
#file-tree:focus-within {
    border: round $accent;
}

#editor:focus-within {
    border: round $accent;
}

#chat:focus-within {
    border: round $accent;
}

/* Hidden panel */
.hidden {
    display: none;
}

/* Future: terminal dock (Phase 6 placeholder) */
#terminal {
    display: none;
    dock: bottom;
    height: 30%;
    min-height: 5;
    border: round $secondary;
}

#terminal:focus-within {
    border: round $accent;
}

#terminal.visible {
    display: block;
}
```

Source: [Textual CSS Reference](https://textual.textualize.io/styles/), [Textual Layout Guide](https://textual.textualize.io/guide/layout/)

### Testing Pattern

```python
# tests/test_layout.py
import pytest
from nano_claude.app import NanoClaudeApp


async def test_three_panels_visible_on_launch():
    """LAYOUT-01: Three panels visible on launch."""
    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        # All three panels should be visible (not hidden)
        tree = app.query_one("#file-tree")
        editor = app.query_one("#editor")
        chat = app.query_one("#chat")
        assert tree.display is True
        assert editor.display is True
        assert chat.display is True


async def test_focus_switching_via_shortcuts():
    """LAYOUT-02: Focus switches between panels via keyboard shortcuts."""
    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        # Focus editor
        await pilot.press("ctrl+e")
        await pilot.pause()
        # Verify editor panel has focus-within
        editor = app.query_one("#editor")
        assert editor.has_pseudo_class("focus-within")

        # Focus chat
        await pilot.press("ctrl+r")
        await pilot.pause()
        chat = app.query_one("#chat")
        assert chat.has_pseudo_class("focus-within")


async def test_panel_resize_via_shortcuts():
    """LAYOUT-03: Panel grows/shrinks via keyboard shortcuts."""
    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        # Focus editor
        await pilot.press("ctrl+e")
        await pilot.pause()
        initial_width = app.editor_width
        # Grow
        await pilot.press("ctrl+equal")
        await pilot.pause()
        assert app.editor_width > initial_width


async def test_terminal_resize_no_crash():
    """LAYOUT-04: App doesn't crash when terminal is resized."""
    app = NanoClaudeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        # Resize to small
        app.resize(40, 20)
        await pilot.pause()
        # Resize to large
        app.resize(200, 60)
        await pilot.pause()
        # Still three panels
        assert app.query_one("#file-tree") is not None
        assert app.query_one("#editor") is not None
        assert app.query_one("#chat") is not None
```

Source: [Textual Testing Guide](https://textual.textualize.io/guide/testing/)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `layout: grid` for multi-column | `Horizontal` container + `fr` widths | Textual 1.0+ (2024) | Simpler for column layouts; Grid still available for complex grids |
| Manual keybinding list | `Binding` with `id=` + `set_keymap()` | Textual 0.82.0 (2024) | Enables runtime keybinding customization |
| `BINDINGS` tuples | `Binding` objects | Textual 0.40+ | More features: `priority`, `show`, `id`, `key_display` |
| No pseudo-class support | `:focus-within`, `:hover`, `:blur` | Textual 1.0+ | Declarative styling based on focus state |

**Deprecated/outdated:**
- Tuple-based BINDINGS `("key", "action", "desc")`: Still works but lacks `id` for keymaps, `priority`, `show`. Use `Binding()` objects.
- `textual.css_query` for focus: Use `:focus-within` CSS pseudo-class instead.

## Open Questions

1. **Ctrl+Plus binding name**
   - What we know: `Ctrl+=` (ctrl+equal) is the common binding for "plus" since `+` requires Shift. Need to verify the exact Textual key name.
   - What's unclear: Whether `ctrl+plus` or `ctrl+equal` is the correct key name in Textual.
   - Recommendation: Test with `textual keys` and use `ctrl+equal` as primary, with a note in documentation.

2. **`fr` unit dynamic modification from Python**
   - What we know: `widget.styles.width = "3.3fr"` should work based on Textual docs for setting width from Python.
   - What's unclear: Whether fractional `fr` values (e.g., `3.3fr`) are supported or only integers.
   - Recommendation: Test early in implementation. If fractional `fr` is unsupported, use percentages with manual rebalancing.

3. **Minimum collapse threshold**
   - What we know: CONTEXT says collapse order is tree first, then chat, then editor-only.
   - What's unclear: What terminal width triggers collapse. Needs experimentation.
   - Recommendation: Start with 60 columns as first collapse (hide tree), 40 columns as second collapse (hide chat). Tune based on testing.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LAYOUT-01 | Three panels visible on launch with correct proportions | integration | `uv run pytest tests/test_layout.py -x` | No -- Wave 0 |
| LAYOUT-02 | Focus switches between panels via keyboard shortcuts | integration | `uv run pytest tests/test_focus.py -x` | No -- Wave 0 |
| LAYOUT-03 | Panel resizing via keyboard shortcuts | integration | `uv run pytest tests/test_resize.py -x` | No -- Wave 0 |
| LAYOUT-04 | Terminal resize adaptation (no crash, graceful collapse) | integration | `uv run pytest tests/test_responsive.py -x` | No -- Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/conftest.py` -- shared fixtures (app factory with configurable size)
- [ ] `tests/test_layout.py` -- covers LAYOUT-01
- [ ] `tests/test_focus.py` -- covers LAYOUT-02
- [ ] `tests/test_resize.py` -- covers LAYOUT-03
- [ ] `tests/test_responsive.py` -- covers LAYOUT-04
- [ ] `pyproject.toml` -- project configuration with test settings (`asyncio_mode = "auto"`)
- [ ] Framework install: `uv add --dev pytest pytest-asyncio pytest-textual-snapshot`

## Sources

### Primary (HIGH confidence)
- [Textual Layout Guide](https://textual.textualize.io/guide/layout/) -- Horizontal/Vertical containers, fr units, percentage widths, docking, grid layout
- [Textual CSS Guide](https://textual.textualize.io/guide/CSS/) -- Pseudo-classes (:focus-within, :hover), class selectors, dynamic class management (add_class, toggle_class)
- [Textual Input Guide](https://textual.textualize.io/guide/input/) -- BINDINGS, focus management, Ctrl+key combinations, action system
- [Textual Actions Guide](https://textual.textualize.io/guide/actions/) -- action_focus_next, action_focus_previous, custom actions, check_action
- [Textual Testing Guide](https://textual.textualize.io/guide/testing/) -- Pilot class, run_test(), press(), pause(), snapshot testing
- [Textual Containers API](https://textual.textualize.io/api/containers/) -- Horizontal, Vertical, Grid, HorizontalScroll, VerticalScroll
- [Textual Width Style](https://textual.textualize.io/styles/width/) -- fr units, percentages, vw, fixed, dynamic from Python
- [Textual Border Style](https://textual.textualize.io/styles/border/) -- round, solid, heavy, border-title, border-subtitle
- [Textual Header Widget](https://textual.textualize.io/widgets/header/) -- title, sub_title, icon, clock
- [Textual Footer Widget](https://textual.textualize.io/widgets/footer/) -- auto-displays BINDINGS, compact mode, show_command_palette
- [Textual FAQ](https://textual.textualize.io/FAQ/) -- Key binding limitations, terminal compatibility, macOS Terminal issues
- [Textual Resize Event](https://textual.textualize.io/events/resize/) -- size, virtual_size, container_size
- [Textual Keymaps](https://darren.codes/posts/textual-keymaps/) -- Binding id, set_keymap(), runtime override

### Secondary (MEDIUM confidence)
- [Textual Resize Discussion #3527](https://github.com/Textualize/textual/discussions/3527) -- on_resize fires before layout redraws
- [Textual Design a Layout How-To](https://textual.textualize.io/how-to/design-a-layout/) -- work outside-in pattern
- PyPI version checks: textual 8.1.1, click 8.3.1, pytest 9.0.2, pytest-asyncio 1.3.0 (verified 2026-03-22)

### Tertiary (LOW confidence)
- Ctrl+number key support: WebSearch confirms widespread terminal incompatibility, but exact behavior varies per terminal. Needs `textual keys` validation on target terminals.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Textual 8.1.1 verified on PyPI, all versions confirmed
- Architecture: HIGH -- Layout patterns verified against official Textual docs (Layout Guide, CSS Guide, Containers API)
- Pitfalls: HIGH -- Ctrl+number limitation confirmed in Textual FAQ and wiki; resize timing confirmed in Discussion #3527; focus-on-hide is standard Textual behavior
- Code examples: MEDIUM -- Composed from verified API docs but not runtime-tested; specific `fr` dynamic modification needs validation

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (stable domain -- Textual 8.x is mature)
