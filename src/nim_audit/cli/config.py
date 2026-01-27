"""CLI command for config analysis."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from nim_audit.models.config import ImpactLevel

console = Console()


def config_cmd(
    image: str = typer.Option(..., "--image", "-i", help="NIM image reference"),
    env_file: Optional[Path] = typer.Option(
        None,
        "--env-file",
        "-e",
        help="Path to .env file to analyze",
    ),
    format: str = typer.Option(
        "terminal",
        "--format",
        "-f",
        help="Output format (terminal, json)",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path",
    ),
    validate: bool = typer.Option(
        False,
        "--validate",
        help="Validate configuration values",
    ),
    show_all: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Show all config options, including unset",
    ),
) -> None:
    """
    Analyze NIM container configuration.

    Examines environment variables and configuration options,
    providing impact analysis and recommendations.

    Example:
        nim-audit config --image nvcr.io/nim/llama3:1.6.0 --env-file prod.env
    """
    from nim_audit.core.image import NIMImage
    from nim_audit.core.config import ConfigAnalyzer

    with console.status("Loading image..."):
        try:
            nim_image = NIMImage.from_local(image)
        except ValueError:
            nim_image = NIMImage.from_registry(image)

    # Load env file if provided
    env: dict[str, str] = {}
    if env_file and env_file.exists():
        with console.status("Loading environment file..."):
            analyzer = ConfigAnalyzer()
            env = analyzer._load_env_file(str(env_file))

    with console.status("Analyzing configuration..."):
        analyzer = ConfigAnalyzer()
        result = analyzer.analyze(nim_image, env=env)

        if validate:
            validation_errors = analyzer.validate(nim_image, env=env)

    if not result.success:
        console.print("[red]Error:[/red] Failed to analyze configuration")
        for error in result.errors:
            console.print(f"  {error}")
        raise typer.Exit(1)

    report = result.report
    if report is None:
        console.print("[red]Error:[/red] No report generated")
        raise typer.Exit(1)

    if format == "json":
        import json

        output_data = report.model_dump(mode="json")
        json_str = json.dumps(output_data, indent=2, default=str)

        if output:
            output.write_text(json_str)
            console.print(f"Report written to {output}")
        else:
            console.print(json_str)
    else:
        _print_terminal_report(report, show_all, validate, validation_errors if validate else [])


def _print_terminal_report(
    report,
    show_all: bool,
    show_validation: bool,
    validation_errors: list[str],
) -> None:
    """Print a rich terminal report."""
    console.print()
    console.print(
        Panel(
            f"[bold]Image:[/bold] {report.image_reference}",
            title="NIM Config Analysis",
        )
    )

    # Warnings
    if report.warnings:
        console.print()
        console.print("[bold yellow]Warnings[/bold yellow]")
        for warning in report.warnings:
            console.print(f"  [yellow]![/yellow] {warning}")

    # Validation errors
    if show_validation and validation_errors:
        console.print()
        console.print("[bold red]Validation Errors[/bold red]")
        for error in validation_errors:
            console.print(f"  [red]x[/red] {error}")

    # Configuration entries
    entries = report.entries
    if not show_all:
        entries = [e for e in entries if e.is_set]

    if entries:
        console.print()
        table = Table(title="Configuration")
        table.add_column("Variable", style="bold")
        table.add_column("Value")
        table.add_column("Default")
        table.add_column("Impact")
        table.add_column("Description", max_width=40)

        for entry in entries:
            impact_str = ""
            if entry.impact:
                level = entry.impact.level
                style = {
                    ImpactLevel.CRITICAL: "bold red",
                    ImpactLevel.HIGH: "red",
                    ImpactLevel.MEDIUM: "yellow",
                    ImpactLevel.LOW: "green",
                }.get(level, "dim")
                impact_str = f"[{style}]{level.value}[/{style}]"

            name = entry.name
            if entry.is_deprecated:
                name = f"[dim strike]{name}[/dim strike]"
            elif entry.is_required and not entry.is_set:
                name = f"[red]{name}*[/red]"

            table.add_row(
                name,
                entry.value or "[dim]-[/dim]",
                entry.default_value or "[dim]-[/dim]",
                impact_str,
                entry.description[:40] if entry.description else "",
            )

        console.print(table)

    # Recommendations
    if report.recommendations:
        console.print()
        console.print("[bold]Recommendations[/bold]")
        for rec in report.recommendations:
            console.print(f"  - {rec}")

    # Deprecated entries warning
    deprecated = report.deprecated_entries
    if deprecated:
        console.print()
        console.print("[bold yellow]Deprecated Settings in Use[/bold yellow]")
        for entry in deprecated:
            msg = entry.deprecated_message or "This setting is deprecated"
            console.print(f"  [yellow]![/yellow] {entry.name}: {msg}")

    # Required missing
    missing = report.required_missing
    if missing:
        console.print()
        console.print("[bold red]Required Settings Missing[/bold red]")
        for entry in missing:
            console.print(f"  [red]x[/red] {entry.name}: {entry.description}")
