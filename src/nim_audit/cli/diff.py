"""CLI command for diffing NIM containers."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from nim_audit.models.diff import Severity

app = typer.Typer(help="Compare two NIM container versions.")
console = Console()


@app.callback(invoke_without_command=True)
def diff_cmd(
    ctx: typer.Context,
    source: str = typer.Argument(..., help="Source (old) image reference"),
    target: str = typer.Argument(..., help="Target (new) image reference"),
    format: str = typer.Option(
        "terminal",
        "--format",
        "-f",
        help="Output format (terminal, json, markdown)",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path",
    ),
    breaking_only: bool = typer.Option(
        False,
        "--breaking-only",
        help="Only show breaking changes",
    ),
    category: Optional[str] = typer.Option(
        None,
        "--category",
        "-c",
        help="Filter by category (metadata, model, tokenizer, api, runtime, layer, config, environment)",
    ),
) -> None:
    """
    Compare two NIM container versions.

    Analyzes differences in metadata, model artifacts, configuration,
    and API schemas between two container images.

    Example:
        nim-audit diff nvcr.io/nim/llama3:1.5.0 nvcr.io/nim/llama3:1.6.0
    """
    from nim_audit.core.image import NIMImage
    from nim_audit.core.diff import DiffEngine
    from nim_audit.models.diff import ChangeCategory

    with console.status(f"Loading images..."):
        try:
            source_image = NIMImage.from_local(source)
        except ValueError:
            source_image = NIMImage.from_registry(source)

        try:
            target_image = NIMImage.from_local(target)
        except ValueError:
            target_image = NIMImage.from_registry(target)

    with console.status("Analyzing differences..."):
        engine = DiffEngine()
        result = engine.diff(source_image, target_image)

    if not result.success:
        console.print("[red]Error:[/red] Failed to diff images")
        for error in result.errors:
            console.print(f"  {error}")
        raise typer.Exit(1)

    report = result.report
    if report is None:
        console.print("[red]Error:[/red] No report generated")
        raise typer.Exit(1)

    # Filter entries if category specified
    entries = report.entries
    if category:
        try:
            cat = ChangeCategory(category)
            entries = [e for e in entries if e.category == cat]
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid category: {category}")
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

    elif format == "markdown":
        md = _generate_markdown(report)
        if output:
            output.write_text(md)
            console.print(f"Report written to {output}")
        else:
            console.print(md)

    else:  # terminal
        _print_terminal_report(report, entries, breaking_only)


def _print_terminal_report(report, entries, breaking_only: bool) -> None:
    """Print a rich terminal report."""
    # Header
    console.print()
    console.print(
        Panel(
            f"[bold]Source:[/bold] {report.source_image.reference}\n"
            f"[bold]Target:[/bold] {report.target_image.reference}",
            title="NIM Diff Report",
        )
    )

    # Breaking changes
    if report.breaking_changes:
        console.print()
        console.print("[bold red]Breaking Changes[/bold red]")
        for bc in report.breaking_changes:
            console.print(f"  [red]![/red] {bc.title}")
            console.print(f"      {bc.description}")
            if bc.migration:
                console.print(f"      [dim]Migration: {bc.migration}[/dim]")

    if breaking_only:
        return

    # Summary
    console.print()
    table = Table(title="Summary", show_header=False)
    table.add_column("Metric", style="bold")
    table.add_column("Count")
    table.add_row("Total Changes", str(report.total_changes))
    table.add_row("Added", f"[green]{report.added_count}[/green]")
    table.add_row("Removed", f"[red]{report.removed_count}[/red]")
    table.add_row("Modified", f"[yellow]{report.modified_count}[/yellow]")
    table.add_row("Breaking", f"[bold red]{len(report.breaking_changes)}[/bold red]")
    console.print(table)

    # Detailed changes
    if entries:
        console.print()
        table = Table(title="Changes")
        table.add_column("Category", style="dim")
        table.add_column("Type")
        table.add_column("Path")
        table.add_column("Old Value", max_width=30)
        table.add_column("New Value", max_width=30)

        for entry in entries:
            type_style = {
                "added": "green",
                "removed": "red",
                "modified": "yellow",
            }.get(entry.change_type.value, "white")

            severity_marker = ""
            if entry.severity == Severity.BREAKING:
                severity_marker = " [bold red]![/bold red]"

            table.add_row(
                entry.category.value,
                f"[{type_style}]{entry.change_type.value}[/{type_style}]{severity_marker}",
                entry.path,
                entry.old_value or "-",
                entry.new_value or "-",
            )

        console.print(table)


def _generate_markdown(report) -> str:
    """Generate a markdown report."""
    lines = [
        "# NIM Diff Report",
        "",
        f"**Source:** `{report.source_image.reference}`",
        f"**Target:** `{report.target_image.reference}`",
        f"**Generated:** {report.generated_at}",
        "",
        "## Summary",
        "",
        f"- Total Changes: {report.total_changes}",
        f"- Added: {report.added_count}",
        f"- Removed: {report.removed_count}",
        f"- Modified: {report.modified_count}",
        f"- Breaking Changes: {len(report.breaking_changes)}",
        "",
    ]

    if report.breaking_changes:
        lines.extend(
            [
                "## Breaking Changes",
                "",
            ]
        )
        for bc in report.breaking_changes:
            lines.extend(
                [
                    f"### {bc.title}",
                    "",
                    bc.description,
                    "",
                    f"**Impact:** {bc.impact}",
                    "",
                ]
            )
            if bc.migration:
                lines.append(f"**Migration:** {bc.migration}")
                lines.append("")

    lines.extend(
        [
            "## All Changes",
            "",
            "| Category | Type | Path | Old | New |",
            "|----------|------|------|-----|-----|",
        ]
    )

    for entry in report.entries:
        old = entry.old_value or "-"
        new = entry.new_value or "-"
        # Escape pipe characters
        old = old.replace("|", "\\|")[:50]
        new = new.replace("|", "\\|")[:50]
        lines.append(
            f"| {entry.category.value} | {entry.change_type.value} | "
            f"`{entry.path}` | {old} | {new} |"
        )

    return "\n".join(lines)
