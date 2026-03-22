"""File tree panel with filtered directory browsing."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from textual.reactive import reactive
from textual.widgets import DirectoryTree

from nano_claude.config.settings import HIDDEN_PATTERNS
from nano_claude.panels.base import BasePanel


class FilteredDirectoryTree(DirectoryTree):
    """DirectoryTree that filters hidden files/directories by default.

    Hidden patterns (defined in HIDDEN_PATTERNS) and dotfiles (names starting
    with '.') are excluded unless show_hidden is True.

    Paths are sorted with directories first, then files, alphabetically
    (case-insensitive) within each group.
    """

    show_hidden: reactive[bool] = reactive(False)

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        """Filter and sort directory entries.

        When show_hidden is False:
        - Exclude paths whose name starts with '.'
        - Exclude paths whose name matches HIDDEN_PATTERNS

        Always sort: directories first, then files, alphabetical within each group.
        """
        path_list = list(paths)

        if not self.show_hidden:
            path_list = [
                p for p in path_list
                if not p.name.startswith(".") and p.name not in HIDDEN_PATTERNS
            ]

        # Sort: directories first, then alphabetical (case-insensitive)
        path_list.sort(key=lambda p: (not p.is_dir(), p.name.lower()))
        return path_list

    def watch_show_hidden(self, value: bool) -> None:
        """Reload tree when hidden file visibility changes."""
        try:
            self.reload()
        except Exception:
            # Widget not yet mounted -- reload will happen on mount
            pass


class FileTreePanel(BasePanel):
    """Left panel: file tree browser with filtered directory navigation."""

    def compose(self):
        self.panel_title = "Files"
        yield FilteredDirectoryTree(Path.cwd(), id="directory-tree")

    def on_mount(self) -> None:
        """Expand the root node one level deep on startup."""
        tree = self.query_one(FilteredDirectoryTree)
        tree.root.expand()

    def action_toggle_hidden(self) -> None:
        """Toggle visibility of hidden files in the directory tree."""
        tree = self.query_one(FilteredDirectoryTree)
        tree.show_hidden = not tree.show_hidden
