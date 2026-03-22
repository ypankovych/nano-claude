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

    async def watch_show_hidden(self, value: bool) -> None:
        """Reload tree when hidden file visibility changes."""
        if self.is_mounted:
            await self.reload()


class FileTreePanel(BasePanel):
    """Left panel: file tree browser with filtered directory navigation."""

    def compose(self):
        self.panel_title = "Files"
        yield FilteredDirectoryTree(Path.cwd(), id="directory-tree")

    def on_tree_node_expanded(self, event) -> None:
        """Detect when the root node finishes its initial async load.

        DirectoryTree loads root contents asynchronously. We listen for the
        first root expansion event to know the tree is ready for interaction.
        """
        # Only care about root's first expansion (initial load)
        pass

    def action_toggle_hidden(self) -> None:
        """Toggle visibility of hidden files in the directory tree."""
        tree = self.query_one(FilteredDirectoryTree)
        tree.show_hidden = not tree.show_hidden

    async def reload_preserving_state(self) -> None:
        """Reload the directory tree while preserving expanded directories.

        Captures which directories are currently expanded, reloads the tree,
        then re-expands those directories. This ensures external changes
        (file add/remove) are reflected without collapsing user's view.
        """
        tree = self.query_one(FilteredDirectoryTree)

        # Capture expanded paths by walking tree nodes
        expanded_paths: set[Path] = set()

        def _collect_expanded(node) -> None:
            """Recursively collect paths of expanded tree nodes."""
            if node.is_expanded and node.data and hasattr(node.data, "path"):
                expanded_paths.add(node.data.path)
            elif node.is_expanded and hasattr(node, "data") and isinstance(node.data, Path):
                expanded_paths.add(node.data)
            for child in node.children:
                _collect_expanded(child)

        _collect_expanded(tree.root)

        # Reload the tree from disk
        await tree.reload()

        # Re-expand previously expanded directories
        def _restore_expanded(node) -> None:
            """Recursively re-expand nodes whose paths were previously expanded."""
            node_path = None
            if node.data and hasattr(node.data, "path"):
                node_path = node.data.path
            elif hasattr(node, "data") and isinstance(node.data, Path):
                node_path = node.data

            if node_path and node_path in expanded_paths:
                node.expand()

            for child in node.children:
                _restore_expanded(child)

        _restore_expanded(tree.root)
