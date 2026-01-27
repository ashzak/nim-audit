"""CLI command for behavioral fingerprinting."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

app = typer.Typer(help="Generate and compare behavioral fingerprints.")
console = Console()


@app.callback(invoke_without_command=True)
def fingerprint_cmd(
    ctx: typer.Context,
    image: Optional[str] = typer.Option(
        None,
        "--image",
        "-i",
        help="NIM image reference to fingerprint",
    ),
    endpoint: Optional[str] = typer.Option(
        None,
        "--endpoint",
        "-e",
        help="NIM endpoint URL (if already running)",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file for fingerprint",
    ),
    format: str = typer.Option(
        "terminal",
        "--format",
        "-f",
        help="Output format (terminal, json)",
    ),
) -> None:
    """
    Generate a behavioral fingerprint for a NIM image.

    Runs a standard suite of prompts against the model to capture
    its behavioral signature for comparison across versions.

    Example:
        nim-audit fingerprint --image nvcr.io/nim/llama3:1.6.0 --endpoint http://localhost:8000
    """
    if ctx.invoked_subcommand is not None:
        return

    if not image:
        console.print("[red]Error:[/red] --image is required")
        raise typer.Exit(1)

    if not endpoint:
        console.print("[red]Error:[/red] --endpoint is required (container auto-start not yet supported)")
        raise typer.Exit(1)

    from nim_audit.core.image import NIMImage
    from nim_audit.core.fingerprint import BehavioralFingerprinter

    with console.status("Loading image..."):
        try:
            nim_image = NIMImage.from_local(image)
        except ValueError:
            nim_image = NIMImage.from_registry(image)

    with console.status("Generating fingerprint..."):
        fingerprinter = BehavioralFingerprinter()
        result = fingerprinter.generate(nim_image, endpoint=endpoint)

    if not result.success:
        console.print("[red]Error:[/red] Failed to generate fingerprint")
        for error in result.errors:
            console.print(f"  {error}")
        raise typer.Exit(1)

    fingerprint = result.fingerprint
    if fingerprint is None:
        console.print("[red]Error:[/red] No fingerprint generated")
        raise typer.Exit(1)

    # Save fingerprint
    if output:
        fingerprinter.save_fingerprint(fingerprint, str(output))
        console.print(f"[green]Fingerprint saved to {output}[/green]")

    if format == "json":
        import json

        json_str = json.dumps(fingerprint.model_dump(mode="json"), indent=2, default=str)
        if not output:
            console.print(json_str)
    else:
        _print_terminal_report(fingerprint)


@app.command()
def compare(
    source: Path = typer.Argument(..., help="Source fingerprint file"),
    target: Path = typer.Argument(..., help="Target fingerprint file"),
    tolerance: float = typer.Option(
        0.05,
        "--tolerance",
        "-t",
        help="Similarity tolerance (0.0-1.0)",
    ),
    format: str = typer.Option(
        "terminal",
        "--format",
        "-f",
        help="Output format (terminal, json)",
    ),
) -> None:
    """
    Compare two behavioral fingerprints.

    Analyzes the similarity between two fingerprints and reports
    any behavioral differences.

    Example:
        nim-audit fingerprint compare v1.5.json v1.6.json --tolerance 0.05
    """
    from nim_audit.core.fingerprint import BehavioralFingerprinter

    if not source.exists():
        console.print(f"[red]Error:[/red] Source file not found: {source}")
        raise typer.Exit(1)

    if not target.exists():
        console.print(f"[red]Error:[/red] Target file not found: {target}")
        raise typer.Exit(1)

    with console.status("Loading fingerprints..."):
        fingerprinter = BehavioralFingerprinter()
        source_fp = fingerprinter.load_fingerprint(str(source))
        target_fp = fingerprinter.load_fingerprint(str(target))

    with console.status("Comparing fingerprints..."):
        comparison = fingerprinter.compare(source_fp, target_fp, tolerance=tolerance)

    if format == "json":
        import json

        output_data = {
            "source": source_fp.image_reference,
            "target": target_fp.image_reference,
            "similarity_score": comparison.similarity_score,
            "identical_responses": comparison.identical_responses,
            "different_responses": comparison.different_responses,
            "latency_change_percent": comparison.latency_change_percent,
            "is_similar": comparison.is_similar,
            "differences": comparison.response_diffs,
        }
        console.print(json.dumps(output_data, indent=2))
    else:
        _print_comparison_report(comparison, tolerance)

    # Exit with error if not similar
    if not comparison.is_similar:
        raise typer.Exit(1)


def _print_terminal_report(fingerprint) -> None:
    """Print fingerprint details."""
    console.print()
    console.print(
        Panel(
            f"[bold]Image:[/bold] {fingerprint.image_reference}\n"
            f"[bold]ID:[/bold] {fingerprint.fingerprint_id}\n"
            f"[bold]Generated:[/bold] {fingerprint.generated_at}\n"
            f"[bold]Prompts:[/bold] {len(fingerprint.responses)}",
            title="Behavioral Fingerprint",
        )
    )

    # Response summary
    console.print()
    table = Table(title="Responses")
    table.add_column("Prompt ID", style="bold")
    table.add_column("Latency (ms)")
    table.add_column("Tokens In")
    table.add_column("Tokens Out")
    table.add_column("Hash")

    for resp in fingerprint.responses:
        table.add_row(
            resp.prompt_id,
            f"{resp.latency_ms:.1f}",
            str(resp.tokens_in),
            str(resp.tokens_out),
            resp.response_hash or "-",
        )

    console.print(table)

    # Metrics
    console.print()
    console.print("[bold]Metrics[/bold]")
    console.print(f"  Average Latency: {fingerprint.avg_latency_ms:.1f}ms")
    console.print(f"  Total Tokens In: {fingerprint.total_tokens_in}")
    console.print(f"  Total Tokens Out: {fingerprint.total_tokens_out}")


def _print_comparison_report(comparison, tolerance: float) -> None:
    """Print comparison details."""
    console.print()

    # Status
    if comparison.is_similar:
        status = "[bold green]SIMILAR[/bold green]"
    else:
        status = "[bold red]DIFFERENT[/bold red]"

    console.print(
        Panel(
            f"[bold]Source:[/bold] {comparison.source.image_reference}\n"
            f"[bold]Target:[/bold] {comparison.target.image_reference}\n"
            f"[bold]Similarity:[/bold] {comparison.similarity_score:.1%}\n"
            f"[bold]Status:[/bold] {status}",
            title="Fingerprint Comparison",
        )
    )

    # Summary
    console.print()
    table = Table(title="Summary", show_header=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("Identical Responses", str(comparison.identical_responses))
    table.add_row("Different Responses", str(comparison.different_responses))
    table.add_row("Similarity Score", f"{comparison.similarity_score:.1%}")
    table.add_row("Tolerance", f"{tolerance:.1%}")

    latency_color = "green" if comparison.latency_change_percent <= 10 else "yellow"
    if comparison.latency_change_percent > 25:
        latency_color = "red"
    table.add_row(
        "Latency Change",
        f"[{latency_color}]{comparison.latency_change_percent:+.1f}%[/{latency_color}]",
    )
    console.print(table)

    # Differences
    if comparison.response_diffs:
        console.print()
        console.print("[bold]Response Differences[/bold]")
        for diff in comparison.response_diffs[:5]:  # Show first 5
            console.print(f"\n  [bold]{diff['prompt_id']}[/bold]")
            console.print(f"    Source: {diff['source'][:60]}...")
            console.print(f"    Target: {diff['target'][:60]}...")

        if len(comparison.response_diffs) > 5:
            console.print(f"\n  [dim]... and {len(comparison.response_diffs) - 5} more[/dim]")
