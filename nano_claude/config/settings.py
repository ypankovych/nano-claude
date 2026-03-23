"""Layout defaults and configuration constants."""

from __future__ import annotations

# Layout defaults (fr units, approximating 15% / 50% / 35%)
DEFAULT_TREE_WIDTH = 1.0  # 1.0 / 6.6 total = ~15%
DEFAULT_EDITOR_WIDTH = 3.3  # 3.3 / 6.6 total = ~50%
DEFAULT_CHAT_WIDTH = 2.3  # 2.3 / 6.6 total = ~35%

# Minimum widths in character columns before collapse
MIN_PANEL_WIDTH = 15
MIN_EDITOR_WIDTH = 20

# Collapse thresholds (terminal width in columns)
COLLAPSE_TREE_THRESHOLD = 60  # Hide file tree below this
COLLAPSE_CHAT_THRESHOLD = 40  # Hide chat below this, editor only

# Welcome greeting shown when no README.md exists in project root
WELCOME_GREETING = """\
Welcome to nano-claude!

Quick Start:
  Ctrl+b  Focus file tree
  Ctrl+e  Focus editor
  Ctrl+r  Focus chat
  Tab     Cycle panels
  Ctrl+=  Grow panel
  Ctrl+-  Shrink panel
  Ctrl+\\  Toggle file tree
  Ctrl+q  Quit

Open a project directory to get started."""

# Hidden file/directory patterns -- filtered from DirectoryTree by default.
# Dotfiles (names starting with ".") are also hidden independently.
# Toggled via Ctrl+H.
HIDDEN_PATTERNS: frozenset[str] = frozenset({
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".DS_Store",
    ".idea",
    ".vscode",
    ".eggs",
    "*.egg-info",
})

# Map file extensions to TextArea language names for syntax highlighting.
EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "javascript",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".json": "json",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".md": "markdown",
    ".markdown": "markdown",
    ".sql": "sql",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".xml": "xml",
    ".svg": "xml",
    ".regex": "regex",
}

# Large file threshold -- warn user before opening files larger than this.
# Per research Pitfall 3: tree-sitter can have quadratic scaling above ~2000 lines.
MAX_FILE_SIZE_BYTES: int = 1_048_576  # 1 MB

# ---------------------------------------------------------------------------
# Claude Code integration
# ---------------------------------------------------------------------------

CLAUDE_NOT_FOUND_MESSAGE = """\
Claude Code not found

Install Claude Code CLI:
  npm install -g @anthropic-ai/claude-code

The editor and file tree still work without Claude.
Visit https://docs.anthropic.com/en/docs/claude-code for details."""

CLAUDE_EXITED_MESSAGE = """\
Claude Code has exited (code: {exit_code}).

Press Ctrl+Shift+R to restart Claude."""

CLAUDE_RESTART_KEY = "ctrl+shift+r"

# Claude status display
CLAUDE_STATUS_SEPARATOR = " | "

# ---------------------------------------------------------------------------
# Terminal panel
# ---------------------------------------------------------------------------

TERMINAL_PANEL_HEIGHT = "30%"  # Fixed height when expanded
TERMINAL_MIN_HEIGHT = 8        # Minimum rows to display
TERMINAL_MAX_TABS = 8          # Maximum concurrent shell sessions

SHELL_EXITED_MESSAGE = """\
Shell exited (code: {exit_code}).

Press Ctrl+T to reopen or Ctrl+N for a new tab."""

TERMINAL_STATUS_IDLE = " Terminal (idle) | Ctrl+T to open "
TERMINAL_STATUS_RUNNING = " Terminal ({count} tab{s}) | Ctrl+T to focus "
