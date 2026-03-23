# Phase 4: Change Detection and Auto-Jump - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Detect when Claude edits files via the PTY and automatically navigate the editor to those changes. Show change highlights on modified lines. Provide a toggleable unified diff view. Auto-reload open files when they change on disk from external tools (git, other editors). This is the killer feature — the reason nano-claude exists over tmux+editor+Claude.

</domain>

<decisions>
## Implementation Decisions

### Auto-Jump Behavior
- When Claude edits a file: show a notification first, NOT instant jump — "Claude edited foo.py" toast + status bar message with "Ctrl+G to jump"
- If user is actively editing another file: notification only, don't steal focus — let user jump when ready
- If Claude edits multiple files in one response: show a list of all changed files so user can pick which to open
- Detection source: filesystem watcher (already exists from Phase 2) catches all edits regardless of how Claude makes them (Write, Edit, Bash sed, etc.)

### Change Highlights
- Changed lines get a tinted background color (green for added, yellow for modified) — more visible than gutter markers alone
- Highlights persist until the user starts editing the file OR Claude makes new changes — then previous highlights clear
- Highlight style reuses the SearchableTextArea render_line override pattern from Phase 2

### Diff View
- Unified inline diff (green/red lines like `git diff`) — toggled with Ctrl+D
- Replaces the normal editor view temporarily while active; toggle again to return to normal editing
- Compares: version before Claude's edit (snapshot) vs current file on disk (after Claude saved)
- Need to capture a "before" snapshot of files before Claude edits them — snapshot on first filesystem change detection per file
- Diff view is read-only — can't edit while viewing the diff

### Auto-Reload
- When an open file changes on disk (git checkout, external tool): silent auto-reload without asking — seamless
- EXCEPTION: if the file has unsaved edits AND it changed on disk, prompt the user: "foo.py changed on disk but has unsaved edits. Reload (lose edits) or keep?"
- Uses the existing FileWatcherService from Phase 2 — extend its handler to also reload open editor buffers

### Claude's Discretion
- Exact shortcut for "jump to changed file" (suggested Ctrl+G)
- How the changed-files list UI looks (overlay, sidebar, or notification stack)
- Snapshot storage strategy (in-memory dict of path → content)
- How to handle very large diffs (scrolling, truncation)
- Diff view color scheme (green/red intensity, background vs foreground)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing File Watcher
- `nano_claude/services/file_watcher.py` — FileWatcherService with watchfiles awatch(), FileSystemChanged message
- `nano_claude/app.py` — on_file_system_changed handler (sole owner), tree reload coordination

### Editor Infrastructure
- `nano_claude/panels/editor.py` — EditorPanel with open_file(), BufferManager, SearchableTextArea
- `nano_claude/widgets/searchable_text_area.py` — render_line override pattern for highlighting (reusable for change highlights)
- `nano_claude/models/file_buffer.py` — FileBuffer, BufferManager, detect_language

### PTY Integration
- `nano_claude/terminal/widget.py` — TerminalWidget, PtyDataReceived message (can be used to detect Claude's file edits)
- `nano_claude/terminal/status_parser.py` — StatusParser pattern for parsing PTY output

### Requirements
- `.planning/REQUIREMENTS.md` — CHNG-01, CHNG-02, CHNG-03
- `.planning/research/PITFALLS.md` — Dual detection strategy concerns, FSEvents latency on macOS

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FileWatcherService` — Already watches cwd for changes with 800ms debounce, posts FileSystemChanged
- `SearchableTextArea.render_line()` — Override pattern for applying custom styles to specific line ranges (used for search highlights, reusable for change highlights)
- `BufferManager` — Tracks open file buffers with content, cursor position, and modified state
- `StatusParser` — Pattern for extracting structured info from PTY output

### Established Patterns
- App-level message handlers coordinate between panels (on_file_system_changed, on_text_area_changed)
- Textual toast notifications via `self.notify()`
- All bindings use `Binding(key, action, id=..., priority=True)` pattern

### Integration Points
- `FileWatcherService` → needs to also trigger editor buffer reloads (currently only refreshes tree)
- `on_file_system_changed` in app.py → needs to diff changed files against snapshots, show notifications, update editor highlights
- `EditorPanel` → needs new methods: apply_change_highlights(), show_diff_view(), reload_if_changed()
- `SearchableTextArea` → extend render_line to support change highlights alongside search highlights

</code_context>

<specifics>
## Specific Ideas

- The auto-jump notification should feel like VS Code's "file changed on disk" toast — brief, actionable, not blocking
- Change highlights should be subtle enough to not interfere with syntax highlighting but visible enough to spot at a glance
- Diff view should feel like running `git diff` inline — familiar to any developer
- The "before" snapshot is the key enabler — without it, we can only detect THAT something changed, not WHAT changed

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-change-detection-and-auto-jump*
*Context gathered: 2026-03-23*
