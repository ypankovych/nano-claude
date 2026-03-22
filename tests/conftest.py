"""Shared test fixtures for nano-claude."""

import pytest


@pytest.fixture
def app():
    """Create a NanoClaudeApp instance for testing."""
    from nano_claude.app import NanoClaudeApp

    return NanoClaudeApp()
