# Technology Stack

**Project:** nano-claude (Terminal-native IDE with embedded Claude Code)
**Researched:** 2026-03-22

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Textual | 8.1.1 | TUI application framework | The only serious choice for a modern Python TUI. 120 FPS renders via Rich segment trees, CSS-like styling, built-in widget library (DirectoryTree, TextArea, Input, Log), asyncio-native, responsive layouts, keymaps system, theming. Nothing else comes close for this use case. | HIGH |
| Rich | 14.3.3 | Terminal rendering engine (Textual dependency) | Textual's rendering backend. Provides syntax highlighting via Pygments, 16.7M color support, styled text, layout primitives. Installed automatically with Textual. | HIGH |

### Claude Code Integration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| claude-agent-sdk | 0.1.50 | Claude Code subprocess management | Official Python SDK from Anthropic. Provides `ClaudeSDKClient` for multi-turn interactive conversations, streaming via `StreamEvent` objects, typed message classes (`AssistantMessage`, `ToolUseBlock`), interrupt support, session resume, and in-process custom tools via `@tool` decorator. Replaces the deprecated `claude-code-sdk`. Manages the CLI subprocess internally -- no manual PTY/stdin/stdout management needed for the chat panel. | HIGH |

### Syntax Highlighting & Parsing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| tree-sitter (py-tree-sitter) | 0.25.2 | Incremental parsing for syntax highlighting | Textual's TextArea uses tree-sitter natively. Incremental parsing means only changed regions are re-parsed -- critical for a code editor. Industry standard (used by Neovim, Helix, Zed). | HIGH |
| tree-sitter-language-pack | 1.0.0 | Pre-compiled grammars for 170+ languages | Actively maintained successor to the abandoned tree-sitter-languages. Pre-compiled wheels, no compilation step needed. Covers every language a developer would encounter. | HIGH |

### Subprocess & Terminal Emulation (for terminal panel only)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| ptyprocess | 0.7.0 | PTY subprocess management for shell panel | Launches user's shell ($SHELL) in a pseudo-terminal for the toggleable terminal panel. Lightweight, stable, production-grade. Used internally by pexpect. NOT needed for Claude -- the SDK handles that. | MEDIUM |
| pyte | 0.8.2 | In-memory VT100 terminal emulator | Parses VT100/ANSI escape sequences from the shell PTY into a screen buffer that Textual can render. Only needed for the terminal panel, not for Claude chat. | MEDIUM |
| asyncio (stdlib) | 3.12+ | Async event loop | Textual is asyncio-native. SDK streaming, file watching, and UI updates all need non-blocking coordination. stdlib -- no extra dependency. | HIGH |

### File System Monitoring

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| watchfiles | 1.1.1 | Detect file changes from Claude Code edits | Rust-based (Notify library), async-native (`awatch`), debounced, cross-platform. Acts as safety net alongside SDK tool-use detection. Catches edits from external tools (git, scripts) that the SDK can't see. | HIGH |

### CLI Entry Point

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| click | 8.1.x | CLI argument parsing and entry point | Battle-tested, minimal, composable. Textual apps need a thin CLI wrapper for flags like `--project-dir`, `--theme`. Click is lighter than typer and has no runtime dependency on Rich (avoiding version conflicts with Textual's Rich). | MEDIUM |

### Project Management & Build

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| uv | 0.10.x | Package/project management | 10-100x faster than pip. Handles virtualenvs, lockfiles, Python version management, and pyproject.toml-based builds. The standard for new Python projects in 2025/2026. | HIGH |
| hatchling | latest | Build backend | Lightweight PEP 517 build backend. Works well with uv and pyproject.toml. Simpler than setuptools for pure-Python packages. | MEDIUM |

### Testing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pytest | 8.x | Test framework | Standard Python testing. | HIGH |
| pytest-asyncio | 0.24.x | Async test support | Required for testing Textual apps (all Textual tests are async). | HIGH |
| pytest-textual-snapshot | latest | Visual regression testing | Official Textual snapshot testing. Renders app headless, captures output, compares against saved snapshots. Critical for catching UI regressions. | HIGH |

### Development Tools

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| textual-dev | latest | Textual dev console & live reload | Connects a dev console from a separate terminal showing events, logs, and print statements. Essential for debugging TUI apps where stdout is occupied by the UI. | HIGH |
| ruff | latest | Linter and formatter | Rust-based, replaces flake8+black+isort. Fast, opinionated, zero-config for most projects. | HIGH |
| mypy | latest | Type checking | Static type analysis. Textual uses extensive typing; mypy catches widget composition errors early. | MEDIUM |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| TUI Framework | Textual 8.1.1 | urwid | Legacy API, OOMs at 5k widgets, no CSS styling, no built-in tree-sitter TextArea, no DirectoryTree. Textual outperforms it in every dimension relevant to this project. |
| TUI Framework | Textual 8.1.1 | prompt_toolkit | Optimized for command-line input (autocomplete, multi-line editing), not full-screen app layouts. No layout engine, no widget system, no file tree. |
| TUI Framework | Textual 8.1.1 | curses (stdlib) | Raw terminal primitives. 20 FPS vs Textual's 120 FPS. No widgets, no CSS, no async. Would require building everything from scratch. |
| Claude Integration | claude-agent-sdk | Raw subprocess (claude -p --output-format stream-json) | Manual subprocess lifecycle management, no typed message objects, no session management, no interrupt support, no multi-turn context. The SDK wraps all of this. |
| Claude Integration | claude-agent-sdk | claude-code-sdk | Deprecated. Replaced by claude-agent-sdk. Do not use. |
| Claude Integration | claude-agent-sdk | Direct Anthropic API | Loses ALL Claude Code features: tools (Edit, Write, Bash, Read, Glob, Grep), hooks, MCP servers, CLAUDE.md, permission system, extended thinking. Would require reimplementing years of work. |
| Syntax Highlighting | tree-sitter | Pygments (via Rich) | Pygments re-highlights entire files on every change. tree-sitter is incremental -- only re-parses changed regions. For a code editor with live updates, this difference is critical. Pygments is fine for one-shot rendering but not for editing. |
| Language Grammars | tree-sitter-language-pack | tree-sitter-languages | Unmaintained. Does not support Python 3.13+. tree-sitter-language-pack is the actively maintained fork with 170+ languages. |
| File Watching | watchfiles | watchdog | watchdog uses threads (not asyncio-native), has OS-specific backends with different behaviors, and known debouncing bugs. watchfiles is Rust-based, async-native, simpler API. |
| PTY Management | ptyprocess | pexpect | pexpect adds pattern-matching/expect logic on top of ptyprocess. We don't need expect-style matching -- we need raw PTY read/write. ptyprocess is the lower-level building block. |
| Terminal Emulation | pyte + custom | textual-terminal | textual-terminal wraps pyte but is unmaintained (1 contributor, 7 open issues), LGPL-3 licensed, and described as "extremely slow" by the Textual maintainer. Build a custom widget using pyte directly for better performance and control. |
| Terminal Panel | pyte + PTY | RichLog + Input | Will McGugan recommends this simpler approach for most use cases. However, it cannot handle interactive programs (vim, htop, ssh). For a terminal panel in an IDE, users will expect full interactivity. Start with RichLog+Input as a fallback if PTY proves too complex. |
| CLI Parser | click | typer | Typer depends on Rich, risking version conflicts with Textual's Rich dependency. Click has zero conflicts and is already a transitive dependency of many tools. |
| CLI Parser | click | argparse (stdlib) | Works but verbose for nested commands. Click provides better help formatting and composability with less code. |
| Build Tool | uv | pip + venv | Dramatically slower (10-100x). No lockfile. No Python version management. uv is the modern standard. |
| Build Tool | uv | poetry | Poetry is slower, has its own lockfile format (not PEP 621 pyproject.toml native), and the resolver has known edge cases. uv is faster and standards-compliant. |

## Claude Code Integration Strategy

This is the most architecturally critical decision. The `claude-agent-sdk` provides two integration modes:

### Primary: ClaudeSDKClient (Multi-Turn Interactive)

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

client = ClaudeSDKClient(options=ClaudeAgentOptions(
    cwd="/path/to/project",
    allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
))
await client.connect()

# Send a message and stream responses
await client.query("Refactor the auth module")
async for message in client.receive_response():
    if isinstance(message, StreamEvent):
        # Real-time text deltas for chat display
        ...
    elif isinstance(message, AssistantMessage):
        # Complete turn with tool_use blocks for file edit detection
        for block in message.content:
            if isinstance(block, ToolUseBlock) and block.name in ("Edit", "Write"):
                # Trigger auto-jump to edited file
                ...
    elif isinstance(message, ResultMessage):
        # Session complete, extract cost/usage
        ...
```

**Advantages:**
- Multi-turn conversations with maintained context
- Streaming `StreamEvent` objects for real-time chat rendering
- Typed `ToolUseBlock` objects for detecting file edits (auto-jump feature)
- Built-in session resume and interrupt support
- In-process custom tools via `@tool` decorator (future extensibility)
- Manages subprocess lifecycle internally

### Terminal Panel: PTY + pyte (for arbitrary shell commands)

```python
import ptyprocess
import pyte

# For the toggleable terminal panel only
process = ptyprocess.PtyProcess.spawn(["/bin/zsh"])
screen = pyte.Screen(80, 24)
stream = pyte.Stream(screen)

# Read output and feed to pyte
data = process.read()
stream.feed(data)

# Render screen buffer in Textual widget
for line in screen.display:
    ...
```

**Recommendation:** Use `claude-agent-sdk` `ClaudeSDKClient` for the Claude chat panel. Use PTY + pyte only for the toggleable terminal panel where users run arbitrary shell commands. This gives structured data where we need it (chat) and full terminal emulation where we need it (shell).

## Python Version

**Target: Python 3.12+**

- claude-agent-sdk requires >= 3.10
- tree-sitter and tree-sitter-language-pack require >= 3.10
- Textual supports 3.9-3.14, but 3.12+ provides significant performance improvements (PEP 709 inlined comprehensions, PEP 684 per-interpreter GIL)
- f-string improvements in 3.12 (arbitrary expressions)
- 3.12 is the sweet spot: modern enough for all dependencies, old enough for wide availability

## Installation

```bash
# Project setup with uv
uv init nano-claude
cd nano-claude

# Core dependencies
uv add textual "textual[syntax]" claude-agent-sdk click watchfiles ptyprocess pyte

# The [syntax] extra installs tree-sitter and tree-sitter-language-pack
# If not bundled in textual[syntax], install explicitly:
uv add tree-sitter tree-sitter-language-pack

# Dev dependencies
uv add --dev textual-dev pytest pytest-asyncio pytest-textual-snapshot ruff mypy

# Run the app
uv run nano-claude
```

## pyproject.toml Skeleton

```toml
[project]
name = "nano-claude"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "textual>=8.1,<9",
    "claude-agent-sdk>=0.1.50",
    "click>=8.1,<9",
    "watchfiles>=1.1,<2",
    "ptyprocess>=0.7",
    "pyte>=0.8",
    "tree-sitter>=0.25",
    "tree-sitter-language-pack>=1.0",
]

[project.scripts]
nano-claude = "nano_claude.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.mypy]
python_version = "3.12"
strict = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

## Sources

- Textual 8.1.1: https://pypi.org/project/textual/ (verified PyPI, March 2026)
- Textual docs - TextArea: https://textual.textualize.io/widgets/text_area/
- Textual docs - DirectoryTree: https://textual.textualize.io/widgets/directory_tree/
- Textual docs - Testing: https://textual.textualize.io/guide/testing/
- Textual docs - Layout: https://textual.textualize.io/guide/layout/
- Textual docs - Keymaps: https://darren.codes/posts/textual-keymaps/
- Textual docs - Themes: https://textual.textualize.io/guide/design/
- Rich 14.3.3: https://pypi.org/project/rich/
- claude-agent-sdk 0.1.50: https://pypi.org/project/claude-agent-sdk/ (verified PyPI, March 2026)
- Claude Agent SDK Python reference: https://platform.claude.com/docs/en/agent-sdk/python
- Claude Agent SDK overview: https://platform.claude.com/docs/en/agent-sdk/overview
- tree-sitter 0.25.2: https://pypi.org/project/tree-sitter/ (verified PyPI)
- tree-sitter-language-pack 1.0.0: https://pypi.org/project/tree-sitter-language-pack/ (verified PyPI, March 2026)
- watchfiles 1.1.1: https://pypi.org/project/watchfiles/ (verified PyPI)
- pyte 0.8.2: https://pypi.org/project/pyte/ (verified PyPI)
- ptyprocess 0.7.0: https://github.com/pexpect/ptyprocess
- Claude Code CLI reference: https://code.claude.com/docs/en/cli-reference
- uv: https://docs.astral.sh/uv/
- Textual terminal widget discussion: https://github.com/Textualize/textual/discussions/5461
- textual-terminal (rejected): https://github.com/mitosch/textual-terminal
