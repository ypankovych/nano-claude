# Phase 4: Change Detection and Auto-Jump - Research

**Researched:** 2026-03-23
**Domain:** Filesystem change detection, line-level diffing, editor auto-navigation, change highlighting in TUI
**Confidence:** HIGH

## Summary

Phase 4 is the killer feature of nano-claude: when Claude edits files via the embedded PTY, the editor automatically detects the changes, notifies the user, highlights modified lines, and provides a unified diff view. The existing codebase provides strong foundations -- `FileWatcherService` already watches the project directory with 800ms debounce, `SearchableTextArea.render_line()` already supports overlay highlighting via Strip crop/join, and `BufferManager` already tracks file content per path.

The core technical challenges are: (1) capturing "before" snapshots of file content before Claude's edits arrive so we can compute diffs, (2) extending `render_line` to support change-highlight styles alongside existing search-highlight styles, (3) building a read-only diff view mode that replaces the normal editor temporarily, and (4) coordinating notifications with auto-reload when multiple files change simultaneously.

**Primary recommendation:** Use Python's stdlib `difflib.SequenceMatcher.get_opcodes()` for line-level change detection (added/modified/deleted line ranges), `difflib.unified_diff()` for the diff view content, and extend the existing `render_line` override in `SearchableTextArea` to layer change highlights. No new dependencies are needed -- everything builds on stdlib + existing infrastructure.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- When Claude edits a file: show a notification first, NOT instant jump -- "Claude edited foo.py" toast + status bar message with "Ctrl+G to jump"
- If user is actively editing another file: notification only, don't steal focus -- let user jump when ready
- If Claude edits multiple files in one response: show a list of all changed files so user can pick which to open
- Detection source: filesystem watcher (already exists from Phase 2) catches all edits regardless of how Claude makes them (Write, Edit, Bash sed, etc.)
- Changed lines get a tinted background color (green for added, yellow for modified) -- more visible than gutter markers alone
- Highlights persist until the user starts editing the file OR Claude makes new changes -- then previous highlights clear
- Highlight style reuses the SearchableTextArea render_line override pattern from Phase 2
- Unified inline diff (green/red lines like `git diff`) -- toggled with Ctrl+D
- Replaces the normal editor view temporarily while active; toggle again to return to normal editing
- Compares: version before Claude's edit (snapshot) vs current file on disk (after Claude saved)
- Need to capture a "before" snapshot of files before Claude edits them -- snapshot on first filesystem change detection per file
- Diff view is read-only -- can't edit while viewing the diff
- When an open file changes on disk (git checkout, external tool): silent auto-reload without asking -- seamless
- EXCEPTION: if the file has unsaved edits AND it changed on disk, prompt the user: "foo.py changed on disk but has unsaved edits. Reload (lose edits) or keep?"
- Uses the existing FileWatcherService from Phase 2 -- extend its handler to also reload open editor buffers

### Claude's Discretion
- Exact shortcut for "jump to changed file" (suggested Ctrl+G)
- How the changed-files list UI looks (overlay, sidebar, or notification stack)
- Snapshot storage strategy (in-memory dict of path -> content)
- How to handle very large diffs (scrolling, truncation)
- Diff view color scheme (green/red intensity, background vs foreground)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CHNG-01 | When Claude edits a file, the editor automatically jumps to that file and highlights the changed lines | FileWatcherService detects changes -> `difflib.SequenceMatcher` computes changed line ranges -> `render_line` override applies green/yellow backgrounds -> notification + keybinding for jump |
| CHNG-02 | User can toggle a git-style diff view (green additions, red deletions) of Claude's changes via a keyboard shortcut | `difflib.unified_diff()` generates diff content -> read-only TextArea or Static widget renders with colored lines -> Ctrl+D toggles between normal and diff mode |
| CHNG-03 | A filesystem watcher detects external file changes (git operations, other tools) and auto-reloads open files | Existing `FileWatcherService` + `FileSystemChanged` message -> extend `on_file_system_changed` handler to reload open `BufferManager` buffers, with conflict prompt for unsaved edits |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| difflib (stdlib) | Python 3.12 | Line-level diff computation | Zero dependency; `SequenceMatcher.get_opcodes()` gives exact change ranges (equal/replace/insert/delete); `unified_diff()` generates standard git-style output |
| watchfiles | 1.1.1 | Filesystem change detection | Already installed and in use (FileWatcherService); Rust-backed, uses FSEvents on macOS; provides Change enum (added/modified/deleted) with path strings |
| textual | 8.1.1 | TUI framework | Already installed; provides App.notify() with Rich markup support including `@click` action links; OptionList for selection UIs; ModalScreen for conflict prompts |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib (stdlib) | Python 3.12 | Path manipulation and file I/O | Already used throughout codebase for all file operations |
| rich.style (stdlib via textual) | - | Style objects for change highlights | Already used in SearchableTextArea for match highlighting |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| difflib | unidiff (PyPI) | Better for parsing existing .diff files, but difflib is stdlib and we're generating diffs from content strings |
| difflib | whatthepatch | Parses patch files; overkill when we control both old and new content |
| In-memory snapshots | Git stash/commit-based | Would require git dependency and subprocess calls; in-memory is simpler, faster, and works for non-git projects |

**Installation:**
No new dependencies needed. Everything is either stdlib or already installed.

## Architecture Patterns

### Recommended Project Structure
```
nano_claude/
  services/
    file_watcher.py          # EXISTING -- extend FileSystemChanged handling
    change_tracker.py         # NEW -- ChangeTracker: snapshots, diff computation, changed-line tracking
  models/
    file_buffer.py            # EXISTING -- extend with reload_from_disk(), snapshot fields
  widgets/
    searchable_text_area.py   # EXISTING -- extend render_line for change highlights
    diff_view.py              # NEW -- DiffView widget: read-only colored unified diff display
    changed_files_overlay.py  # NEW -- overlay listing files Claude changed, user picks one
  panels/
    editor.py                 # EXISTING -- extend with diff toggle, jump-to-change, auto-reload
  config/
    settings.py               # EXISTING -- add change highlight colors, new keybindings
```

### Pattern 1: ChangeTracker Service (Snapshot + Diff Engine)
**What:** A pure-Python class that maintains in-memory "before" snapshots and computes line-level diffs when files change.
**When to use:** Called from `on_file_system_changed` whenever the watcher reports a modification.
**Example:**
```python
# Source: Python stdlib difflib documentation
import difflib
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class FileChange:
    """Represents detected changes in a single file."""
    path: Path
    added_lines: list[int]       # Line numbers in the NEW file that were added
    modified_lines: list[int]    # Line numbers in the NEW file that were modified
    deleted_count: int           # Number of lines deleted (for info display)
    old_content: str             # Snapshot before change
    new_content: str             # Content after change

class ChangeTracker:
    """Tracks file snapshots and computes diffs when files change on disk."""

    def __init__(self) -> None:
        self._snapshots: dict[Path, str] = {}  # path -> content before change
        self._pending_changes: dict[Path, FileChange] = {}  # most recent change per file

    def ensure_snapshot(self, path: Path) -> None:
        """Capture a snapshot of a file's current content if not already tracked."""
        if path not in self._snapshots:
            try:
                self._snapshots[path] = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass

    def compute_change(self, path: Path) -> FileChange | None:
        """Compare current file content against snapshot, return changes."""
        old = self._snapshots.get(path)
        if old is None:
            return None  # No snapshot -- can't diff

        try:
            new = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

        old_lines = old.splitlines()
        new_lines = new.splitlines()

        sm = difflib.SequenceMatcher(None, old_lines, new_lines)
        added: list[int] = []
        modified: list[int] = []
        deleted_count = 0

        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "insert":
                added.extend(range(j1, j2))
            elif tag == "replace":
                modified.extend(range(j1, j2))
            elif tag == "delete":
                deleted_count += (i2 - i1)

        if not added and not modified and deleted_count == 0:
            return None  # No actual changes

        change = FileChange(
            path=path,
            added_lines=added,
            modified_lines=modified,
            deleted_count=deleted_count,
            old_content=old,
            new_content=new,
        )
        self._pending_changes[path] = change
        # Update snapshot to new content (so next change compares against this)
        self._snapshots[path] = new
        return change

    def get_unified_diff(self, path: Path) -> str:
        """Generate unified diff string for a file's most recent change."""
        change = self._pending_changes.get(path)
        if change is None:
            return ""
        diff_lines = difflib.unified_diff(
            change.old_content.splitlines(keepends=True),
            change.new_content.splitlines(keepends=True),
            fromfile=f"a/{path.name}",
            tofile=f"b/{path.name}",
        )
        return "".join(diff_lines)

    def clear_change(self, path: Path) -> None:
        """Clear pending change for a file (user started editing or new Claude change)."""
        self._pending_changes.pop(path, None)

    def clear_all(self) -> None:
        """Clear all tracked changes and snapshots."""
        self._snapshots.clear()
        self._pending_changes.clear()
```

### Pattern 2: Extending render_line for Change Highlights
**What:** Layer change-highlight styles on top of the existing search-highlight styles in `SearchableTextArea.render_line()`.
**When to use:** When a file has pending change highlights (green for added lines, yellow for modified lines).
**Example:**
```python
# Source: Existing SearchableTextArea.render_line pattern in nano_claude/widgets/searchable_text_area.py
from rich.style import Style

# Change highlight styles
_ADDED_LINE_STYLE = Style(bgcolor="dark_green")      # Green tint for added lines
_MODIFIED_LINE_STYLE = Style(bgcolor="dark_goldenrod") # Yellow tint for modified lines

def render_line(self, y: int) -> Strip:
    """Render a line with search AND change highlights."""
    strip = super().render_line(y)  # Gets base + search highlights

    if not self._change_highlights:
        return strip

    scroll_x, scroll_y = self.scroll_offset
    doc_row = scroll_y + y

    if doc_row in self._added_lines:
        style = _ADDED_LINE_STYLE
    elif doc_row in self._modified_lines:
        style = _MODIFIED_LINE_STYLE
    else:
        return strip

    # Apply background tint to the ENTIRE line (full strip width)
    return self._apply_style_to_range(strip, 0, strip.cell_length, style)
```

### Pattern 3: Notification with Action Link
**What:** Use Textual's Rich markup in `App.notify()` to include a clickable action link.
**When to use:** When Claude edits a file and the user should be offered a quick jump.
**Example:**
```python
# Source: Textual documentation on actions in markup
# Textual 8.1.1 supports @click action links in notify() markup

# Simple toast with keybinding hint
self.notify(
    f"Claude edited [bold]{path.name}[/bold] -- Ctrl+J to jump",
    title="File Changed",
    severity="information",
    timeout=8,
)

# Update status bar as well
self.sub_title = f"Claude edited {path.name} | Ctrl+J to jump"
```

### Pattern 4: Diff View as Temporary Read-Only Widget
**What:** Replace the normal TextArea with a read-only diff view widget when toggled.
**When to use:** User presses Ctrl+D to see what Claude changed.
**Example:**
```python
# The diff view can be a Static widget with Rich Text coloring,
# or a read-only TextArea. Static is simpler and sufficient since
# diff view is not editable.

from rich.text import Text
from textual.widgets import Static

class DiffView(Static):
    """Read-only unified diff display with colored lines."""

    DEFAULT_CSS = """
    DiffView {
        overflow-y: auto;
        overflow-x: auto;
        width: 1fr;
        height: 1fr;
    }
    """

    def set_diff(self, diff_text: str) -> None:
        """Parse unified diff and render with colors."""
        result = Text()
        for line in diff_text.splitlines():
            if line.startswith("+++") or line.startswith("---"):
                result.append(line + "\n", style="bold")
            elif line.startswith("@@"):
                result.append(line + "\n", style="cyan")
            elif line.startswith("+"):
                result.append(line + "\n", style="green")
            elif line.startswith("-"):
                result.append(line + "\n", style="red")
            else:
                result.append(line + "\n")
        self.update(result)
```

### Anti-Patterns to Avoid
- **Parsing PTY output to detect file edits:** Do NOT try to detect Claude's file edits by parsing the terminal output for "[Write]" or "[Edit]" tool markers. The filesystem watcher catches ALL edits (including Bash sed, MCP tools, subagents). PTY parsing is fragile and incomplete.
- **Instant focus-steal on change detection:** Do NOT auto-jump the editor to the changed file immediately. The user may be mid-edit. Always notify first, let user jump when ready.
- **Storing snapshots on disk:** Do NOT write snapshot files to disk. In-memory `dict[Path, str]` is simpler, avoids cleanup issues, and is fast enough for projects with < 100 simultaneously tracked files.
- **Full file re-render on change highlight update:** Do NOT call `load_text()` to re-render the file after applying change highlights. Only call `refresh()` to trigger a re-render of visible lines via `render_line`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Line-level diff computation | Custom string comparison / manual line matching | `difflib.SequenceMatcher.get_opcodes()` | Handles insert/delete/replace/equal correctly; SequenceMatcher uses Ratcliff/Obershelp with O(n^2) worst case but fast heuristics for real code |
| Unified diff generation | Manual +/- line formatting | `difflib.unified_diff()` | Standard format, handles context lines, headers, and hunk markers correctly |
| File change detection | Polling loop or PTY output parsing | Existing `FileWatcherService` with `watchfiles.awatch()` | Already implemented, uses FSEvents on macOS, Rust-backed, 800ms debounce |
| Toast notifications | Custom popup widget | `App.notify()` with Rich markup | Built into Textual 8.1.1, supports `@click` action links, auto-timeout, severity levels |
| Modal conflict prompt | Custom screen from scratch | `ModalScreen` pattern (already used for `UnsavedChangesScreen`) | Established pattern in codebase with dismiss callbacks |

**Key insight:** This phase is mostly wiring and UI -- connecting the existing filesystem watcher to diff computation and editor updates. The only "new" algorithms are diff computation (stdlib handles it) and change highlight rendering (existing pattern handles it).

## Common Pitfalls

### Pitfall 1: Snapshot Timing Race Condition
**What goes wrong:** If the snapshot is captured AFTER the first filesystem change event fires, the "before" content is already the changed content, and the diff shows nothing.
**Why it happens:** The FileWatcherService has an 800ms debounce. Claude may write the file and the watcher event arrives after the file is already changed. If you try to read the file as "before" at event-handling time, you get the new content.
**How to avoid:** Capture snapshots PROACTIVELY for all open buffers. The `BufferManager` already holds the last-loaded content in `FileBuffer.original_content` (content at last open/save). Use this as the "before" snapshot for open files. For files not currently open in the editor, capture the snapshot when the `ChangeTracker` first encounters a change event for a path where no snapshot exists yet -- but this means the first change to an un-opened file will have no diff. This is acceptable; the diff is most valuable for files already open in the editor.
**Warning signs:** Diff view always shows "no changes" even though the file was clearly modified.

### Pitfall 2: Change Highlights Interfering with Search Highlights
**What goes wrong:** Both search highlights and change highlights use `render_line` overlay via `_apply_style_to_range`. If applied carelessly, one overwrites the other -- the user sees search highlights but not change highlights, or vice versa.
**Why it happens:** `_apply_style_to_range` merges styles with `seg.style + new_style`. If both search and change highlights apply to the same cell, the last one applied wins for conflicting properties (like `bgcolor`).
**How to avoid:** Apply change highlights FIRST (as full-line background tint), then search highlights on top (as character-range highlights with more specific/brighter colors). The search highlight's `bgcolor` will override the change highlight's `bgcolor` on the matched characters, which is the desired visual behavior. In `render_line`, call the parent class (which applies search highlights) and then overlay change highlights at the full-line level. Actually -- reverse: apply change highlights in the subclass, THEN let the parent apply search highlights on top. This means the `SearchableTextArea` render_line chain should be: base TextArea render -> change highlights (full line bg) -> search highlights (specific character ranges). Since search uses brighter/more specific styles, they visually "pop" above the change tint.
**Warning signs:** Opening a file with both active search and change highlights shows only one or the other.

### Pitfall 3: FileWatcher Event Storm During Git Operations
**What goes wrong:** Running `git checkout` or `git pull` changes dozens or hundreds of files at once. Each triggers a change event. The handler tries to compute diffs, reload buffers, and show notifications for all of them, flooding the UI with toasts and causing lag.
**Why it happens:** The 800ms debounce batches some events, but a large git operation can span multiple debounce windows. Each batch can contain many file changes.
**How to avoid:** (1) Batch all changes within a single `FileSystemChanged` event (watchfiles already does this via debounce). (2) For the notification, show ONE aggregate notification: "12 files changed" instead of 12 individual toasts. (3) Only compute diffs for files currently open in the BufferManager, not for all changed files. (4) For the changed-files overlay, populate it from the watchfiles change set but lazily compute diffs only when the user selects a file.
**Warning signs:** Running `git checkout` produces a wall of toast notifications and the UI freezes for several seconds.

### Pitfall 4: Auto-Reload Losing User's Cursor Position and Scroll
**What goes wrong:** When auto-reloading a file that changed on disk, `open_file()` calls `load_text()` which resets the cursor to (0,0) and scroll to the top. The user loses their place.
**Why it happens:** `TextArea.load_text()` replaces the entire document, which resets cursor and scroll state.
**How to avoid:** When reloading a file that changed externally, save the cursor position and scroll offset BEFORE reload, then restore them AFTER. If the file is shorter than the old cursor position, clamp to the last line. The `FileBuffer` already stores `cursor_location` and `scroll_offset` -- use these.
**Warning signs:** Every time Claude edits a file, the editor jumps to line 1 even though the user was reading line 500.

### Pitfall 5: Ctrl+D and Ctrl+G Binding Conflicts
**What goes wrong:** Ctrl+D is already bound by Textual's TextArea to "delete character right" (`delete_right` action). Ctrl+G is already used in the search overlay for "next match". Using these for diff toggle and jump-to-change creates confusion.
**Why it happens:** TextArea has 16 built-in Ctrl+key bindings. The search overlay locally handles Ctrl+G. New bindings must be registered at the App level with `priority=True` to override, but this breaks the original functionality.
**How to avoid:** For diff toggle: Use Ctrl+D at the App level with `priority=True`. This overrides TextArea's delete_right. The Delete key still works for delete-right, so the loss is minimal and Ctrl+D for diff is more discoverable. For jump-to-change: Use Ctrl+J (not Ctrl+G) since Ctrl+J is completely unused in the codebase and in TextArea's default bindings. Ctrl+G conflict with search overlay's "next match" would be confusing.
**Warning signs:** User presses Ctrl+D expecting to see the diff but a character gets deleted instead. User presses Ctrl+G and gets "next search match" instead of jumping to changed file.

### Pitfall 6: Diff View Toggle Doesn't Restore Editor State
**What goes wrong:** Toggling diff view replaces the TextArea content with diff text. Toggling back requires restoring the original file content, cursor position, language, and all state.
**Why it happens:** If the diff view is implemented by loading diff text into the same TextArea, all editor state is destroyed.
**How to avoid:** Use a SEPARATE widget for the diff view (e.g., a `DiffView(Static)` or a separate read-only `TextArea`). Toggle visibility of the two widgets: when diff mode is on, hide the `SearchableTextArea` and show the `DiffView`; when toggled off, hide `DiffView` and show `SearchableTextArea`. This preserves all editor state without saving/restoring.
**Warning signs:** Toggling diff view and back loses the user's cursor position, unsaved edits, or search state.

## Code Examples

Verified patterns from existing codebase and stdlib:

### Computing Changed Line Ranges with difflib
```python
# Source: Python 3.12 stdlib difflib documentation
import difflib

old_lines = old_content.splitlines()
new_lines = new_content.splitlines()

sm = difflib.SequenceMatcher(None, old_lines, new_lines)
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    # tag is one of: 'equal', 'replace', 'insert', 'delete'
    # i1:i2 = range in old_lines, j1:j2 = range in new_lines
    if tag == "insert":
        # Lines j1..j2 in new_lines are new (added)
        pass
    elif tag == "replace":
        # Lines j1..j2 in new_lines replaced old lines i1..i2
        pass
    elif tag == "delete":
        # Lines i1..i2 from old_lines were deleted
        pass
```

### Generating Unified Diff Output
```python
# Source: Python 3.12 stdlib difflib documentation
import difflib

diff = difflib.unified_diff(
    old_content.splitlines(keepends=True),
    new_content.splitlines(keepends=True),
    fromfile=f"a/{path.name}",
    tofile=f"b/{path.name}",
    n=3,  # context lines
)
diff_text = "".join(diff)
```

### Extending on_file_system_changed for Buffer Reload
```python
# Source: Existing pattern in nano_claude/app.py
def on_file_system_changed(self, event: FileSystemChanged) -> None:
    """Handle filesystem changes -- refresh tree AND reload/diff open buffers."""
    from watchfiles import Change

    # Existing: refresh file tree
    try:
        file_tree = self.query_one(FileTreePanel)
        self.run_worker(file_tree.reload_preserving_state(), name="tree-reload")
    except Exception:
        pass

    # NEW: process file changes for editor
    modified_paths: list[Path] = []
    for change_type, path_str in event.changes:
        if change_type in (Change.modified, Change.added):
            path = Path(path_str)
            if path.is_file():
                modified_paths.append(path)

    if modified_paths:
        self._handle_file_changes(modified_paths)
```

### Using App.notify with Markup
```python
# Source: Textual 8.1.1 App.notify documentation + action link markup
# Textual supports @click action links in notify markup
self.notify(
    f"Claude edited [bold]{name}[/bold]  |  Ctrl+J to jump",
    title="File Changed",
    severity="information",
    timeout=8,
)
```

### Reusable _apply_style_to_range for Full-Line Tinting
```python
# Source: Existing SearchableTextArea._apply_style_to_range
# Apply a background tint to an entire line in render_line:
strip = self._apply_style_to_range(strip, 0, strip.cell_length, _ADDED_LINE_STYLE)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Parse Claude output for tool names | Filesystem watcher catches ALL edits | Phase 2 (already done) | No need for PTY parsing to detect file edits; watcher is the single source of truth |
| watchdog for filesystem watching | watchfiles (Rust-backed) | Already in use since Phase 2 | Better performance, simpler API, works with asyncio natively |
| Custom popup notifications | Textual App.notify() with Rich markup | Textual 0.30+ | Built-in toast system with timeouts, severity, and markup support |
| ModalScreen with manual compose | Established UnsavedChangesScreen pattern | Phase 2 | Reusable pattern for conflict resolution dialogs |

**Deprecated/outdated:**
- watchdog library: While still popular, this project already uses watchfiles which is faster and has native asyncio support. Do NOT add watchdog.
- PTY output parsing for file detection: The PITFALLS.md research explicitly warns against this. Use filesystem watcher as primary source.

## Open Questions

1. **Snapshot for un-opened files**
   - What we know: For files already open in BufferManager, `FileBuffer.original_content` serves as the "before" snapshot. For files not open, we have no pre-existing content.
   - What's unclear: Should we proactively snapshot all project files (expensive), or accept that diffs are only available for files that were open before Claude edited them?
   - Recommendation: Accept the limitation. When `ChangeTracker` gets a change event for an un-opened file, read the file (it's already the "new" version). The user can see the file but won't get line-level highlights. This is fine -- the primary value is for files the user is actively working in alongside Claude.

2. **Multiple simultaneous changes UI**
   - What we know: User wants a list of changed files when Claude edits multiple. Textual has `OptionList` and `ModalScreen` for selection UIs.
   - What's unclear: Should this be a persistent sidebar element, a transient overlay, or a modal?
   - Recommendation: Use a transient overlay (like the search overlay pattern) docked to the top of the editor panel. Shows file names as a selectable list. Dismissed after selection or Escape. Non-modal so user can still see the editor.

3. **Large diff handling**
   - What we know: `difflib.unified_diff` generates full output. Very large diffs (> 1000 lines) could be slow to render.
   - What's unclear: What is the practical upper bound of diffs users will encounter?
   - Recommendation: For the DiffView widget, use a scrollable Static (already overflow-y: auto). If diff exceeds 5000 lines, truncate with a "... (truncated, showing first 5000 lines)" message. This handles the rare edge case without over-engineering.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio (auto mode) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `.venv/bin/python -m pytest tests/ -x -q` |
| Full suite command | `.venv/bin/python -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CHNG-01a | ChangeTracker computes added/modified/deleted lines from before/after content | unit | `.venv/bin/python -m pytest tests/test_change_tracker.py -x` | No - Wave 0 |
| CHNG-01b | FileSystemChanged triggers change notification with correct file name | unit | `.venv/bin/python -m pytest tests/test_change_detection.py::test_notification_on_change -x` | No - Wave 0 |
| CHNG-01c | Change highlights (green added, yellow modified) render on correct lines | unit | `.venv/bin/python -m pytest tests/test_change_detection.py::test_change_highlights -x` | No - Wave 0 |
| CHNG-01d | Ctrl+J jumps editor to the most recently changed file | integration | `.venv/bin/python -m pytest tests/test_change_detection.py::test_jump_to_change -x` | No - Wave 0 |
| CHNG-02a | Unified diff is generated correctly from before/after snapshots | unit | `.venv/bin/python -m pytest tests/test_change_tracker.py::test_unified_diff -x` | No - Wave 0 |
| CHNG-02b | Ctrl+D toggles diff view on/off without losing editor state | integration | `.venv/bin/python -m pytest tests/test_change_detection.py::test_diff_toggle -x` | No - Wave 0 |
| CHNG-03a | External file change triggers auto-reload of open buffer | unit | `.venv/bin/python -m pytest tests/test_change_detection.py::test_auto_reload -x` | No - Wave 0 |
| CHNG-03b | Unsaved edits + external change shows conflict prompt | integration | `.venv/bin/python -m pytest tests/test_change_detection.py::test_conflict_prompt -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/python -m pytest tests/ -x -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_change_tracker.py` -- covers CHNG-01a, CHNG-02a (ChangeTracker unit tests)
- [ ] `tests/test_change_detection.py` -- covers CHNG-01b, CHNG-01c, CHNG-01d, CHNG-02b, CHNG-03a, CHNG-03b (integration tests)

## Keybinding Recommendations

| Action | Recommended Key | Rationale |
|--------|----------------|-----------|
| Jump to changed file | **Ctrl+J** | Completely unused in codebase and TextArea defaults. Ctrl+G conflicts with search overlay "next match". Ctrl+J is mnemonic for "Jump". |
| Toggle diff view | **Ctrl+D** | Overrides TextArea's delete_right (Delete key still works). Ctrl+D is standard for "diff" in many tools. Must use `priority=True` at App level. |
| Dismiss changed-files overlay | **Escape** | Consistent with search overlay dismissal pattern. |

These bindings must be added to `RESERVED_KEYS` in `terminal/widget.py` so the PTY does not capture them.

## Sources

### Primary (HIGH confidence)
- Python 3.12 `difflib` documentation -- SequenceMatcher.get_opcodes(), unified_diff()
- Existing codebase: `nano_claude/services/file_watcher.py` -- FileWatcherService, FileSystemChanged, awatch with 800ms debounce
- Existing codebase: `nano_claude/widgets/searchable_text_area.py` -- render_line override, _apply_style_to_range, Strip crop/join pattern
- Existing codebase: `nano_claude/models/file_buffer.py` -- BufferManager, FileBuffer with original_content/current_content
- Existing codebase: `nano_claude/app.py` -- on_file_system_changed handler, notify() usage, Binding pattern
- Textual 8.1.1 App.notify signature -- supports Rich markup with `@click` action links

### Secondary (MEDIUM confidence)
- [Textual content markup documentation](https://textual.textualize.io/guide/content/) -- @click action links in markup
- [Textual actions guide](https://textual.textualize.io/guide/actions/) -- action link syntax
- [Textual Toast widget](https://textual.textualize.io/widgets/toast/) -- notification rendering details
- `.planning/research/PITFALLS.md` -- Pitfall 4 warns against parsing output for file detection, recommends filesystem watcher as primary

### Tertiary (LOW confidence)
- None -- all findings verified against installed packages and existing code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all stdlib or already installed; verified against actual installed versions
- Architecture: HIGH -- extends existing patterns (render_line, on_file_system_changed, BufferManager); all integration points verified in codebase
- Pitfalls: HIGH -- binding conflicts verified by inspecting TextArea.BINDINGS and search_overlay.py; race condition identified from watchfiles 800ms debounce timing; event storm pattern documented in PITFALLS.md

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable -- stdlib difflib, existing codebase patterns)
