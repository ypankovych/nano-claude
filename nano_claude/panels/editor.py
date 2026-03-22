"""Editor panel -- placeholder with README.md detection or welcome greeting."""

from pathlib import Path

from textual.widgets import Static

from nano_claude.config.settings import WELCOME_GREETING
from nano_claude.panels.base import BasePanel


class EditorPanel(BasePanel):
    """Center panel: code editor.

    On compose, checks if README.md exists in the current working directory.
    If yes, shows a reference to it. If no, shows a welcome greeting with shortcuts.
    Phase 2 will replace the placeholder with a TextArea editor widget.
    """

    def compose(self):
        readme_path = Path.cwd() / "README.md"
        if readme_path.exists():
            self.panel_title = "README.md"
            placeholder = Static(
                "README.md\n\n(Phase 2 will display file content here)",
                id="editor-placeholder",
            )
        else:
            self.panel_title = "Welcome"
            placeholder = Static(
                WELCOME_GREETING,
                id="editor-placeholder",
            )
        placeholder.can_focus = True
        yield placeholder
