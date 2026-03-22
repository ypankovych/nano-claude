"""CLI entry point for nano-claude."""

import click


@click.command()
@click.argument("path", required=False, default=None, type=click.Path(exists=True))
def main(path: str | None) -> None:
    """Launch nano-claude TUI application.

    Optionally provide a PATH to open a specific file or directory.
    """
    from nano_claude.app import NanoClaudeApp

    app = NanoClaudeApp()
    if path is not None:
        app.initial_path = path
    app.run()
