"""Tests for file tree panel and configuration constants."""

from nano_claude.config.settings import (
    EXTENSION_TO_LANGUAGE,
    HIDDEN_PATTERNS,
    MAX_FILE_SIZE_BYTES,
)


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
