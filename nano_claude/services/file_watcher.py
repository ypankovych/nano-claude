"""File watcher service for detecting external filesystem changes."""

from __future__ import annotations

from pathlib import Path

import anyio
from textual.message import Message
from watchfiles import Change, DefaultFilter, awatch


class FileSystemChanged(Message):
    """Posted when watched filesystem paths change externally.

    Attributes:
        changes: Set of (Change, path_str) tuples from watchfiles.
    """

    def __init__(self, changes: set[tuple[Change, str]]) -> None:
        super().__init__()
        self.changes = changes


class FileWatcherService:
    """Background service that watches a directory for file changes.

    Uses watchfiles awatch() with an 800ms debounce to batch rapid
    changes. Posts FileSystemChanged messages to the Textual app when
    files are added, modified, or deleted.

    The app.py is responsible for handling FileSystemChanged and
    coordinating the response (e.g., refreshing the file tree).
    """

    def __init__(self, app, watch_path: Path) -> None:
        self.app = app
        self.watch_path = watch_path
        self._stop_event: anyio.Event | None = None

    async def start(self) -> None:
        """Start watching the directory for changes.

        This is a long-running coroutine meant to be run as a Textual worker.
        It blocks until stop() is called or the app exits.
        """
        self._stop_event = anyio.Event()

        watch_filter = DefaultFilter(
            ignore_dirs=(
                "__pycache__",
                ".git",
                "node_modules",
                ".venv",
                ".mypy_cache",
                ".pytest_cache",
                ".ruff_cache",
            )
        )

        try:
            async for changes in awatch(
                self.watch_path,
                watch_filter=watch_filter,
                debounce=800,
                stop_event=self._stop_event,
            ):
                self.app.post_message(FileSystemChanged(changes))
        except Exception:
            # Watcher stopped or errored -- exit gracefully
            pass

    def stop(self) -> None:
        """Signal the watcher to stop."""
        if self._stop_event is not None:
            self._stop_event.set()
