"""File tree panel -- placeholder for Phase 2."""

from textual.widgets import Static

from nano_claude.panels.base import BasePanel


class FileTreePanel(BasePanel):
    """Left panel: file tree browser.

    Phase 2 will replace the placeholder with a DirectoryTree widget.
    """

    def compose(self):
        placeholder = Static(
            "File Tree\n\nPhase 2 will add DirectoryTree here.",
            id="file-tree-placeholder",
        )
        placeholder.can_focus = True
        yield placeholder
