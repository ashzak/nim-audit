"""DiffEngine for comparing NIM container images."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from nim_audit.models.common import AuditError
from nim_audit.models.diff import (
    BreakingChange,
    ChangeCategory,
    ChangeType,
    DiffEntry,
    DiffReport,
    DiffResult,
    Severity,
)

if TYPE_CHECKING:
    from nim_audit.core.image import NIMImage
    from nim_audit.extractors.base import Extractor
    from nim_audit.renderers.base import Renderer


class DiffEngine:
    """Engine for comparing two NIM container images.

    The DiffEngine identifies differences between container images,
    including metadata, model artifacts, tokenizers, and API schemas.
    It also detects breaking changes that may affect compatibility.

    Example:
        engine = DiffEngine()
        result = engine.diff(image1, image2)

        if result.success:
            for entry in result.report.entries:
                print(f"{entry.path}: {entry.change_type}")
            for bc in result.report.breaking_changes:
                print(f"BREAKING: {bc.title}")
    """

    def __init__(
        self,
        extractors: list[Extractor] | None = None,
        renderer: Renderer | None = None,
    ) -> None:
        """Initialize the diff engine.

        Args:
            extractors: Optional list of artifact extractors to use
            renderer: Optional renderer for output
        """
        self._extractors = extractors or []
        self._renderer = renderer

    def diff(self, source: "NIMImage", target: "NIMImage") -> DiffResult:
        """Compare two NIM images and generate a diff report.

        Args:
            source: The source (old) image
            target: The target (new) image

        Returns:
            DiffResult containing the comparison report or errors
        """
        try:
            entries: list[DiffEntry] = []
            breaking_changes: list[BreakingChange] = []

            # Compare metadata
            metadata_entries, metadata_breaking = self._diff_metadata(source, target)
            entries.extend(metadata_entries)
            breaking_changes.extend(metadata_breaking)

            # Compare environment variables
            env_entries, env_breaking = self._diff_environment(source, target)
            entries.extend(env_entries)
            breaking_changes.extend(env_breaking)

            # Compare labels
            label_entries = self._diff_labels(source, target)
            entries.extend(label_entries)

            # Compare layers (structural)
            layer_entries, layer_breaking = self._diff_layers(source, target)
            entries.extend(layer_entries)
            breaking_changes.extend(layer_breaking)

            # Run extractors and compare extracted data
            for extractor in self._extractors:
                if extractor.can_extract(source.reference) and extractor.can_extract(
                    target.reference
                ):
                    source_result = extractor.extract(source.reference)
                    target_result = extractor.extract(target.reference)

                    if source_result.success and target_result.success:
                        extractor_entries = self._diff_extracted_data(
                            source_result.data,
                            target_result.data,
                            extractor.name,
                        )
                        entries.extend(extractor_entries)

            # Calculate statistics
            added = sum(1 for e in entries if e.change_type == ChangeType.ADDED)
            removed = sum(1 for e in entries if e.change_type == ChangeType.REMOVED)
            modified = sum(1 for e in entries if e.change_type == ChangeType.MODIFIED)

            report = DiffReport(
                source_image=source.metadata,
                target_image=target.metadata,
                generated_at=datetime.utcnow(),
                entries=entries,
                breaking_changes=breaking_changes,
                total_changes=len(entries),
                added_count=added,
                removed_count=removed,
                modified_count=modified,
            )

            return DiffResult.ok(report)

        except Exception as e:
            return DiffResult.fail(
                [
                    AuditError(
                        code="DIFF_ERROR",
                        message=f"Failed to diff images: {e}",
                        details={"source": source.reference, "target": target.reference},
                    )
                ]
            )

    def _diff_metadata(
        self, source: "NIMImage", target: "NIMImage"
    ) -> tuple[list[DiffEntry], list[BreakingChange]]:
        """Compare image metadata."""
        entries: list[DiffEntry] = []
        breaking: list[BreakingChange] = []

        sm = source.metadata
        tm = target.metadata

        # Compare NIM version
        if sm.nim_version != tm.nim_version:
            entry = DiffEntry(
                category=ChangeCategory.METADATA,
                change_type=ChangeType.MODIFIED,
                path="nim_version",
                old_value=sm.nim_version,
                new_value=tm.nim_version,
                severity=Severity.WARNING,
                description="NIM version changed",
            )
            entries.append(entry)

        # Compare model name
        if sm.model_name != tm.model_name:
            entry = DiffEntry(
                category=ChangeCategory.MODEL,
                change_type=ChangeType.MODIFIED,
                path="model_name",
                old_value=sm.model_name,
                new_value=tm.model_name,
                severity=Severity.BREAKING,
                description="Model name changed",
            )
            entries.append(entry)
            breaking.append(
                BreakingChange(
                    category=ChangeCategory.MODEL,
                    title="Model name changed",
                    description=f"Model changed from {sm.model_name} to {tm.model_name}",
                    impact="Different model may produce different outputs",
                    migration="Verify model outputs match expectations",
                    related_entries=["model_name"],
                )
            )

        # Compare model version
        if sm.model_version != tm.model_version:
            entry = DiffEntry(
                category=ChangeCategory.MODEL,
                change_type=ChangeType.MODIFIED,
                path="model_version",
                old_value=sm.model_version,
                new_value=tm.model_version,
                severity=Severity.WARNING,
                description="Model version changed",
            )
            entries.append(entry)

        # Compare quantization
        if sm.quantization != tm.quantization:
            entry = DiffEntry(
                category=ChangeCategory.MODEL,
                change_type=ChangeType.MODIFIED,
                path="quantization",
                old_value=sm.quantization,
                new_value=tm.quantization,
                severity=Severity.WARNING,
                description="Quantization method changed",
            )
            entries.append(entry)

        # Compare architecture
        if sm.architecture != tm.architecture:
            entry = DiffEntry(
                category=ChangeCategory.METADATA,
                change_type=ChangeType.MODIFIED,
                path="architecture",
                old_value=sm.architecture,
                new_value=tm.architecture,
                severity=Severity.BREAKING,
                description="Target architecture changed",
            )
            entries.append(entry)
            breaking.append(
                BreakingChange(
                    category=ChangeCategory.METADATA,
                    title="Architecture changed",
                    description=f"Architecture changed from {sm.architecture} to {tm.architecture}",
                    impact="Container may not run on previous hardware",
                    migration="Ensure target system supports new architecture",
                    related_entries=["architecture"],
                )
            )

        # Compare exposed ports
        source_ports = set(sm.exposed_ports)
        target_ports = set(tm.exposed_ports)

        for port in source_ports - target_ports:
            entries.append(
                DiffEntry(
                    category=ChangeCategory.CONFIG,
                    change_type=ChangeType.REMOVED,
                    path=f"exposed_ports/{port}",
                    old_value=str(port),
                    new_value=None,
                    severity=Severity.WARNING,
                    description=f"Port {port} no longer exposed",
                )
            )

        for port in target_ports - source_ports:
            entries.append(
                DiffEntry(
                    category=ChangeCategory.CONFIG,
                    change_type=ChangeType.ADDED,
                    path=f"exposed_ports/{port}",
                    old_value=None,
                    new_value=str(port),
                    severity=Severity.INFO,
                    description=f"Port {port} now exposed",
                )
            )

        return entries, breaking

    def _diff_environment(
        self, source: "NIMImage", target: "NIMImage"
    ) -> tuple[list[DiffEntry], list[BreakingChange]]:
        """Compare environment variables."""
        entries: list[DiffEntry] = []
        breaking: list[BreakingChange] = []

        source_env = source.metadata.env
        target_env = target.metadata.env

        all_keys = set(source_env.keys()) | set(target_env.keys())

        for key in sorted(all_keys):
            source_val = source_env.get(key)
            target_val = target_env.get(key)

            if source_val is None and target_val is not None:
                entries.append(
                    DiffEntry(
                        category=ChangeCategory.ENVIRONMENT,
                        change_type=ChangeType.ADDED,
                        path=f"env/{key}",
                        old_value=None,
                        new_value=target_val,
                        severity=Severity.INFO,
                        description=f"Environment variable {key} added",
                    )
                )
            elif source_val is not None and target_val is None:
                entries.append(
                    DiffEntry(
                        category=ChangeCategory.ENVIRONMENT,
                        change_type=ChangeType.REMOVED,
                        path=f"env/{key}",
                        old_value=source_val,
                        new_value=None,
                        severity=Severity.WARNING,
                        description=f"Environment variable {key} removed",
                    )
                )
            elif source_val != target_val:
                entries.append(
                    DiffEntry(
                        category=ChangeCategory.ENVIRONMENT,
                        change_type=ChangeType.MODIFIED,
                        path=f"env/{key}",
                        old_value=source_val,
                        new_value=target_val,
                        severity=Severity.INFO,
                        description=f"Environment variable {key} changed",
                    )
                )

        return entries, breaking

    def _diff_labels(self, source: "NIMImage", target: "NIMImage") -> list[DiffEntry]:
        """Compare container labels."""
        entries: list[DiffEntry] = []

        source_labels = source.metadata.labels
        target_labels = target.metadata.labels

        all_keys = set(source_labels.keys()) | set(target_labels.keys())

        for key in sorted(all_keys):
            source_val = source_labels.get(key)
            target_val = target_labels.get(key)

            if source_val is None and target_val is not None:
                entries.append(
                    DiffEntry(
                        category=ChangeCategory.METADATA,
                        change_type=ChangeType.ADDED,
                        path=f"labels/{key}",
                        old_value=None,
                        new_value=target_val,
                        severity=Severity.INFO,
                        description=f"Label {key} added",
                    )
                )
            elif source_val is not None and target_val is None:
                entries.append(
                    DiffEntry(
                        category=ChangeCategory.METADATA,
                        change_type=ChangeType.REMOVED,
                        path=f"labels/{key}",
                        old_value=source_val,
                        new_value=None,
                        severity=Severity.INFO,
                        description=f"Label {key} removed",
                    )
                )
            elif source_val != target_val:
                entries.append(
                    DiffEntry(
                        category=ChangeCategory.METADATA,
                        change_type=ChangeType.MODIFIED,
                        path=f"labels/{key}",
                        old_value=source_val,
                        new_value=target_val,
                        severity=Severity.INFO,
                        description=f"Label {key} changed",
                    )
                )

        return entries

    def _diff_layers(
        self, source: "NIMImage", target: "NIMImage"
    ) -> tuple[list[DiffEntry], list[BreakingChange]]:
        """Compare image layers."""
        entries: list[DiffEntry] = []
        breaking: list[BreakingChange] = []

        source_layers = source.metadata.manifest.layers if source.metadata.manifest else []
        target_layers = target.metadata.manifest.layers if target.metadata.manifest else []

        source_digests = {str(layer.digest) for layer in source_layers}
        target_digests = {str(layer.digest) for layer in target_layers}

        # Layers removed
        for digest in source_digests - target_digests:
            entries.append(
                DiffEntry(
                    category=ChangeCategory.LAYER,
                    change_type=ChangeType.REMOVED,
                    path=f"layers/{digest[:12]}",
                    old_value=digest,
                    new_value=None,
                    severity=Severity.INFO,
                    description="Layer removed",
                )
            )

        # Layers added
        for digest in target_digests - source_digests:
            entries.append(
                DiffEntry(
                    category=ChangeCategory.LAYER,
                    change_type=ChangeType.ADDED,
                    path=f"layers/{digest[:12]}",
                    old_value=None,
                    new_value=digest,
                    severity=Severity.INFO,
                    description="Layer added",
                )
            )

        # Layer count change
        if len(source_layers) != len(target_layers):
            entries.append(
                DiffEntry(
                    category=ChangeCategory.LAYER,
                    change_type=ChangeType.MODIFIED,
                    path="layers/count",
                    old_value=str(len(source_layers)),
                    new_value=str(len(target_layers)),
                    severity=Severity.INFO,
                    description="Number of layers changed",
                )
            )

        return entries, breaking

    def _diff_extracted_data(
        self,
        source_data: dict,
        target_data: dict,
        extractor_name: str,
    ) -> list[DiffEntry]:
        """Compare data extracted by an extractor."""
        entries: list[DiffEntry] = []

        all_keys = set(source_data.keys()) | set(target_data.keys())

        for key in sorted(all_keys):
            source_val = source_data.get(key)
            target_val = target_data.get(key)

            if source_val is None and target_val is not None:
                entries.append(
                    DiffEntry(
                        category=ChangeCategory.RUNTIME,
                        change_type=ChangeType.ADDED,
                        path=f"{extractor_name}/{key}",
                        old_value=None,
                        new_value=str(target_val),
                        severity=Severity.INFO,
                        description=f"{key} added",
                    )
                )
            elif source_val is not None and target_val is None:
                entries.append(
                    DiffEntry(
                        category=ChangeCategory.RUNTIME,
                        change_type=ChangeType.REMOVED,
                        path=f"{extractor_name}/{key}",
                        old_value=str(source_val),
                        new_value=None,
                        severity=Severity.WARNING,
                        description=f"{key} removed",
                    )
                )
            elif source_val != target_val:
                entries.append(
                    DiffEntry(
                        category=ChangeCategory.RUNTIME,
                        change_type=ChangeType.MODIFIED,
                        path=f"{extractor_name}/{key}",
                        old_value=str(source_val),
                        new_value=str(target_val),
                        severity=Severity.INFO,
                        description=f"{key} changed",
                    )
                )

        return entries
