"""CLI command for policy linting."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from nim_audit.models.policy import RuleSeverity

console = Console()


def lint_cmd(
    image: str = typer.Option(..., "--image", "-i", help="NIM image reference"),
    policy: Optional[Path] = typer.Option(
        None,
        "--policy",
        "-p",
        help="Path to policy YAML file",
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
    no_builtin: bool = typer.Option(
        False,
        "--no-builtin",
        help="Disable built-in rules",
    ),
    severity: Optional[str] = typer.Option(
        None,
        "--severity",
        "-s",
        help="Minimum severity to report (info, warning, error)",
    ),
) -> None:
    """
    Lint a NIM image against policies.

    Validates container configuration and metadata against
    a set of rules defined in a policy file.

    Example:
        nim-audit lint --image nvcr.io/nim/llama3:1.6.0 --policy enterprise.yaml
    """
    from nim_audit.core.image import NIMImage
    from nim_audit.core.lint import PolicyLinter

    with console.status("Loading image..."):
        try:
            nim_image = NIMImage.from_local(image)
        except ValueError:
            nim_image = NIMImage.from_registry(image)

    # Load custom policy if provided
    custom_policy = None
    if policy and policy.exists():
        with console.status("Loading policy..."):
            linter = PolicyLinter()
            custom_policy = linter.load_policy(str(policy))

    with console.status("Running lint checks..."):
        linter = PolicyLinter()
        result = linter.lint(nim_image, policy=custom_policy, include_builtin=not no_builtin)

    if not result.success:
        console.print("[red]Error:[/red] Linting failed")
        for error in result.errors:
            console.print(f"  {error}")
        raise typer.Exit(1)

    # Filter by severity if specified
    violations = result.violations
    if severity:
        try:
            min_severity = RuleSeverity(severity)
            severity_order = [RuleSeverity.INFO, RuleSeverity.WARNING, RuleSeverity.ERROR]
            min_index = severity_order.index(min_severity)
            violations = [
                v for v in violations if severity_order.index(v.severity) >= min_index
            ]
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid severity: {severity}")
            raise typer.Exit(1)

    if format == "json":
        import json

        output_data = {
            "image": result.image_reference,
            "policy": result.policy.name,
            "passed": result.passed,
            "violations": [
                {
                    "rule_id": v.rule.id,
                    "rule_name": v.rule.name,
                    "severity": v.severity.value,
                    "message": v.message,
                    "remediation": v.rule.remediation,
                }
                for v in violations
            ],
        }
        json_str = json.dumps(output_data, indent=2)

        if output:
            output.write_text(json_str)
            console.print(f"Report written to {output}")
        else:
            console.print(json_str)
    else:
        _print_terminal_report(result, violations)

    # Exit with error if there are error-level violations
    if not result.passed:
        raise typer.Exit(1)


def _print_terminal_report(result, violations) -> None:
    """Print a rich terminal report."""
    console.print()

    # Status
    if result.passed:
        status = "[bold green]PASSED[/bold green]"
    else:
        status = "[bold red]FAILED[/bold red]"

    console.print(
        Panel(
            f"[bold]Image:[/bold] {result.image_reference}\n"
            f"[bold]Policy:[/bold] {result.policy.name} v{result.policy.version}\n"
            f"[bold]Status:[/bold] {status}",
            title="Lint Report",
        )
    )

    # Summary
    console.print()
    table = Table(title="Summary", show_header=False)
    table.add_column("Metric", style="bold")
    table.add_column("Count")
    table.add_row("Total Rules", str(len(result.policy.enabled_rules)))
    table.add_row("Errors", f"[red]{result.error_count}[/red]")
    table.add_row("Warnings", f"[yellow]{result.warning_count}[/yellow]")
    table.add_row(
        "Info",
        str(sum(1 for v in result.violations if v.severity == RuleSeverity.INFO)),
    )
    console.print(table)

    # Violations
    if violations:
        console.print()
        table = Table(title="Violations")
        table.add_column("Severity")
        table.add_column("Rule", style="bold")
        table.add_column("Message")
        table.add_column("Remediation", max_width=40)

        for v in violations:
            severity_style = {
                RuleSeverity.ERROR: "red",
                RuleSeverity.WARNING: "yellow",
                RuleSeverity.INFO: "blue",
            }.get(v.severity, "white")

            table.add_row(
                f"[{severity_style}]{v.severity.value.upper()}[/{severity_style}]",
                v.rule.name,
                v.message,
                v.rule.remediation or "-",
            )

        console.print(table)
    else:
        console.print()
        console.print("[green]No violations found![/green]")
