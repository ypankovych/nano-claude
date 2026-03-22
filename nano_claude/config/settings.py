"""Layout defaults and configuration constants."""

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
