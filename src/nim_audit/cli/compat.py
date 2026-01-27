"""CLI command for GPU compatibility checking."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def compat_cmd(
    image: str = typer.Option(..., "--image", "-i", help="NIM image reference"),
    gpu: Optional[str] = typer.Option(
        None,
        "--gpu",
        "-g",
        help="Target GPU (e.g., A100, H100, L4)",
    ),
    driver: Optional[str] = typer.Option(
        None,
        "--driver",
        "-d",
        help="NVIDIA driver version",
    ),
    cuda: Optional[str] = typer.Option(
        None,
        "--cuda",
        "-c",
        help="CUDA version",
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
    detect: bool = typer.Option(
        False,
        "--detect",
        help="Auto-detect local GPU and driver",
    ),
) -> None:
    """
    Check GPU compatibility for a NIM image.

    Verifies that the target GPU meets the requirements
    for running the specified NIM container.

    Example:
        nim-audit compat --image nvcr.io/nim/llama3:1.6.0 --gpu A10 --driver 550.54
    """
    from nim_audit.core.image import NIMImage
    from nim_audit.core.compat import CompatChecker

    with console.status("Loading image..."):
        try:
            nim_image = NIMImage.from_local(image)
        except ValueError:
            nim_image = NIMImage.from_registry(image)

    # Auto-detect GPU if requested
    detected_gpu = None
    detected_driver = None
    if detect:
        with console.status("Detecting GPU..."):
            detected_gpu, detected_driver = _detect_gpu()
            if detected_gpu:
                console.print(f"[green]Detected GPU:[/green] {detected_gpu}")
            if detected_driver:
                console.print(f"[green]Detected Driver:[/green] {detected_driver}")

    # Use detected values if not explicitly provided
    gpu = gpu or detected_gpu
    driver = driver or detected_driver

    if not gpu:
        console.print("[yellow]Warning:[/yellow] No GPU specified. Use --gpu or --detect")

    with console.status("Checking compatibility..."):
        checker = CompatChecker()
        result = checker.check(nim_image, gpu=gpu, driver_version=driver, cuda_version=cuda)

    if not result.success:
        console.print("[red]Error:[/red] Failed to check compatibility")
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
        _print_terminal_report(report)

    # Exit with error code if not compatible
    if not report.compatible:
        raise typer.Exit(1)


def _print_terminal_report(report) -> None:
    """Print a rich terminal report."""
    console.print()

    # Compatibility status
    if report.compatible:
        status = "[bold green]COMPATIBLE[/bold green]"
    else:
        status = "[bold red]NOT COMPATIBLE[/bold red]"

    console.print(
        Panel(
            f"[bold]Image:[/bold] {report.image_reference}\n"
            f"[bold]GPU:[/bold] {report.gpu.name if report.gpu else 'Not specified'}\n"
            f"[bold]Driver:[/bold] {report.driver_version or 'Not specified'}\n"
            f"[bold]Status:[/bold] {status}",
            title="GPU Compatibility Check",
        )
    )

    # Requirements
    reqs = report.requirements
    console.print()
    table = Table(title="Requirements")
    table.add_column("Requirement", style="bold")
    table.add_column("Required")
    table.add_column("Actual")
    table.add_column("Status")

    def status_icon(ok: bool) -> str:
        return "[green]OK[/green]" if ok else "[red]FAIL[/red]"

    if reqs.min_compute_capability:
        actual = report.gpu.compute_capability if report.gpu else "Unknown"
        table.add_row(
            "Compute Capability",
            f">= {reqs.min_compute_capability}",
            actual or "Unknown",
            status_icon(report.compute_compatible),
        )

    if reqs.min_memory_gb:
        actual = f"{report.gpu.memory_gb}GB" if report.gpu and report.gpu.memory_gb else "Unknown"
        table.add_row(
            "GPU Memory",
            f">= {reqs.min_memory_gb}GB",
            actual,
            status_icon(report.memory_compatible),
        )

    if reqs.min_driver_version:
        table.add_row(
            "Driver Version",
            f">= {reqs.min_driver_version}",
            report.driver_version or "Unknown",
            status_icon(report.driver_compatible),
        )

    if reqs.supported_gpus:
        gpu_name = report.gpu.name if report.gpu else "Unknown"
        table.add_row(
            "Supported GPUs",
            ", ".join(reqs.supported_gpus[:3]) + ("..." if len(reqs.supported_gpus) > 3 else ""),
            gpu_name,
            status_icon(report.gpu_supported),
        )

    console.print(table)

    # Warnings
    if report.warnings:
        console.print()
        console.print("[bold yellow]Warnings[/bold yellow]")
        for warning in report.warnings:
            console.print(f"  [yellow]![/yellow] {warning}")

    # Recommendations
    if report.recommendations:
        console.print()
        console.print("[bold]Recommendations[/bold]")
        for rec in report.recommendations:
            console.print(f"  - {rec}")


def _detect_gpu() -> tuple[Optional[str], Optional[str]]:
    """Detect local GPU and driver version.

    Returns:
        Tuple of (gpu_name, driver_version)
    """
    try:
        import subprocess

        # Try nvidia-smi
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            line = result.stdout.strip().split("\n")[0]
            parts = line.split(",")
            if len(parts) >= 2:
                gpu_name = parts[0].strip()
                # Extract model name (e.g., "NVIDIA A100" -> "A100")
                for prefix in ["NVIDIA ", "GeForce ", "Tesla "]:
                    if gpu_name.startswith(prefix):
                        gpu_name = gpu_name[len(prefix) :]
                driver_version = parts[1].strip()
                return gpu_name, driver_version
    except FileNotFoundError:
        pass
    except Exception:
        pass

    return None, None
