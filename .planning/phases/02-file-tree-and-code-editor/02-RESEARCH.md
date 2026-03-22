# Phase 2: File Tree and Code Editor - Research

**Researched:** 2026-03-22
**Domain:** Textual DirectoryTree, TextArea code editor, filesystem watching, in-editor search
**Confidence:** HIGH

## Summary

Phase 2 replaces the Phase 1 placeholder panels with real widgets: a DirectoryTree for file browsing and a TextArea.code_editor() for viewing/editing code with syntax highlighting. Both widgets are built into Textual 8.1.1 and are well-documented. The main implementation work involves: (1) subclassing DirectoryTree to add filtering for hidden files, (2) wiring file selection to the editor via Textual messages, (3) building a custom search overlay since TextArea has no built-in find/search, (4) managing an open-file buffer system for unsaved changes, and (5) integrating watchfiles for filesystem auto-refresh.

The most significant discovery is that TextArea's built-in keybindings conflict with app-level bindings -- `ctrl+f` is mapped to `delete_word_right` and `ctrl+e` to `cursor_line_end` in TextArea. Since app-level bindings have `priority=True`, they take precedence, but the TextArea loses those editing shortcuts when focused. This requires either remapping the TextArea bindings or accepting the trade-off. Additionally, TextArea has no built-in search functionality -- the search overlay (Ctrl+F) must be implemented from scratch using the Document API.

**Primary recommendation:** Use TextArea.code_editor() as-is for the editor, subclass DirectoryTree for the file tree with filter_paths, build the search overlay as a custom widget composited inside EditorPanel, and use watchfiles awatch() in a Textual Worker for filesystem monitoring.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Hide dotfiles, .git, node_modules, __pycache__, .venv by default -- toggleable via shortcut to show hidden files
- Open file on Enter (keyboard) or click (mouse) -- both work
- Expand root directory one level deep on launch (not fully collapsed, not deeply expanded)
- Basic unicode icons for folders/files -- nothing language-specific
- Auto-detect indentation from opened file (tabs vs spaces, indent width) -- respect existing file style
- No word wrap -- horizontal scroll for long lines, preserves code structure
- Unsaved changes indicated by BOTH a dot in the editor title bar AND filename color change
- Unsaved changes kept in buffer when switching files -- no prompt, no auto-save on file switch
- Prompt to save unsaved changes when quitting the app (Ctrl+Q) -- prevent data loss on exit
- Save shortcut: Ctrl+S
- Search bar appears as a top overlay inside the editor panel (like VS Code Ctrl+F)
- Ctrl+F to open search, Escape to close
- All matches highlighted in the file simultaneously, current match in a different/brighter color
- Next match (Enter or Ctrl+G), previous match (Shift+Enter or Ctrl+Shift+G)
- Plain text search only for v1 -- no regex support
- Filesystem watcher (watchfiles) for real-time auto-refresh when files are added/removed externally
- Preserve expanded directory state across refreshes -- don't collapse/disorient the user
- This watcher is foundational -- Phase 4 (Change Detection) will also use it for auto-reload of open files

### Claude's Discretion
- Exact hidden file patterns (beyond .git, node_modules, __pycache__, .venv)
- How indentation detection algorithm works (first N lines? EditorConfig support?)
- Search highlight colors (current match vs other matches)
- How the search overlay interacts with editor keybindings (focus management)
- Large file handling (lazy loading, size threshold warning)
- File tree sort order (alphabetical, folders first, etc.)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TREE-01 | User sees the project directory structure in a collapsible tree | DirectoryTree widget with filter_paths subclass; expand root one level on mount |
| TREE-02 | User can navigate the file tree with keyboard (up/down, expand/collapse) | Tree widget BINDINGS provide up/down/enter/space/shift+arrow natively |
| TREE-03 | User can open a file in the editor by selecting it in the tree | DirectoryTree.FileSelected message bubbles to app; app handler calls editor.open_file(path) |
| TREE-04 | File tree auto-refreshes when files are added or removed | watchfiles awatch() in Textual Worker; tree.reload() preserves expansion state |
| EDIT-01 | User can open files from the file tree and view them with syntax highlighting | TextArea.code_editor() with language auto-detection from file extension; 15 built-in languages |
| EDIT-02 | User can edit file content with standard text editing | TextArea provides insert/delete/selection/cursor movement natively |
| EDIT-03 | User can undo and redo edits | TextArea has built-in undo (ctrl+z) and redo (ctrl+y) with max_checkpoints |
| EDIT-04 | User can save files with a keyboard shortcut | Ctrl+S binding at app level writes TextArea.text to file path; update unsaved indicator |
| EDIT-05 | User sees line numbers in the editor | TextArea.code_editor() enables show_line_numbers=True by default |
| EDIT-06 | User can search within the current file | Custom search overlay widget using Document.get_line() for text scanning, TextArea selection/cursor for highlighting |

</phase_requirements>

## Standard Stack

### Core (Already in Project)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Textual | 8.1.1 | TUI framework with DirectoryTree + TextArea widgets | Already installed; provides both key widgets for this phase |

### New Dependencies for Phase 2

| Library | Version | Purpose | Why Needed |
|---------|---------|---------|------------|
| watchfiles | 1.1.1 | Async filesystem watcher for tree auto-refresh | Rust-backed, async-native (awatch), debounced. Required by TREE-04 and reused in Phase 4 |
| tree-sitter | 0.25.2 | Incremental syntax parsing for TextArea | Required for syntax highlighting in TextArea.code_editor(). Installed via `textual[syntax]` extras |
| tree-sitter-language-pack | 1.0.0 | Pre-compiled grammars for 170+ languages | Provides Language objects for register_language() to extend beyond the 15 built-in languages. Published 2026-03-21 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| watchfiles | watchdog | watchdog uses threads (not asyncio-native), has OS-specific quirks, and known debouncing bugs. watchfiles is simpler and async-native |
| tree-sitter-language-pack | tree-sitter-languages | Unmaintained, no Python 3.13+ support. language-pack is the actively maintained successor |
| Custom search overlay | textual-textarea (3rd party) | 3rd party package with its own TextArea widget; would conflict with Textual's built-in TextArea |

**Installation:**
```bash
uv add "textual[syntax]" watchfiles tree-sitter-language-pack
```

**Version verification:**
- textual: 8.1.1 (installed, verified)
- watchfiles: 1.1.1 (verified PyPI, March 2026)
- tree-sitter: 0.25.2 (verified PyPI)
- tree-sitter-language-pack: 1.0.0 (verified PyPI, March 2026)

## Architecture Patterns

### Recommended Project Structure Changes

```
nano_claude/
  panels/
    file_tree.py      # Replace placeholder with FilteredDirectoryTree
    editor.py          # Replace placeholder with TextArea.code_editor() + search overlay
  widgets/
    search_overlay.py  # New: Ctrl+F search bar widget
  services/
    file_watcher.py    # New: watchfiles integration running in Worker
  models/
    file_buffer.py     # New: unsaved file buffer management
  config/
    settings.py        # Add: HIDDEN_PATTERNS, EXTENSION_TO_LANGUAGE map, file size threshold
```

### Pattern 1: Filtered DirectoryTree with Hidden File Toggle

**What:** Subclass DirectoryTree, override filter_paths to exclude hidden files, provide toggle action.
**When to use:** For the file tree panel (TREE-01).

```python
from pathlib import Path
from typing import Iterable
from textual.widgets import DirectoryTree

HIDDEN_PATTERNS = {".git", "node_modules", "__pycache__", ".venv", ".mypy_cache",
                   ".pytest_cache", ".ruff_cache", ".DS_Store", ".idea", ".vscode"}

class FilteredDirectoryTree(DirectoryTree):
    show_hidden = reactive(False)

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        if self.show_hidden:
            return paths
        return [
            path for path in paths
            if not path.name.startswith(".") and path.name not in HIDDEN_PATTERNS
        ]

    def watch_show_hidden(self, value: bool) -> None:
        self.reload()
```

**Source:** Verified against Textual DirectoryTree docs + actual installed API.

### Pattern 2: File Extension to Language Detection

**What:** Map file extensions to TextArea language names for syntax highlighting.
**When to use:** When opening a file in the editor (EDIT-01).

```python
EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "python", ".pyi": "python",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "javascript",  # Use javascript grammar; TypeScript is separate in language-pack
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".json": "json",
    ".toml": "toml",
    ".yaml": "yaml", ".yml": "yaml",
    ".html": "html", ".htm": "html",
    ".css": "css",
    ".md": "markdown", ".markdown": "markdown",
    ".sql": "sql",
    ".sh": "bash", ".bash": "bash", ".zsh": "bash",
    ".xml": "xml", ".svg": "xml",
    ".regex": "regex",
}

def detect_language(path: Path) -> str | None:
    return EXTENSION_TO_LANGUAGE.get(path.suffix.lower())
```

**Confidence:** HIGH -- verified the 15 built-in language names from Textual source.

### Pattern 3: File Buffer Management for Unsaved Changes

**What:** Maintain in-memory buffers for open files, track modified state, handle file switching without data loss.
**When to use:** Core of the editor panel implementation.

```python
from dataclasses import dataclass, field

@dataclass
class FileBuffer:
    path: Path
    original_content: str  # Content at last save/open
    current_content: str   # Current editor content
    cursor_location: tuple[int, int] = (0, 0)
    scroll_offset: tuple[int, int] = (0, 0)

    @property
    def is_modified(self) -> bool:
        return self.current_content != self.original_content

class BufferManager:
    def __init__(self) -> None:
        self._buffers: dict[Path, FileBuffer] = {}

    def open_file(self, path: Path) -> FileBuffer:
        if path in self._buffers:
            return self._buffers[path]
        content = path.read_text(encoding="utf-8", errors="replace")
        buf = FileBuffer(path=path, original_content=content, current_content=content)
        self._buffers[path] = buf
        return buf

    def save_file(self, path: Path) -> None:
        buf = self._buffers[path]
        path.write_text(buf.current_content, encoding="utf-8")
        buf.original_content = buf.current_content

    def has_unsaved_changes(self) -> bool:
        return any(buf.is_modified for buf in self._buffers.values())

    def get_unsaved_files(self) -> list[Path]:
        return [buf.path for buf in self._buffers.values() if buf.is_modified]
```

### Pattern 4: Search Overlay as Composited Widget

**What:** A search bar widget that overlays the top of the editor panel. Manages its own focus, finds matches via Document API, and highlights via TextArea styling.
**When to use:** For EDIT-06 search-in-file functionality.

```python
from textual.containers import Horizontal
from textual.widgets import Input, Button, Static
from textual.message import Message

class SearchOverlay(Horizontal):
    """Search bar overlaying the editor. Hidden by default."""

    class SearchRequested(Message):
        def __init__(self, query: str, direction: int = 1) -> None:
            super().__init__()
            self.query = query
            self.direction = direction  # 1 = forward, -1 = backward

    DEFAULT_CSS = """
    SearchOverlay {
        dock: top;
        height: 3;
        display: none;
        background: $surface;
        border-bottom: solid $primary;
    }
    SearchOverlay.visible {
        display: block;
    }
    SearchOverlay Input {
        width: 1fr;
    }
    """

    def compose(self):
        yield Input(placeholder="Find...", id="search-input")
        yield Static("0/0", id="search-count")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.post_message(self.SearchRequested(event.value))
```

### Pattern 5: Indentation Auto-Detection

**What:** Detect tabs vs spaces and indent width from the first N lines of a file.
**When to use:** When opening a file, before loading into TextArea.

```python
def detect_indentation(content: str, sample_lines: int = 100) -> tuple[str, int]:
    """Detect indentation style from file content.

    Returns:
        ("spaces", width) or ("tabs", width)
    """
    tab_count = 0
    space_counts: dict[int, int] = {}

    for i, line in enumerate(content.splitlines()):
        if i >= sample_lines:
            break
        if line.startswith("\t"):
            tab_count += 1
        elif line.startswith(" "):
            # Count leading spaces
            stripped = line.lstrip(" ")
            indent = len(line) - len(stripped)
            if indent > 0:
                space_counts[indent] = space_counts.get(indent, 0) + 1

    if tab_count > sum(space_counts.values()):
        return ("tabs", 4)

    # Find most common indent difference (likely 2 or 4)
    if space_counts:
        # GCD of common indents gives indent width
        from math import gcd
        from functools import reduce
        common_indents = sorted(space_counts.keys())
        if common_indents:
            width = reduce(gcd, common_indents)
            return ("spaces", max(2, min(8, width)))

    return ("spaces", 4)  # Default
```

### Pattern 6: Filesystem Watcher in Textual Worker

**What:** Run watchfiles awatch() in a background Textual Worker, post messages when files change.
**When to use:** For TREE-04 auto-refresh and future Phase 4 file change detection.

```python
from textual.worker import work
from textual.message import Message
from watchfiles import awatch, DefaultFilter, Change
import anyio

class FileSystemChanged(Message):
    def __init__(self, changes: set[tuple[Change, str]]) -> None:
        super().__init__()
        self.changes = changes

class FileWatcherService:
    def __init__(self, app, watch_path: Path) -> None:
        self.app = app
        self.watch_path = watch_path
        self._stop_event: anyio.Event | None = None

    async def start(self) -> None:
        self._stop_event = anyio.Event()
        watcher_filter = DefaultFilter(
            ignore_dirs=("__pycache__", ".git", "node_modules", ".venv",
                         ".mypy_cache", ".pytest_cache", ".ruff_cache")
        )
        async for changes in awatch(
            self.watch_path,
            watch_filter=watcher_filter,
            debounce=800,  # 800ms debounce for reasonable responsiveness
            stop_event=self._stop_event,
        ):
            self.app.post_message(FileSystemChanged(changes))

    def stop(self) -> None:
        if self._stop_event:
            self._stop_event.set()
```

### Anti-Patterns to Avoid

- **Direct panel communication:** Never have FileTreePanel hold a reference to EditorPanel. Use Textual messages exclusively. The app handles coordination.
- **Synchronous file reading:** Never read files in a message handler on the main thread. Use `run_worker()` or `@work` for any file I/O.
- **Polling for file changes:** Never use a timer to check if files changed. Use watchfiles awatch().
- **Rebuilding DirectoryTree on refresh:** Never destroy and recreate the tree widget. Use `tree.reload()` which preserves expanded state.
- **Blocking the event loop with large files:** Never load a 10MB file synchronously. Check file size first, warn or refuse for extremely large files.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| File tree widget | Custom tree from scratch | Textual DirectoryTree | Async loading, keyboard nav, virtual scroll all built in |
| Code editor | Custom text editing | TextArea.code_editor() | Undo/redo, selection, cursor, clipboard, line numbers built in |
| Syntax highlighting | Pygments-based highlighting | TextArea + tree-sitter | Incremental parsing (only re-parses changed regions), not full-file |
| Filesystem watching | os.stat polling or threading | watchfiles awatch() | Rust-backed, async-native, debounced, cross-platform |
| Undo/redo | Custom command pattern | TextArea built-in | max_checkpoints=50 by default, just works |
| Tree keyboard nav | Custom key handlers | Tree widget BINDINGS | up/down/enter/space/shift+arrows all built in |

**Key insight:** Textual provides 80% of what this phase needs out of the box. The custom work is: search overlay, file buffer management, indentation detection, and wiring everything together via messages.

## Common Pitfalls

### Pitfall 1: Keybinding Conflicts Between TextArea and App

**What goes wrong:** TextArea has built-in bindings for `ctrl+f` (delete_word_right), `ctrl+e` (cursor_line_end), `ctrl+b` (not used, but close), `ctrl+k` (delete to line end), `ctrl+u` (delete to line start). These conflict with app-level panel focus shortcuts and the search shortcut.
**Why it happens:** TextArea was designed as a standalone widget, not embedded in a multi-panel app with its own keybinding layer.
**How to avoid:**
- App bindings have `priority=True`, so they win. This means `ctrl+f` will trigger search (good) and NOT delete-word-right (acceptable loss).
- `ctrl+e` will focus the editor panel (which is a no-op when already focused). Users lose the "cursor to line end" shortcut -- but `End` key does the same thing.
- The TextArea binding for `ctrl+e` has `priority=False`, so the app binding takes precedence.
- Document the trade-offs: `End` replaces `ctrl+e` for cursor-line-end, `Delete` or `ctrl+d` replaces `ctrl+f` for delete-right.
**Warning signs:** Users report "ctrl+F opens search but I can't delete words forward."

### Pitfall 2: Tree Expansion State Lost on Reload

**What goes wrong:** Calling `tree.reload()` refreshes the tree but collapses all expanded directories, disorienting the user.
**Why it happens:** `reload()` re-reads the filesystem and repopulates nodes. If expanded state is not preserved, everything starts collapsed.
**How to avoid:**
- Before `reload()`, capture the set of expanded directory paths by walking the tree nodes.
- After `reload()` completes (it returns `AwaitComplete`), re-expand the previously expanded nodes.
- Use `await tree.reload()` to ensure the tree is stable before re-expanding.
```python
async def reload_preserving_state(tree: DirectoryTree) -> None:
    expanded = set()
    for node in tree.root.children:
        _collect_expanded(node, expanded)
    await tree.reload()
    # Re-expand saved paths after reload completes
    for node in tree.root.children:
        _restore_expanded(node, expanded)
```
**Warning signs:** After a `git checkout` or external file addition, the tree collapses to root.

### Pitfall 3: TextArea Performance with Large Files

**What goes wrong:** Opening files with >2000 lines causes noticeable lag on keystroke, especially with syntax highlighting enabled.
**Why it happens:** tree-sitter's Python bindings have a known quadratic scaling issue in `Query.captures`. Textual PRs #5642 and #5645 added lazy highlighting and background parsing to mitigate this.
**How to avoid:**
- Textual 8.1.1 should include the lazy highlighting fixes -- verify this.
- Set a file size threshold (e.g., 1MB or 50,000 lines). Above this, either disable syntax highlighting or warn the user.
- Test with realistic file sizes during development (2,000-10,000 lines), not just small test files.
**Warning signs:** Editor feels smooth with 50-line files but lags on real codebases.

### Pitfall 4: File Encoding Errors

**What goes wrong:** Opening a binary file or a file with non-UTF-8 encoding crashes the editor or shows garbage.
**Why it happens:** `path.read_text()` without error handling raises UnicodeDecodeError on binary files.
**How to avoid:**
- Use `path.read_text(encoding="utf-8", errors="replace")` to handle encoding issues gracefully.
- Check file size and detect binary files (check for null bytes in first 8KB) before attempting to open.
- Show a user-friendly message for binary files: "Cannot display binary file."
**Warning signs:** App crashes when user clicks on a `.png` or `.wasm` file in the tree.

### Pitfall 5: Search Highlight Clearing

**What goes wrong:** After closing the search overlay, match highlights remain visible in the editor, confusing the user.
**Why it happens:** TextArea does not have built-in search highlighting. Any visual highlighting added (via selection or custom rendering) must be explicitly cleaned up.
**How to avoid:**
- When search overlay closes (Escape), clear all search-related state and force a re-render of the TextArea.
- Use TextArea's `selection` for current match highlighting (moves with next/prev), and a separate visual mechanism (like a custom theme component) for all-match highlighting.
- The simplest v1 approach: only highlight the current match via cursor_location/selection; skip all-match highlighting if it's too complex.
**Warning signs:** Old search highlights visible after closing search, especially after scrolling.

### Pitfall 6: Watchfiles Debounce Too Aggressive or Too Weak

**What goes wrong:** With the default 1600ms debounce, users experience a noticeable delay between external file changes and tree refresh. Or with too-low debounce, a `git checkout` causes dozens of rapid tree reloads.
**Why it happens:** watchfiles default debounce is 1600ms. For git operations that touch hundreds of files, this is appropriate. For single file additions, it feels slow.
**How to avoid:**
- Use 800ms debounce as a compromise.
- Batch all changes in a debounce window into a single tree.reload() call.
- For Phase 4 (auto-reload of open files), this same watcher can also trigger editor reload, but that should be handled separately from tree refresh.

## Code Examples

### Opening a File in the Editor (TREE-03 + EDIT-01)

```python
# In app.py - handle file selection from tree
from textual.widgets import DirectoryTree

class NanoClaudeApp(App):
    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        """User selected a file in the tree -- open it in the editor."""
        editor = self.query_one(EditorPanel)
        editor.open_file(event.path)

# In panels/editor.py
class EditorPanel(BasePanel):
    current_file: reactive[Path | None] = reactive(None)

    def compose(self):
        yield SearchOverlay(id="search-overlay")
        self._text_area = TextArea.code_editor(
            "",
            language=None,
            theme="monokai",
            soft_wrap=False,
            id="code-editor",
        )
        yield self._text_area

    def open_file(self, path: Path) -> None:
        # Save current buffer state before switching
        if self.current_file is not None:
            self._save_buffer_state()

        buf = self._buffer_manager.open_file(path)
        language = detect_language(path)
        indent_type, indent_width = detect_indentation(buf.current_content)

        self._text_area.load_text(buf.current_content)
        self._text_area.language = language
        self._text_area.indent_width = indent_width
        self._text_area.cursor_location = buf.cursor_location

        self.current_file = path
        self._update_title()

    def _update_title(self) -> None:
        if self.current_file is None:
            self.panel_title = "Editor"
            return
        name = self.current_file.name
        buf = self._buffer_manager._buffers.get(self.current_file)
        modified = " [bold red]●[/]" if (buf and buf.is_modified) else ""
        self.panel_title = f"{name}{modified}"
```

**Source:** Verified against TextArea.code_editor() signature, load_text() method, and Document API.

### Saving a File (EDIT-04)

```python
# In app.py
class NanoClaudeApp(App):
    BINDINGS = [
        # ... existing bindings ...
        Binding("ctrl+s", "save_file", "Save", id="file.save", priority=True),
    ]

    def action_save_file(self) -> None:
        editor = self.query_one(EditorPanel)
        editor.save_current_file()

# In panels/editor.py
class EditorPanel(BasePanel):
    def save_current_file(self) -> None:
        if self.current_file is None:
            return
        buf = self._buffer_manager._buffers.get(self.current_file)
        if buf is None:
            return
        buf.current_content = self._text_area.text
        self._buffer_manager.save_file(self.current_file)
        self._update_title()
        self.notify(f"Saved {self.current_file.name}", severity="information")
```

### Search Implementation (EDIT-06)

```python
# In panels/editor.py - search handling
def find_matches(self, query: str) -> list[tuple[int, int]]:
    """Find all occurrences of query in the document. Returns (row, col) pairs."""
    if not query:
        return []
    matches = []
    doc = self._text_area.document
    query_lower = query.lower()
    for row in range(doc.line_count):
        line = doc.get_line(row).lower()
        col = 0
        while True:
            idx = line.find(query_lower, col)
            if idx == -1:
                break
            matches.append((row, idx))
            col = idx + 1
    return matches

def jump_to_match(self, row: int, col: int, query_len: int) -> None:
    """Move cursor to match and select it."""
    self._text_area.selection = Selection(
        start=(row, col),
        end=(row, col + query_len),
    )
    self._text_area.scroll_cursor_visible()
```

**Source:** Verified Document.get_line(), Document.line_count, TextArea.selection, TextArea.scroll_cursor_visible() all exist.

### Quit with Unsaved Changes Prompt

```python
# In app.py
class NanoClaudeApp(App):
    def action_quit(self) -> None:
        editor = self.query_one(EditorPanel)
        if editor.has_unsaved_changes():
            self.push_screen(UnsavedChangesScreen())
        else:
            self.exit()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| tree-sitter-languages | tree-sitter-language-pack 1.0.0 | March 2026 | Old package unmaintained; new package covers 170+ languages with pre-compiled wheels |
| Full tree re-query per keystroke | Lazy 50-line block highlighting | Textual PR #5642 | Fixes quadratic scaling for files >1000 lines |
| Synchronous tree loading | Async DirectoryTree with lazy expand | Built into Textual | Large projects don't block UI during tree population |
| watchdog for filesystem monitoring | watchfiles (Rust-backed) | Standard since 2024 | Async-native, simpler API, better cross-platform behavior |

**Deprecated/outdated:**
- `tree-sitter-languages`: Unmaintained, no Python 3.13+. Use `tree-sitter-language-pack` instead.
- `textual-terminal`: 16 commits, single contributor, "extremely slow" per Textual maintainer. Do not use.

## Open Questions

1. **TextArea all-match highlighting**
   - What we know: TextArea supports selection (for current match) and themes. No built-in "highlight all matches" feature.
   - What's unclear: Whether TextArea's custom theme/component styling can apply multiple highlight regions simultaneously (not just the selection). May need to use the underlying Rich style system.
   - Recommendation: Start with current-match-only highlighting via selection. Add all-match highlighting as a follow-up if the styling mechanism supports it. The CONTEXT.md specifies all matches highlighted simultaneously -- this may require a custom TextArea subclass with render override.

2. **tree-sitter-language-pack integration with TextArea**
   - What we know: TextArea.register_language() takes a name, Language object, and highlight_query string. tree-sitter-language-pack provides `get_language("name")` returning Language objects.
   - What's unclear: Whether the language-pack includes highlight queries, or just Language objects. The highlight queries are typically in `queries/highlights.scm` in each tree-sitter grammar repository.
   - Recommendation: Start with the 15 built-in languages (sufficient for most use cases). If more languages are needed, use `from tree_sitter_language_pack import get_language` plus manually bundled highlight queries.

3. **Preserving tree expansion state across reload()**
   - What we know: `tree.reload()` returns `AwaitComplete`. Nodes have `is_expanded` property.
   - What's unclear: Whether reload() completely replaces the tree data (losing expansion state) or whether Textual preserves it internally.
   - Recommendation: Implement the capture-and-restore pattern defensively. Test with a simple scenario: expand a directory, add a file externally, verify expansion is preserved after watcher triggers reload.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24.x |
| Config file | pyproject.toml `[tool.pytest.ini_options]` with `asyncio_mode = "auto"` |
| Quick run command | `.venv/bin/python -m pytest tests/ -x -q` |
| Full suite command | `.venv/bin/python -m pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TREE-01 | DirectoryTree renders in file-tree panel with filtered paths | integration | `.venv/bin/python -m pytest tests/test_file_tree.py::test_directory_tree_renders -x` | Wave 0 |
| TREE-02 | Keyboard nav (up/down/enter/space) works in tree | integration | `.venv/bin/python -m pytest tests/test_file_tree.py::test_tree_keyboard_navigation -x` | Wave 0 |
| TREE-03 | Selecting file in tree opens it in editor | integration | `.venv/bin/python -m pytest tests/test_file_tree.py::test_file_selection_opens_editor -x` | Wave 0 |
| TREE-04 | Tree refreshes when files added externally | integration | `.venv/bin/python -m pytest tests/test_file_watcher.py::test_tree_refresh_on_external_change -x` | Wave 0 |
| EDIT-01 | File opens with syntax highlighting and correct language | integration | `.venv/bin/python -m pytest tests/test_editor.py::test_open_file_with_highlighting -x` | Wave 0 |
| EDIT-02 | Standard text editing (insert/delete/selection) works | integration | `.venv/bin/python -m pytest tests/test_editor.py::test_text_editing_operations -x` | Wave 0 |
| EDIT-03 | Undo/redo works | integration | `.venv/bin/python -m pytest tests/test_editor.py::test_undo_redo -x` | Wave 0 |
| EDIT-04 | Ctrl+S saves file to disk | integration | `.venv/bin/python -m pytest tests/test_editor.py::test_save_file -x` | Wave 0 |
| EDIT-05 | Line numbers visible | integration | `.venv/bin/python -m pytest tests/test_editor.py::test_line_numbers_visible -x` | Wave 0 |
| EDIT-06 | Ctrl+F opens search, finds matches, navigates | integration | `.venv/bin/python -m pytest tests/test_search.py::test_search_find_and_navigate -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/python -m pytest tests/ -x -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_file_tree.py` -- covers TREE-01, TREE-02, TREE-03
- [ ] `tests/test_editor.py` -- covers EDIT-01, EDIT-02, EDIT-03, EDIT-04, EDIT-05
- [ ] `tests/test_search.py` -- covers EDIT-06
- [ ] `tests/test_file_watcher.py` -- covers TREE-04
- [ ] `tests/test_file_buffer.py` -- covers buffer management, unsaved changes tracking
- [ ] Framework dependency: `uv add "textual[syntax]" watchfiles tree-sitter-language-pack`

## Sources

### Primary (HIGH confidence)
- Textual TextArea source code: `/Users/yaroslavpankovych/nano-claude/.venv/lib/python3.12/site-packages/textual/widgets/_text_area.py` -- verified code_editor() signature, BINDINGS, register_language(), BUILTIN_LANGUAGES, document API
- Textual _tree_sitter.py source: verified Language loading mechanism via `import_module(f"tree_sitter_{name}")`
- Textual DirectoryTree installed API: verified FileSelected message, filter_paths, reload(), reload_node()
- [Textual TextArea docs](https://textual.textualize.io/widgets/text_area/) -- code_editor factory, language setting, undo/redo, register_language
- [Textual DirectoryTree docs](https://textual.textualize.io/widgets/directory_tree/) -- FileSelected, filter_paths, reload, keyboard navigation
- [watchfiles API reference](https://watchfiles.helpmanual.io/api/watch/) -- awatch() signature, stop_event, debounce, DefaultFilter
- [watchfiles Filters API](https://watchfiles.helpmanual.io/api/filters/) -- DefaultFilter exclusions, custom filter creation
- [PyPI watchfiles 1.1.1](https://pypi.org/project/watchfiles/) -- version verified
- [PyPI tree-sitter 0.25.2](https://pypi.org/project/tree-sitter/) -- version verified
- [PyPI tree-sitter-language-pack 1.0.0](https://pypi.org/project/tree-sitter-language-pack/) -- version verified March 2026

### Secondary (MEDIUM confidence)
- [tree-sitter-language-pack GitHub](https://github.com/Goldziher/tree-sitter-language-pack) -- API for get_language(), get_parser()
- [textual-tree-sitter-languages PyPI](https://pypi.org/project/textual-tree-sitter-languages/) -- Will McGugan's fork for Python 3.13 compat
- `.planning/research/PITFALLS.md` -- TextArea quadratic scaling (Pitfall 3), keybinding conflicts (Pitfall 5)
- `.planning/research/ARCHITECTURE.md` -- Message-driven communication pattern, data flow diagrams
- `.planning/research/STACK.md` -- Stack decisions and alternatives

### Tertiary (LOW confidence)
- All-match highlighting in TextArea -- no official documentation found; may require custom render override

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries verified installed or on PyPI, APIs tested locally
- Architecture: HIGH -- patterns derived from Textual source code inspection and official docs
- Pitfalls: HIGH -- keybinding conflicts verified by running actual code; performance concerns from Textual GitHub PRs
- Search overlay: MEDIUM -- no Textual precedent for in-widget search overlay; custom implementation needed
- All-match highlighting: LOW -- unclear if TextArea styling supports multiple highlight regions

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (stable ecosystem, Textual minor versions unlikely to break APIs)

---
*Phase: 02-file-tree-and-code-editor*
*Research completed: 2026-03-22*
