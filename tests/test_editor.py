"""Tests for editor panel, file buffer model, and app-level editor wiring."""

from pathlib import Path

import pytest

from nano_claude.models.file_buffer import (
    BufferManager,
    FileBuffer,
    detect_indentation,
    detect_language,
)
from nano_claude.panels.editor import EditorPanel


# ---------------------------------------------------------------------------
# FileBuffer unit tests
# ---------------------------------------------------------------------------


class TestFileBuffer:
    """Test FileBuffer dataclass."""

    def test_is_modified_false_when_content_matches(self):
        """is_modified returns False when current_content equals original_content."""
        buf = FileBuffer(
            path=Path("/tmp/test.py"),
            original_content="hello",
            current_content="hello",
        )
        assert buf.is_modified is False

    def test_is_modified_true_when_content_differs(self):
        """is_modified returns True when current_content differs from original_content."""
        buf = FileBuffer(
            path=Path("/tmp/test.py"),
            original_content="hello",
            current_content="hello world",
        )
        assert buf.is_modified is True


# ---------------------------------------------------------------------------
# BufferManager unit tests
# ---------------------------------------------------------------------------


class TestBufferManager:
    """Test BufferManager for file open/save/tracking."""

    def test_open_file_reads_content(self, tmp_path: Path):
        """open_file reads file content and returns a FileBuffer."""
        test_file = tmp_path / "example.py"
        test_file.write_text("print('hello')", encoding="utf-8")

        mgr = BufferManager()
        buf = mgr.open_file(test_file)

        assert buf.path == test_file
        assert buf.original_content == "print('hello')"
        assert buf.current_content == "print('hello')"
        assert buf.is_modified is False

    def test_open_file_returns_cached_buffer(self, tmp_path: Path):
        """open_file returns cached buffer on second call for same path."""
        test_file = tmp_path / "example.py"
        test_file.write_text("content", encoding="utf-8")

        mgr = BufferManager()
        buf1 = mgr.open_file(test_file)
        buf1.current_content = "modified"
        buf2 = mgr.open_file(test_file)

        assert buf2 is buf1
        assert buf2.current_content == "modified"

    def test_save_file_writes_and_resets(self, tmp_path: Path):
        """save_file writes current_content to disk and resets is_modified."""
        test_file = tmp_path / "example.py"
        test_file.write_text("original", encoding="utf-8")

        mgr = BufferManager()
        buf = mgr.open_file(test_file)
        buf.current_content = "updated"
        assert buf.is_modified is True

        mgr.save_file(test_file)

        assert test_file.read_text(encoding="utf-8") == "updated"
        assert buf.is_modified is False

    def test_has_unsaved_changes_true(self, tmp_path: Path):
        """has_unsaved_changes returns True when any buffer is modified."""
        f1 = tmp_path / "a.py"
        f1.write_text("a", encoding="utf-8")
        f2 = tmp_path / "b.py"
        f2.write_text("b", encoding="utf-8")

        mgr = BufferManager()
        mgr.open_file(f1)
        buf2 = mgr.open_file(f2)
        buf2.current_content = "modified"

        assert mgr.has_unsaved_changes() is True

    def test_has_unsaved_changes_false(self, tmp_path: Path):
        """has_unsaved_changes returns False when no buffer is modified."""
        f1 = tmp_path / "a.py"
        f1.write_text("a", encoding="utf-8")

        mgr = BufferManager()
        mgr.open_file(f1)

        assert mgr.has_unsaved_changes() is False

    def test_get_unsaved_files(self, tmp_path: Path):
        """get_unsaved_files returns list of paths with unsaved changes."""
        f1 = tmp_path / "a.py"
        f1.write_text("a", encoding="utf-8")
        f2 = tmp_path / "b.py"
        f2.write_text("b", encoding="utf-8")

        mgr = BufferManager()
        mgr.open_file(f1)
        buf2 = mgr.open_file(f2)
        buf2.current_content = "modified"

        unsaved = mgr.get_unsaved_files()
        assert unsaved == [f2]

    def test_update_content(self, tmp_path: Path):
        """update_content updates current_content for a path's buffer."""
        f1 = tmp_path / "a.py"
        f1.write_text("original", encoding="utf-8")

        mgr = BufferManager()
        mgr.open_file(f1)
        mgr.update_content(f1, "new content")

        buf = mgr.open_file(f1)
        assert buf.current_content == "new content"
        assert buf.is_modified is True


# ---------------------------------------------------------------------------
# detect_indentation unit tests
# ---------------------------------------------------------------------------


class TestDetectIndentation:
    """Test detect_indentation helper."""

    def test_four_space_indentation(self):
        """Returns ('spaces', 4) for file with 4-space indentation."""
        content = "def foo():\n    return 1\n    if True:\n        pass\n"
        result = detect_indentation(content)
        assert result == ("spaces", 4)

    def test_tab_indentation(self):
        """Returns ('tabs', 4) for file with tab indentation."""
        content = "def foo():\n\treturn 1\n\tif True:\n\t\tpass\n"
        result = detect_indentation(content)
        assert result == ("tabs", 4)

    def test_two_space_indentation(self):
        """Returns ('spaces', 2) for file with 2-space indentation."""
        content = "function foo() {\n  return 1;\n  if (true) {\n    bar();\n  }\n}\n"
        result = detect_indentation(content)
        assert result == ("spaces", 2)

    def test_empty_content_returns_default(self):
        """Returns default ('spaces', 4) for empty content."""
        result = detect_indentation("")
        assert result == ("spaces", 4)


# ---------------------------------------------------------------------------
# detect_language unit tests
# ---------------------------------------------------------------------------


class TestDetectLanguage:
    """Test detect_language helper."""

    def test_python_extension(self):
        """Returns 'python' for path with .py suffix."""
        assert detect_language(Path("main.py")) == "python"

    def test_unknown_extension(self):
        """Returns None for unknown extension."""
        assert detect_language(Path("file.xyz")) is None

    def test_javascript_extension(self):
        """Returns 'javascript' for .js."""
        assert detect_language(Path("app.js")) == "javascript"

    def test_case_insensitive(self):
        """Returns language even for uppercase extensions."""
        assert detect_language(Path("FILE.PY")) == "python"


# ---------------------------------------------------------------------------
# EditorPanel integration tests
# ---------------------------------------------------------------------------


class TestEditorPanelComposition:
    """Integration tests for EditorPanel widget composition."""

    async def test_editor_composes_textarea_not_static(self):
        """EditorPanel composes a TextArea widget (not a Static placeholder)."""
        from textual.widgets import Static, TextArea

        from nano_claude.app import NanoClaudeApp

        app = NanoClaudeApp()
        async with app.run_test(size=(120, 40)) as pilot:
            panel = app.query_one("#editor", EditorPanel)
            # Should have a TextArea
            text_areas = panel.query(TextArea)
            assert len(text_areas) >= 1, "Expected at least one TextArea in EditorPanel"
            # Should NOT have the old placeholder
            statics = panel.query(Static)
            placeholder_ids = [s.id for s in statics if s.id and "placeholder" in s.id]
            assert len(placeholder_ids) == 0, "Old editor-placeholder should not exist"

    async def test_open_file_loads_content_and_language(self, tmp_path: Path):
        """open_file loads file content into TextArea with correct language."""
        from textual.widgets import TextArea

        from nano_claude.app import NanoClaudeApp

        test_file = tmp_path / "example.py"
        test_file.write_text("print('hello')", encoding="utf-8")

        app = NanoClaudeApp()
        async with app.run_test(size=(120, 40)) as pilot:
            editor = app.query_one("#editor", EditorPanel)
            editor.open_file(test_file)

            text_area = editor.query_one("#code-editor", TextArea)
            assert text_area.text == "print('hello')"
            assert text_area.language == "python"
