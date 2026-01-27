"""CLI commands for environment variable analysis."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from nim_audit.models.env import Severity

app = typer.Typer(
    name="env",
    help="Environment variable analysis tools.",
    no_args_is_help=True,
)

console = Console()


def _load_env_file(path: Path) -> dict[str, str]:
    """Load environment variables from a file."""
    env: dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                if key:
                    env[key] = value
    return env


@app.command()
def lint(
    env_file: Path = typer.Option(
        ...,
        "--env-file",
        "-e",
        help="Path to .env file to lint",
        exists=True,
    ),
    rules: Optional[Path] = typer.Option(
        None,
        "--rules",
        "-r",
        help="Path to custom rules YAML file",
    ),
    registry: Optional[Path] = typer.Option(
        None,
        "--registry",
        help="Path to custom registry YAML file",
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
) -> None:
    """
    Lint environment variables against registry and rules.

    Validates that environment variables conform to expected patterns
    and identifies potential issues based on the registry metadata.

    Example:
        nim-audit env lint --env-file prod.env --rules rules.yaml
    """
    from nim_audit.core.env import load_registry, load_rules, lint_env

    # Load env file
    with console.status("Loading environment file..."):
        env_vars = _load_env_file(env_file)

    # Load registry and rules
    with console.status("Loading registry and rules..."):
        reg = load_registry(str(registry) if registry else None)
        rules_doc = load_rules(str(rules) if rules else None)

    # No discovered vars when just linting a file (would need image)
    discovered_vars: list[str] = []

    # Run lint
    with console.status("Linting environment..."):
        result = lint_env(
            effective=env_vars,
            env_file_vars=env_vars,
            discovered_vars=discovered_vars,
            reg=reg,
            rules_doc=rules_doc,
        )

    if format == "json":
        import json

        output_data = result.model_dump(mode="json")
        json_str = json.dumps(output_data, indent=2)

        if output:
            output.write_text(json_str)
            console.print(f"Report written to {output}")
        else:
            console.print(json_str)
    else:
        _print_lint_report(result, env_file)

    # Exit with error if there are failures
    if result.overall == "FAIL":
        raise typer.Exit(1)


def _print_lint_report(result, env_file: Path) -> None:
    """Print a rich terminal lint report."""
    console.print()

    # Status
    status_style = {
        "PASS": "[bold green]PASS[/bold green]",
        "WARN": "[bold yellow]WARN[/bold yellow]",
        "FAIL": "[bold red]FAIL[/bold red]",
    }
    status = status_style.get(result.overall, result.overall)

    console.print(
        Panel(
            f"[bold]File:[/bold] {env_file}\n[bold]Status:[/bold] {status}",
            title="Environment Lint Report",
        )
    )

    # Summary
    console.print()
    table = Table(title="Summary", show_header=False)
    table.add_column("Metric", style="bold")
    table.add_column("Count")
    table.add_row("Failures", f"[red]{result.counts.get('fail', 0)}[/red]")
    table.add_row("Warnings", f"[yellow]{result.counts.get('warn', 0)}[/yellow]")
    table.add_row("Info", f"[blue]{result.counts.get('info', 0)}[/blue]")
    console.print(table)

    # Findings
    if result.findings:
        console.print()
        table = Table(title="Findings")
        table.add_column("Severity")
        table.add_column("ID", style="bold")
        table.add_column("Variable")
        table.add_column("Message", max_width=50)

        for f in result.findings:
            severity_style = {
                Severity.FAIL: "red",
                Severity.WARN: "yellow",
                Severity.INFO: "blue",
            }.get(f.severity, "white")

            table.add_row(
                f"[{severity_style}]{f.severity.value}[/{severity_style}]",
                f.id,
                f.env or "-",
                f.message,
            )

        console.print(table)
    else:
        console.print()
        console.print("[green]No issues found![/green]")


@app.command()
def describe(
    var: str = typer.Argument(
        ...,
        help="Environment variable name to describe",
    ),
    registry: Optional[Path] = typer.Option(
        None,
        "--registry",
        help="Path to custom registry YAML file",
    ),
    format: str = typer.Option(
        "terminal",
        "--format",
        "-f",
        help="Output format (terminal, json)",
    ),
) -> None:
    """
    Describe an environment variable from the registry.

    Shows detailed information about a known NIM environment variable
    including its impacts, interactions, and failure modes.

    Example:
        nim-audit env describe NIM_MAX_BATCH_SIZE
    """
    from nim_audit.core.env import load_registry, interactions_for

    with console.status("Loading registry..."):
        reg = load_registry(str(registry) if registry else None)

    entry = reg.entries.get(var)

    if format == "json":
        import json

        if entry:
            output_data = {
                "found": True,
                "entry": entry.model_dump(mode="json"),
                "interactions": interactions_for(var, reg),
            }
        else:
            output_data = {"found": False, "name": var}

        console.print(json.dumps(output_data, indent=2))
    else:
        if entry:
            console.print()
            console.print(Panel(f"[bold]{var}[/bold]", title="Environment Variable"))

            # Basic info
            table = Table(show_header=False, box=None)
            table.add_column("Property", style="bold", width=15)
            table.add_column("Value")

            table.add_row("Type", entry.type or "-")
            table.add_row("Scope", entry.scope or "-")
            table.add_row("Default", entry.default or "-")
            table.add_row("Confidence", entry.confidence)

            if entry.precedence:
                table.add_row("Precedence", entry.precedence)

            console.print(table)

            # Affects
            if entry.affects:
                console.print()
                console.print("[bold]Affects[/bold]")
                for a in entry.affects:
                    console.print(f"  - {a.metric.value}: {a.impact.value}")

            # Failure modes
            if entry.failure_modes:
                console.print()
                console.print("[bold yellow]Failure Modes[/bold yellow]")
                for fm in entry.failure_modes:
                    console.print(f"  [yellow]![/yellow] {fm}")

            # Interactions
            ints = interactions_for(var, reg)
            if ints:
                console.print()
                console.print("[bold]Interactions[/bold]")
                for i in ints:
                    console.print(f"  - {i['with']} ({i['type']}): {i['description']}")
        else:
            console.print(f"[yellow]Variable '{var}' not found in registry.[/yellow]")
            console.print("It may be a valid NIM variable not yet documented.")


@app.command()
def diff(
    old_env: Path = typer.Argument(
        ...,
        help="Path to old/baseline .env file",
        exists=True,
    ),
    new_env: Path = typer.Argument(
        ...,
        help="Path to new/target .env file",
        exists=True,
    ),
    registry: Optional[Path] = typer.Option(
        None,
        "--registry",
        help="Path to custom registry YAML file",
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
) -> None:
    """
    Diff two environment files.

    Compares two .env files and identifies added, removed,
    and changed variables with risk assessment.

    Example:
        nim-audit env diff staging.env prod.env
    """
    from nim_audit.core.env import load_registry, env_surface, diff_surfaces, risk_delta
    from nim_audit.models.env import EnvSurface

    # Load files
    with console.status("Loading environment files..."):
        old_vars = _load_env_file(old_env)
        new_vars = _load_env_file(new_env)

    with console.status("Loading registry..."):
        reg = load_registry(str(registry) if registry else None)

    # Build surfaces and diff
    old_surface = EnvSurface(vars=old_vars)
    new_surface = EnvSurface(vars=new_vars)
    env_diff = diff_surfaces(old_surface, new_surface)

    # Calculate risk
    changed_keys = list(env_diff.changed.keys())
    risky = risk_delta(changed_keys, reg)
    env_diff = env_diff.model_copy(update={"risky_changed": risky})

    if format == "json":
        import json

        output_data = env_diff.model_dump(mode="json")
        json_str = json.dumps(output_data, indent=2)

        if output:
            output.write_text(json_str)
            console.print(f"Report written to {output}")
        else:
            console.print(json_str)
    else:
        _print_diff_report(env_diff, old_env, new_env)


def _print_diff_report(env_diff, old_env: Path, new_env: Path) -> None:
    """Print a rich terminal diff report."""
    console.print()
    console.print(
        Panel(
            f"[bold]Old:[/bold] {old_env}\n[bold]New:[/bold] {new_env}",
            title="Environment Diff",
        )
    )

    # Summary
    console.print()
    table = Table(title="Summary", show_header=False)
    table.add_column("Metric", style="bold")
    table.add_column("Count")
    table.add_row("Added", f"[green]{len(env_diff.added)}[/green]")
    table.add_row("Removed", f"[red]{len(env_diff.removed)}[/red]")
    table.add_row("Changed", f"[yellow]{len(env_diff.changed)}[/yellow]")
    table.add_row("Risky", f"[bold red]{env_diff.risky_changed}[/bold red]")
    console.print(table)

    # Added
    if env_diff.added:
        console.print()
        console.print("[bold green]Added Variables[/bold green]")
        for var in env_diff.added:
            console.print(f"  [green]+[/green] {var}")

    # Removed
    if env_diff.removed:
        console.print()
        console.print("[bold red]Removed Variables[/bold red]")
        for var in env_diff.removed:
            console.print(f"  [red]-[/red] {var}")

    # Changed
    if env_diff.changed:
        console.print()
        table = Table(title="Changed Variables")
        table.add_column("Variable", style="bold")
        table.add_column("Old Value")
        table.add_column("New Value")

        for var, (old, new) in env_diff.changed.items():
            table.add_row(var, str(old) if old is not None else "[dim]unset[/dim]", str(new) if new is not None else "[dim]unset[/dim]")

        console.print(table)

    if not env_diff.added and not env_diff.removed and not env_diff.changed:
        console.print()
        console.print("[green]No differences found.[/green]")


@app.command()
def registry_list(
    registry: Optional[Path] = typer.Option(
        None,
        "--registry",
        help="Path to custom registry YAML file",
    ),
    format: str = typer.Option(
        "terminal",
        "--format",
        "-f",
        help="Output format (terminal, json)",
    ),
) -> None:
    """
    List all variables in the registry.

    Shows all known NIM environment variables with their
    types, defaults, and confidence levels.

    Example:
        nim-audit env registry-list
    """
    from nim_audit.core.env import load_registry

    with console.status("Loading registry..."):
        reg = load_registry(str(registry) if registry else None)

    if format == "json":
        import json

        output_data = {
            "count": len(reg.entries),
            "entries": [e.model_dump(mode="json") for e in reg.entries.values()],
            "warnings": reg.warnings,
        }
        console.print(json.dumps(output_data, indent=2))
    else:
        console.print()
        console.print(Panel(f"[bold]Variables:[/bold] {len(reg.entries)}", title="Environment Registry"))

        if reg.warnings:
            console.print()
            console.print("[bold yellow]Warnings[/bold yellow]")
            for w in reg.warnings:
                console.print(f"  [yellow]![/yellow] {w}")

        console.print()
        table = Table(title="Known Variables")
        table.add_column("Name", style="bold")
        table.add_column("Type")
        table.add_column("Default")
        table.add_column("Confidence")
        table.add_column("Affects")

        for entry in sorted(reg.entries.values(), key=lambda e: e.name):
            affects_str = ", ".join(f"{a.metric.value}:{a.impact.value}" for a in entry.affects)
            table.add_row(
                entry.name,
                entry.type or "-",
                entry.default or "-",
                entry.confidence,
                affects_str[:30] if affects_str else "-",
            )

        console.print(table)
