"""Tests for file tree panel and configuration constants."""

from pathlib import Path

from nano_claude.app import NanoClaudeApp
from nano_claude.config.settings import (
    EXTENSION_TO_LANGUAGE,
    HIDDEN_PATTERNS,
    MAX_FILE_SIZE_BYTES,
)
from nano_claude.panels.file_tree import FilteredDirectoryTree, FileTreePanel


class TestHiddenPatterns:
    """Test that HIDDEN_PATTERNS contains expected entries."""

    def test_hidden_patterns_contains_git(self):
        assert ".git" in HIDDEN_PATTERNS

    def test_hidden_patterns_contains_node_modules(self):
        assert "node_modules" in HIDDEN_PATTERNS

    def test_hidden_patterns_contains_pycache(self):
        assert "__pycache__" in HIDDEN_PATTERNS

    def test_hidden_patterns_contains_venv(self):
        assert ".venv" in HIDDEN_PATTERNS

    def test_hidden_patterns_is_frozenset(self):
        assert isinstance(HIDDEN_PATTERNS, frozenset)


class TestExtensionToLanguage:
    """Test that EXTENSION_TO_LANGUAGE maps extensions correctly."""

    def test_python_extension(self):
        assert EXTENSION_TO_LANGUAGE[".py"] == "python"

    def test_javascript_extension(self):
        assert EXTENSION_TO_LANGUAGE[".js"] == "javascript"

    def test_rust_extension(self):
        assert EXTENSION_TO_LANGUAGE[".rs"] == "rust"

    def test_json_extension(self):
        assert EXTENSION_TO_LANGUAGE[".json"] == "json"

    def test_toml_extension(self):
        assert EXTENSION_TO_LANGUAGE[".toml"] == "toml"

    def test_yaml_extension(self):
        assert EXTENSION_TO_LANGUAGE[".yaml"] == "yaml"

    def test_is_dict(self):
        assert isinstance(EXTENSION_TO_LANGUAGE, dict)


class TestMaxFileSize:
    """Test MAX_FILE_SIZE_BYTES constant."""

    def test_exists_and_is_positive_int(self):
        assert isinstance(MAX_FILE_SIZE_BYTES, int)
        assert MAX_FILE_SIZE_BYTES > 0

    def test_is_one_megabyte(self):
        assert MAX_FILE_SIZE_BYTES == 1_048_576


# ---------------------------------------------------------------------------
# FilteredDirectoryTree unit tests
# ---------------------------------------------------------------------------


class TestFilteredDirectoryTreeFilterPaths:
    """Test filter_paths method of FilteredDirectoryTree."""

    def _make_tree(self, tmp_path: Path) -> FilteredDirectoryTree:
        """Create a FilteredDirectoryTree instance rooted at tmp_path."""
        return FilteredDirectoryTree(tmp_path, id="test-tree")

    def test_hidden_files_filtered_when_show_hidden_false(self, tmp_path: Path):
        """Hidden patterns like .git and node_modules are excluded."""
        (tmp_path / ".git").mkdir()
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / "README.md").touch()

        tree = self._make_tree(tmp_path)
        tree.show_hidden = False

        paths = [tmp_path / n for n in [".git", "node_modules", "__pycache__", "src", "README.md"]]
        result = list(tree.filter_paths(paths))

        result_names = [p.name for p in result]
        assert ".git" not in result_names
        assert "node_modules" not in result_names
        assert "__pycache__" not in result_names
        assert "src" in result_names
        assert "README.md" in result_names

    def test_dotfiles_filtered_when_show_hidden_false(self, tmp_path: Path):
        """Files starting with '.' are excluded when show_hidden=False."""
        (tmp_path / ".gitignore").touch()
        (tmp_path / ".env").touch()
        (tmp_path / "main.py").touch()

        tree = self._make_tree(tmp_path)
        tree.show_hidden = False

        paths = [tmp_path / n for n in [".gitignore", ".env", "main.py"]]
        result = list(tree.filter_paths(paths))

        result_names = [p.name for p in result]
        assert ".gitignore" not in result_names
        assert ".env" not in result_names
        assert "main.py" in result_names

    def test_show_hidden_true_returns_all(self, tmp_path: Path):
        """When show_hidden=True, all paths are returned."""
        (tmp_path / ".git").mkdir()
        (tmp_path / "node_modules").mkdir()
        (tmp_path / ".env").touch()
        (tmp_path / "src").mkdir()

        tree = self._make_tree(tmp_path)
        tree.show_hidden = True

        paths = [tmp_path / n for n in [".git", "node_modules", ".env", "src"]]
        result = list(tree.filter_paths(paths))

        assert len(result) == 4

    def test_sort_order_directories_before_files(self, tmp_path: Path):
        """Directories appear before files in filter_paths output."""
        (tmp_path / "zebra.txt").touch()
        (tmp_path / "alpha_dir").mkdir()
        (tmp_path / "beta.py").touch()
        (tmp_path / "gamma_dir").mkdir()

        tree = self._make_tree(tmp_path)
        tree.show_hidden = False

        paths = [
            tmp_path / "zebra.txt",
            tmp_path / "alpha_dir",
            tmp_path / "beta.py",
            tmp_path / "gamma_dir",
        ]
        result = list(tree.filter_paths(paths))
        result_names = [p.name for p in result]

        # Directories should come first
        dir_indices = [result_names.index(n) for n in ["alpha_dir", "gamma_dir"]]
        file_indices = [result_names.index(n) for n in ["zebra.txt", "beta.py"]]
        assert max(dir_indices) < min(file_indices), (
            f"Directories should come before files: {result_names}"
        )

    def test_alphabetical_sort_within_group(self, tmp_path: Path):
        """Items are sorted alphabetically (case-insensitive) within dirs and files."""
        (tmp_path / "Zebra_dir").mkdir()
        (tmp_path / "alpha_dir").mkdir()
        (tmp_path / "Zfile.txt").touch()
        (tmp_path / "afile.txt").touch()

        tree = self._make_tree(tmp_path)
        tree.show_hidden = False

        paths = [
            tmp_path / "Zebra_dir",
            tmp_path / "alpha_dir",
            tmp_path / "Zfile.txt",
            tmp_path / "afile.txt",
        ]
        result = list(tree.filter_paths(paths))
        result_names = [p.name for p in result]

        # Dirs first, alphabetical: alpha_dir, Zebra_dir
        # Files next, alphabetical: afile.txt, Zfile.txt
        assert result_names == ["alpha_dir", "Zebra_dir", "afile.txt", "Zfile.txt"]


# ---------------------------------------------------------------------------
# Integration tests (require app mounting)
# ---------------------------------------------------------------------------


class TestFileTreePanelIntegration:
    """Integration tests for FileTreePanel in NanoClaudeApp."""

    async def test_directory_tree_renders_not_placeholder(self):
        """FileTreePanel composes a FilteredDirectoryTree, not a Static placeholder."""
        app = NanoClaudeApp()
        async with app.run_test(size=(120, 40)) as pilot:
            panel = app.query_one("#file-tree")
            trees = panel.query(FilteredDirectoryTree)
            assert len(trees) == 1, "Expected exactly one FilteredDirectoryTree"
            # Verify no placeholder remains
            from textual.widgets import Static
            statics = panel.query(Static)
            placeholder_ids = [s.id for s in statics if s.id and "placeholder" in s.id]
            assert len(placeholder_ids) == 0, "Old placeholder should not be present"

    async def test_tree_panel_title_is_files(self):
        """FileTreePanel has panel_title 'Files'."""
        app = NanoClaudeApp()
        async with app.run_test(size=(120, 40)) as pilot:
            panel = app.query_one("#file-tree", FileTreePanel)
            assert panel.panel_title == "Files"

    async def test_toggle_hidden_binding_exists(self):
        """App has a binding for toggling hidden files."""
        from textual.binding import Binding

        app = NanoClaudeApp()
        hidden_bindings = [
            b for b in app.BINDINGS
            if isinstance(b, Binding) and "toggle_hidden" in b.action
        ]
        assert len(hidden_bindings) >= 1, "Expected a toggle_hidden_files binding"
