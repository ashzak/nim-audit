"""Main CLI entry point for nim-audit."""

import typer
from rich.console import Console

from nim_audit.cli import diff, config, compat, lint, fingerprint, cluster

app = typer.Typer(
    name="nim-audit",
    help="A professional tool for auditing NVIDIA NIM containers.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()

# Register subcommands
app.add_typer(diff.app, name="diff")
app.command(name="config")(config.config_cmd)
app.command(name="compat")(compat.compat_cmd)
app.command(name="lint")(lint.lint_cmd)
app.add_typer(fingerprint.app, name="fingerprint")
app.command(name="cluster")(cluster.cluster_cmd)


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-essential output"),
) -> None:
    """
    nim-audit: A professional tool for auditing NVIDIA NIM containers.

    Provides comprehensive auditing capabilities including:

    - [bold]diff[/bold]: Compare two NIM container versions
    - [bold]config[/bold]: Analyze configuration and environment variables
    - [bold]compat[/bold]: Check GPU and driver compatibility
    - [bold]lint[/bold]: Validate against enterprise policies
    - [bold]fingerprint[/bold]: Generate and compare behavioral signatures
    - [bold]cluster[/bold]: Scan Kubernetes cluster compatibility
    """
    from nim_audit.utils.logging import configure_logging

    if verbose:
        configure_logging(level="DEBUG")
    elif quiet:
        configure_logging(level="WARNING")
    else:
        configure_logging(level="INFO")


@app.command()
def version() -> None:
    """Show the nim-audit version."""
    from nim_audit import __version__

    console.print(f"nim-audit version {__version__}")


if __name__ == "__main__":
    app()
