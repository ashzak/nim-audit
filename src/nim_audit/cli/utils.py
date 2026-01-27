"""Shared utilities for CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

import typer
from pydantic import BaseModel
from rich.console import Console

if TYPE_CHECKING:
    from nim_audit.core.image import NIMImage

T = TypeVar("T", bound=BaseModel)

# Shared console instance
console = Console()


def load_image(image: str) -> "NIMImage":
    """Load a NIM image from local or registry.

    Tries local first, falls back to registry.

    Args:
        image: Image reference

    Returns:
        Loaded NIMImage instance
    """
    from nim_audit.core.image import NIMImage

    with console.status("Loading image..."):
        try:
            return NIMImage.from_local(image)
        except ValueError:
            return NIMImage.from_registry(image)


def handle_result_errors(result: Any, error_message: str = "Operation failed") -> None:
    """Handle errors in a result object and exit if failed.

    Args:
        result: Result object with success and errors attributes
        error_message: Message to display on error
    """
    if not result.success:
        console.print(f"[red]Error:[/red] {error_message}")
        for error in result.errors:
            console.print(f"  {error}")
        raise typer.Exit(1)


def check_report(report: Any | None, error_message: str = "No report generated") -> None:
    """Check that a report was generated and exit if not.

    Args:
        report: Report object (may be None)
        error_message: Message to display if report is None
    """
    if report is None:
        console.print(f"[red]Error:[/red] {error_message}")
        raise typer.Exit(1)


def output_json(data: dict[str, Any] | BaseModel, output: Path | None = None) -> None:
    """Output data as JSON to console or file.

    Args:
        data: Data to output (dict or Pydantic model)
        output: Optional output file path
    """
    if isinstance(data, BaseModel):
        data = data.model_dump(mode="json")

    json_str = json.dumps(data, indent=2, default=str)

    if output:
        output.write_text(json_str)
        console.print(f"Report written to {output}")
    else:
        console.print(json_str)


def severity_style(severity: str) -> str:
    """Get Rich style for a severity level.

    Args:
        severity: Severity value (error, warning, info)

    Returns:
        Rich style string
    """
    styles = {
        "error": "red",
        "warning": "yellow",
        "info": "blue",
        "critical": "bold red",
        "high": "red",
        "medium": "yellow",
        "low": "green",
        "breaking": "bold red",
    }
    return styles.get(severity.lower(), "white")


def status_icon(success: bool) -> str:
    """Get a colored status icon.

    Args:
        success: Whether the status is successful

    Returns:
        Formatted status string
    """
    return "[green]OK[/green]" if success else "[red]FAIL[/red]"
