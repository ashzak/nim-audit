"""Terminal renderer for nim-audit output."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from nim_audit.renderers.base import BaseRenderer, OutputFormat, RenderContext


class TerminalRenderer(BaseRenderer):
    """Renderer for rich terminal output.

    Uses the Rich library to render colorful, formatted output
    to the terminal.

    Example:
        renderer = TerminalRenderer()
        renderer.render(diff_report, context)
    """

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the terminal renderer.

        Args:
            console: Rich console to use. Creates a new one if None.
        """
        self._console = console or Console()

    @property
    def format(self) -> OutputFormat:
        """The output format this renderer produces."""
        return OutputFormat.TERMINAL

    def render(self, data: Any, context: RenderContext) -> str:
        """Render data to the terminal.

        Note: This method prints to the console and returns an empty string.
        For capturing output, use Console.capture().

        Args:
            data: The data to render
            context: Rendering context

        Returns:
            Empty string (output is printed to console)
        """
        # Check data type and render appropriately
        if hasattr(data, "__class__"):
            class_name = data.__class__.__name__

            if class_name == "DiffReport":
                self._render_diff_report(data, context)
            elif class_name == "ConfigReport":
                self._render_config_report(data, context)
            elif class_name == "CompatReport":
                self._render_compat_report(data, context)
            elif class_name == "LintResult":
                self._render_lint_result(data, context)
            elif class_name == "BehavioralSignature":
                self._render_fingerprint(data, context)
            elif class_name == "FingerprintComparison":
                self._render_fingerprint_comparison(data, context)
            else:
                self._render_generic(data, context)
        else:
            self._render_generic(data, context)

        return ""

    def render_to_file(self, data: Any, context: RenderContext) -> None:
        """Render data to a file.

        Captures terminal output and writes to file.

        Args:
            data: The data to render
            context: Rendering context
        """
        if context.output_path is None:
            raise ValueError("output_path must be set in context for file rendering")

        # Create a console that captures output
        file_console = Console(record=True, force_terminal=True)
        original_console = self._console
        self._console = file_console

        try:
            self.render(data, context)
            # Export with ANSI codes for color support
            output = file_console.export_text(styles=True)
            context.output_path.write_text(output)
        finally:
            self._console = original_console

    def _render_diff_report(self, report: Any, context: RenderContext) -> None:
        """Render a diff report."""
        # Header
        self._console.print()
        self._console.print(
            Panel(
                f"[bold]Source:[/bold] {report.source_image.reference}\n"
                f"[bold]Target:[/bold] {report.target_image.reference}",
                title="NIM Diff Report",
            )
        )

        # Breaking changes
        if report.breaking_changes:
            self._console.print()
            self._console.print("[bold red]Breaking Changes[/bold red]")
            for bc in report.breaking_changes:
                self._console.print(f"  [red]![/red] {bc.title}")
                self._console.print(f"      {bc.description}")
                if bc.migration:
                    self._console.print(f"      [dim]Migration: {bc.migration}[/dim]")

        # Summary table
        self._console.print()
        table = Table(title="Summary", show_header=False)
        table.add_column("Metric", style="bold")
        table.add_column("Count")
        table.add_row("Total Changes", str(report.total_changes))
        table.add_row("Added", f"[green]{report.added_count}[/green]")
        table.add_row("Removed", f"[red]{report.removed_count}[/red]")
        table.add_row("Modified", f"[yellow]{report.modified_count}[/yellow]")
        table.add_row("Breaking", f"[bold red]{len(report.breaking_changes)}[/bold red]")
        self._console.print(table)

        # Changes table
        if report.entries and context.verbose:
            self._console.print()
            table = Table(title="Changes")
            table.add_column("Category", style="dim")
            table.add_column("Type")
            table.add_column("Path")
            table.add_column("Old Value", max_width=30)
            table.add_column("New Value", max_width=30)

            for entry in report.entries:
                type_style = {
                    "added": "green",
                    "removed": "red",
                    "modified": "yellow",
                }.get(entry.change_type.value, "white")

                table.add_row(
                    entry.category.value,
                    f"[{type_style}]{entry.change_type.value}[/{type_style}]",
                    entry.path,
                    entry.old_value or "-",
                    entry.new_value or "-",
                )

            self._console.print(table)

    def _render_config_report(self, report: Any, context: RenderContext) -> None:
        """Render a config report."""
        self._console.print()
        self._console.print(
            Panel(
                f"[bold]Image:[/bold] {report.image_reference}",
                title="NIM Config Analysis",
            )
        )

        # Warnings
        if report.warnings:
            self._console.print()
            self._console.print("[bold yellow]Warnings[/bold yellow]")
            for warning in report.warnings:
                self._console.print(f"  [yellow]![/yellow] {warning}")

        # Configuration table
        entries = report.entries if context.verbose else [e for e in report.entries if e.is_set]

        if entries:
            self._console.print()
            table = Table(title="Configuration")
            table.add_column("Variable", style="bold")
            table.add_column("Value")
            table.add_column("Default")
            table.add_column("Impact")

            for entry in entries:
                impact_str = ""
                if entry.impact:
                    style = {
                        "critical": "bold red",
                        "high": "red",
                        "medium": "yellow",
                        "low": "green",
                    }.get(entry.impact.level.value, "dim")
                    impact_str = f"[{style}]{entry.impact.level.value}[/{style}]"

                name = entry.name
                if entry.is_deprecated:
                    name = f"[dim strike]{name}[/dim strike]"

                table.add_row(
                    name,
                    entry.value or "[dim]-[/dim]",
                    entry.default_value or "[dim]-[/dim]",
                    impact_str,
                )

            self._console.print(table)

        # Recommendations
        if report.recommendations:
            self._console.print()
            self._console.print("[bold]Recommendations[/bold]")
            for rec in report.recommendations:
                self._console.print(f"  - {rec}")

    def _render_compat_report(self, report: Any, context: RenderContext) -> None:
        """Render a compatibility report."""
        self._console.print()

        status = "[bold green]COMPATIBLE[/bold green]" if report.compatible else "[bold red]NOT COMPATIBLE[/bold red]"

        self._console.print(
            Panel(
                f"[bold]Image:[/bold] {report.image_reference}\n"
                f"[bold]GPU:[/bold] {report.gpu.name if report.gpu else 'Not specified'}\n"
                f"[bold]Status:[/bold] {status}",
                title="GPU Compatibility Check",
            )
        )

        # Checks table
        self._console.print()
        table = Table(title="Compatibility Checks")
        table.add_column("Check", style="bold")
        table.add_column("Status")

        def status_icon(ok: bool) -> str:
            return "[green]PASS[/green]" if ok else "[red]FAIL[/red]"

        table.add_row("Compute Capability", status_icon(report.compute_compatible))
        table.add_row("GPU Memory", status_icon(report.memory_compatible))
        table.add_row("Driver Version", status_icon(report.driver_compatible))
        table.add_row("GPU Supported", status_icon(report.gpu_supported))

        self._console.print(table)

        # Warnings
        if report.warnings:
            self._console.print()
            self._console.print("[bold yellow]Warnings[/bold yellow]")
            for warning in report.warnings:
                self._console.print(f"  [yellow]![/yellow] {warning}")

    def _render_lint_result(self, result: Any, context: RenderContext) -> None:
        """Render a lint result."""
        self._console.print()

        status = "[bold green]PASSED[/bold green]" if result.passed else "[bold red]FAILED[/bold red]"

        self._console.print(
            Panel(
                f"[bold]Image:[/bold] {result.image_reference}\n"
                f"[bold]Policy:[/bold] {result.policy.name} v{result.policy.version}\n"
                f"[bold]Status:[/bold] {status}",
                title="Lint Report",
            )
        )

        # Summary
        self._console.print()
        table = Table(title="Summary", show_header=False)
        table.add_column("Metric", style="bold")
        table.add_column("Count")
        table.add_row("Total Rules", str(len(result.policy.enabled_rules)))
        table.add_row("Errors", f"[red]{result.error_count}[/red]")
        table.add_row("Warnings", f"[yellow]{result.warning_count}[/yellow]")
        self._console.print(table)

        # Violations
        if result.violations:
            self._console.print()
            table = Table(title="Violations")
            table.add_column("Severity")
            table.add_column("Rule", style="bold")
            table.add_column("Message")

            for v in result.violations:
                severity_style = {
                    "error": "red",
                    "warning": "yellow",
                    "info": "blue",
                }.get(v.severity.value, "white")

                table.add_row(
                    f"[{severity_style}]{v.severity.value.upper()}[/{severity_style}]",
                    v.rule.name,
                    v.message,
                )

            self._console.print(table)

    def _render_fingerprint(self, fingerprint: Any, context: RenderContext) -> None:
        """Render a behavioral fingerprint."""
        self._console.print()
        self._console.print(
            Panel(
                f"[bold]Image:[/bold] {fingerprint.image_reference}\n"
                f"[bold]ID:[/bold] {fingerprint.fingerprint_id}\n"
                f"[bold]Prompts:[/bold] {len(fingerprint.responses)}",
                title="Behavioral Fingerprint",
            )
        )

        # Metrics
        self._console.print()
        self._console.print("[bold]Metrics[/bold]")
        self._console.print(f"  Average Latency: {fingerprint.avg_latency_ms:.1f}ms")
        self._console.print(f"  Total Tokens In: {fingerprint.total_tokens_in}")
        self._console.print(f"  Total Tokens Out: {fingerprint.total_tokens_out}")

    def _render_fingerprint_comparison(self, comparison: Any, context: RenderContext) -> None:
        """Render a fingerprint comparison."""
        self._console.print()

        status = "[bold green]SIMILAR[/bold green]" if comparison.is_similar else "[bold red]DIFFERENT[/bold red]"

        self._console.print(
            Panel(
                f"[bold]Source:[/bold] {comparison.source.image_reference}\n"
                f"[bold]Target:[/bold] {comparison.target.image_reference}\n"
                f"[bold]Similarity:[/bold] {comparison.similarity_score:.1%}\n"
                f"[bold]Status:[/bold] {status}",
                title="Fingerprint Comparison",
            )
        )

    def _render_generic(self, data: Any, context: RenderContext) -> None:
        """Render generic data."""
        import json

        from pydantic import BaseModel

        if isinstance(data, BaseModel):
            dict_data = data.model_dump(mode="json")
        elif isinstance(data, dict):
            dict_data = data
        else:
            self._console.print(str(data))
            return

        json_str = json.dumps(dict_data, indent=2, default=str)
        self._console.print(json_str)
