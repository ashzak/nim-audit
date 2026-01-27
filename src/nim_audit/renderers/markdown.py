"""Markdown renderer for nim-audit output."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from nim_audit.renderers.base import BaseRenderer, OutputFormat, RenderContext


class MarkdownRenderer(BaseRenderer):
    """Renderer for Markdown output format.

    Converts audit results to formatted Markdown documents.

    Example:
        renderer = MarkdownRenderer()
        md_str = renderer.render(diff_report, context)
    """

    @property
    def format(self) -> OutputFormat:
        """The output format this renderer produces."""
        return OutputFormat.MARKDOWN

    def render(self, data: Any, context: RenderContext) -> str:
        """Render data to a Markdown string.

        Args:
            data: The data to render
            context: Rendering context

        Returns:
            Markdown string
        """
        # Check data type and render appropriately
        if hasattr(data, "__class__"):
            class_name = data.__class__.__name__

            if class_name == "DiffReport":
                return self._render_diff_report(data, context)
            elif class_name == "ConfigReport":
                return self._render_config_report(data, context)
            elif class_name == "CompatReport":
                return self._render_compat_report(data, context)
            elif class_name == "LintResult":
                return self._render_lint_result(data, context)
            elif class_name == "BehavioralSignature":
                return self._render_fingerprint(data, context)
            elif class_name == "FingerprintComparison":
                return self._render_fingerprint_comparison(data, context)

        # Generic rendering
        return self._render_generic(data, context)

    def _render_diff_report(self, report: Any, context: RenderContext) -> str:
        """Render a diff report to Markdown."""
        lines = [
            "# NIM Diff Report",
            "",
            f"**Generated:** {report.generated_at.isoformat()}",
            "",
            "## Images Compared",
            "",
            f"- **Source:** `{report.source_image.reference}`",
            f"- **Target:** `{report.target_image.reference}`",
            "",
            "## Summary",
            "",
            f"- Total Changes: **{report.total_changes}**",
            f"- Added: {report.added_count}",
            f"- Removed: {report.removed_count}",
            f"- Modified: {report.modified_count}",
            f"- Breaking Changes: **{len(report.breaking_changes)}**",
            "",
        ]

        # Breaking changes
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

        # All changes table
        if report.entries:
            lines.extend(
                [
                    "## All Changes",
                    "",
                    "| Category | Type | Path | Old Value | New Value |",
                    "|----------|------|------|-----------|-----------|",
                ]
            )

            for entry in report.entries:
                old = self._escape_md(entry.old_value or "-")[:40]
                new = self._escape_md(entry.new_value or "-")[:40]
                lines.append(
                    f"| {entry.category.value} | {entry.change_type.value} | "
                    f"`{entry.path}` | {old} | {new} |"
                )

        return "\n".join(lines)

    def _render_config_report(self, report: Any, context: RenderContext) -> str:
        """Render a config report to Markdown."""
        lines = [
            "# NIM Configuration Report",
            "",
            f"**Image:** `{report.image_reference}`",
            "",
        ]

        # Warnings
        if report.warnings:
            lines.extend(["## Warnings", ""])
            for warning in report.warnings:
                lines.append(f"- ⚠️ {warning}")
            lines.append("")

        # Configuration table
        if report.entries:
            lines.extend(
                [
                    "## Configuration",
                    "",
                    "| Variable | Value | Default | Impact | Description |",
                    "|----------|-------|---------|--------|-------------|",
                ]
            )

            for entry in report.entries:
                if entry.is_set or context.verbose:
                    impact = entry.impact.level.value if entry.impact else "-"
                    desc = (entry.description or "")[:30]
                    value = entry.value or "-"
                    default = entry.default_value or "-"
                    name = entry.name
                    if entry.is_deprecated:
                        name = f"~~{name}~~"
                    lines.append(f"| `{name}` | {value} | {default} | {impact} | {desc} |")

            lines.append("")

        # Recommendations
        if report.recommendations:
            lines.extend(["## Recommendations", ""])
            for rec in report.recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        return "\n".join(lines)

    def _render_compat_report(self, report: Any, context: RenderContext) -> str:
        """Render a compatibility report to Markdown."""
        status = "✅ Compatible" if report.compatible else "❌ Not Compatible"

        lines = [
            "# GPU Compatibility Report",
            "",
            f"**Image:** `{report.image_reference}`",
            f"**Status:** {status}",
            "",
            "## Configuration",
            "",
            f"- **GPU:** {report.gpu.name if report.gpu else 'Not specified'}",
            f"- **Driver Version:** {report.driver_version or 'Not specified'}",
            f"- **CUDA Version:** {report.cuda_version or 'Not specified'}",
            "",
            "## Requirements",
            "",
        ]

        reqs = report.requirements
        if reqs.min_compute_capability:
            lines.append(f"- Minimum Compute Capability: {reqs.min_compute_capability}")
        if reqs.min_memory_gb:
            lines.append(f"- Minimum GPU Memory: {reqs.min_memory_gb}GB")
        if reqs.min_driver_version:
            lines.append(f"- Minimum Driver Version: {reqs.min_driver_version}")
        if reqs.supported_gpus:
            lines.append(f"- Supported GPUs: {', '.join(reqs.supported_gpus)}")

        lines.append("")

        # Compatibility checks
        lines.extend(
            [
                "## Compatibility Checks",
                "",
                "| Check | Status |",
                "|-------|--------|",
                f"| Compute Capability | {'✅' if report.compute_compatible else '❌'} |",
                f"| GPU Memory | {'✅' if report.memory_compatible else '❌'} |",
                f"| Driver Version | {'✅' if report.driver_compatible else '❌'} |",
                f"| GPU Supported | {'✅' if report.gpu_supported else '❌'} |",
                "",
            ]
        )

        # Warnings
        if report.warnings:
            lines.extend(["## Warnings", ""])
            for warning in report.warnings:
                lines.append(f"- ⚠️ {warning}")
            lines.append("")

        # Recommendations
        if report.recommendations:
            lines.extend(["## Recommendations", ""])
            for rec in report.recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        return "\n".join(lines)

    def _render_lint_result(self, result: Any, context: RenderContext) -> str:
        """Render a lint result to Markdown."""
        status = "✅ Passed" if result.passed else "❌ Failed"

        lines = [
            "# Lint Report",
            "",
            f"**Image:** `{result.image_reference}`",
            f"**Policy:** {result.policy.name} v{result.policy.version}",
            f"**Status:** {status}",
            "",
            "## Summary",
            "",
            f"- Total Rules: {len(result.policy.enabled_rules)}",
            f"- Errors: {result.error_count}",
            f"- Warnings: {result.warning_count}",
            "",
        ]

        # Violations
        if result.violations:
            lines.extend(
                [
                    "## Violations",
                    "",
                    "| Severity | Rule | Message | Remediation |",
                    "|----------|------|---------|-------------|",
                ]
            )

            for v in result.violations:
                severity_icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(
                    v.severity.value, ""
                )
                remediation = (v.rule.remediation or "-")[:40]
                lines.append(
                    f"| {severity_icon} {v.severity.value} | {v.rule.name} | "
                    f"{v.message} | {remediation} |"
                )

            lines.append("")

        return "\n".join(lines)

    def _render_fingerprint(self, fingerprint: Any, context: RenderContext) -> str:
        """Render a behavioral fingerprint to Markdown."""
        lines = [
            "# Behavioral Fingerprint",
            "",
            f"**Image:** `{fingerprint.image_reference}`",
            f"**ID:** `{fingerprint.fingerprint_id}`",
            f"**Generated:** {fingerprint.generated_at.isoformat()}",
            "",
            "## Metrics",
            "",
            f"- Prompts: {len(fingerprint.responses)}",
            f"- Average Latency: {fingerprint.avg_latency_ms:.1f}ms",
            f"- Total Tokens In: {fingerprint.total_tokens_in}",
            f"- Total Tokens Out: {fingerprint.total_tokens_out}",
            "",
        ]

        if fingerprint.responses:
            lines.extend(
                [
                    "## Responses",
                    "",
                    "| Prompt ID | Latency (ms) | Tokens In | Tokens Out | Hash |",
                    "|-----------|--------------|-----------|------------|------|",
                ]
            )

            for resp in fingerprint.responses:
                lines.append(
                    f"| {resp.prompt_id} | {resp.latency_ms:.1f} | "
                    f"{resp.tokens_in} | {resp.tokens_out} | `{resp.response_hash or '-'}` |"
                )

            lines.append("")

        return "\n".join(lines)

    def _render_fingerprint_comparison(self, comparison: Any, context: RenderContext) -> str:
        """Render a fingerprint comparison to Markdown."""
        status = "✅ Similar" if comparison.is_similar else "❌ Different"

        lines = [
            "# Fingerprint Comparison",
            "",
            f"**Source:** `{comparison.source.image_reference}`",
            f"**Target:** `{comparison.target.image_reference}`",
            f"**Status:** {status}",
            "",
            "## Summary",
            "",
            f"- Similarity Score: **{comparison.similarity_score:.1%}**",
            f"- Identical Responses: {comparison.identical_responses}",
            f"- Different Responses: {comparison.different_responses}",
            f"- Latency Change: {comparison.latency_change_percent:+.1f}%",
            "",
        ]

        if comparison.response_diffs:
            lines.extend(
                [
                    "## Differences",
                    "",
                ]
            )

            for diff in comparison.response_diffs[:10]:
                lines.extend(
                    [
                        f"### {diff['prompt_id']}",
                        "",
                        f"**Source:** {diff['source'][:100]}...",
                        "",
                        f"**Target:** {diff['target'][:100]}...",
                        "",
                    ]
                )

        return "\n".join(lines)

    def _render_generic(self, data: Any, context: RenderContext) -> str:
        """Render generic data to Markdown."""
        if isinstance(data, BaseModel):
            dict_data = data.model_dump(mode="json")
        elif isinstance(data, dict):
            dict_data = data
        else:
            return str(data)

        lines = ["# Report", ""]

        for key, value in dict_data.items():
            lines.append(f"## {key.replace('_', ' ').title()}")
            lines.append("")
            lines.append(f"```\n{value}\n```")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _escape_md(text: str) -> str:
        """Escape special Markdown characters."""
        if not text:
            return text
        return text.replace("|", "\\|").replace("\n", " ")
