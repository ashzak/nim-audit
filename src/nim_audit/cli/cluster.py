"""CLI command for cluster compatibility scanning."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def cluster_cmd(
    image: str = typer.Option(..., "--image", "-i", help="NIM image reference"),
    kubeconfig: Optional[Path] = typer.Option(
        None,
        "--kubeconfig",
        "-k",
        help="Path to kubeconfig file",
    ),
    namespace: Optional[str] = typer.Option(
        None,
        "--namespace",
        "-n",
        help="Kubernetes namespace to check",
    ),
    context: Optional[str] = typer.Option(
        None,
        "--context",
        "-c",
        help="Kubernetes context to use",
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
    Scan Kubernetes cluster for NIM compatibility.

    Checks GPU availability and compatibility across all nodes
    in a Kubernetes cluster.

    Example:
        nim-audit cluster --image nvcr.io/nim/llama3:1.6.0 --kubeconfig ~/.kube/config
    """
    from nim_audit.core.image import NIMImage
    from nim_audit.core.compat import CompatChecker

    with console.status("Loading image..."):
        try:
            nim_image = NIMImage.from_local(image)
        except ValueError:
            nim_image = NIMImage.from_registry(image)

    with console.status("Scanning cluster..."):
        nodes = _get_cluster_nodes(kubeconfig, context, namespace)

    if not nodes:
        console.print("[yellow]Warning:[/yellow] No GPU nodes found in cluster")
        raise typer.Exit(0)

    # Check compatibility for each node
    checker = CompatChecker()
    results = []

    with console.status("Checking node compatibility..."):
        for node in nodes:
            result = checker.check(
                nim_image,
                gpu=node.get("gpu"),
                driver_version=node.get("driver_version"),
            )
            results.append(
                {
                    "node": node["name"],
                    "gpu": node.get("gpu"),
                    "gpu_count": node.get("gpu_count", 0),
                    "compatible": result.report.compatible if result.report else False,
                    "issues": result.report.compatibility_issues if result.report else [],
                }
            )

    if format == "json":
        import json

        output_data = {
            "image": image,
            "nodes": results,
            "compatible_nodes": sum(1 for r in results if r["compatible"]),
            "total_nodes": len(results),
        }
        json_str = json.dumps(output_data, indent=2)

        if output:
            output.write_text(json_str)
            console.print(f"Report written to {output}")
        else:
            console.print(json_str)
    else:
        _print_terminal_report(image, results)


def _print_terminal_report(image: str, results: list) -> None:
    """Print a rich terminal report."""
    compatible_count = sum(1 for r in results if r["compatible"])
    total_count = len(results)

    console.print()
    console.print(
        Panel(
            f"[bold]Image:[/bold] {image}\n"
            f"[bold]Compatible Nodes:[/bold] {compatible_count}/{total_count}",
            title="Cluster Compatibility Scan",
        )
    )

    console.print()
    table = Table(title="Node Compatibility")
    table.add_column("Node", style="bold")
    table.add_column("GPU")
    table.add_column("Count")
    table.add_column("Compatible")
    table.add_column("Issues", max_width=40)

    for result in results:
        status = "[green]Yes[/green]" if result["compatible"] else "[red]No[/red]"
        issues = ", ".join(result["issues"]) if result["issues"] else "-"

        table.add_row(
            result["node"],
            result["gpu"] or "Unknown",
            str(result["gpu_count"]),
            status,
            issues,
        )

    console.print(table)

    # Summary
    if compatible_count == 0:
        console.print()
        console.print("[red]No compatible nodes found in cluster![/red]")
    elif compatible_count < total_count:
        console.print()
        console.print(
            f"[yellow]Warning:[/yellow] {total_count - compatible_count} nodes are not compatible"
        )


def _get_cluster_nodes(
    kubeconfig: Optional[Path],
    context: Optional[str],
    namespace: Optional[str],
) -> list[dict]:
    """Get GPU nodes from Kubernetes cluster.

    Returns:
        List of node info dicts with gpu, driver_version, etc.
    """
    try:
        import subprocess
        import json as json_lib

        # Build kubectl command
        cmd = ["kubectl", "get", "nodes", "-o", "json"]
        if kubeconfig:
            cmd.extend(["--kubeconfig", str(kubeconfig)])
        if context:
            cmd.extend(["--context", context])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            console.print(f"[red]kubectl error:[/red] {result.stderr}")
            return []

        data = json_lib.loads(result.stdout)
        nodes = []

        for item in data.get("items", []):
            metadata = item.get("metadata", {})
            labels = metadata.get("labels", {})
            status = item.get("status", {})
            capacity = status.get("capacity", {})

            # Check for GPU resources
            gpu_count = 0
            if "nvidia.com/gpu" in capacity:
                try:
                    gpu_count = int(capacity["nvidia.com/gpu"])
                except (ValueError, TypeError):
                    pass

            if gpu_count > 0:
                # Extract GPU info from labels
                gpu_name = labels.get(
                    "nvidia.com/gpu.product",
                    labels.get("accelerator", "Unknown"),
                )
                driver_version = labels.get("nvidia.com/driver.version")

                nodes.append(
                    {
                        "name": metadata.get("name"),
                        "gpu": gpu_name,
                        "gpu_count": gpu_count,
                        "driver_version": driver_version,
                        "labels": labels,
                    }
                )

        return nodes

    except FileNotFoundError:
        console.print("[red]Error:[/red] kubectl not found. Please install kubectl.")
        return []
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to get cluster nodes: {e}")
        return []
