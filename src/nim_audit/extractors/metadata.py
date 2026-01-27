"""Metadata extractor for NIM containers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nim_audit.extractors.base import ExtractorResult
from nim_audit.registry.docker import DockerRegistry


class MetadataExtractor:
    """Extractor for container metadata.

    Extracts labels, environment variables, and other metadata
    from NIM container images.

    Example:
        extractor = MetadataExtractor()
        if extractor.can_extract("nvcr.io/nim/llama3:1.5.0"):
            result = extractor.extract("nvcr.io/nim/llama3:1.5.0")
            print(result.data["labels"])
    """

    @property
    def name(self) -> str:
        """Unique name for this extractor."""
        return "metadata"

    @property
    def description(self) -> str:
        """Human-readable description."""
        return "Extracts container labels, environment variables, and build metadata"

    def can_extract(self, image_id: str) -> bool:
        """Check if this extractor can handle the given image.

        This extractor can handle any Docker/OCI image.

        Args:
            image_id: Image identifier

        Returns:
            True (metadata can be extracted from any image)
        """
        return True

    def extract(
        self,
        image_id: str,
        container_fs: Path | None = None,
    ) -> ExtractorResult:
        """Extract metadata from the image.

        Args:
            image_id: Image identifier
            container_fs: Optional path to extracted container filesystem

        Returns:
            ExtractorResult with extracted metadata
        """
        from nim_audit.models.common import AuditError

        try:
            registry = DockerRegistry()
            metadata = registry.get_metadata(image_id)

            data: dict[str, Any] = {
                "reference": metadata.reference,
                "repository": metadata.repository,
                "tag": metadata.tag,
                "digest": str(metadata.digest) if metadata.digest else None,
                "created": metadata.created.isoformat() if metadata.created else None,
                "architecture": metadata.architecture,
                "os": metadata.os,
                "labels": metadata.labels,
                "env": metadata.env,
                "exposed_ports": metadata.exposed_ports,
                "entrypoint": metadata.entrypoint,
                "cmd": metadata.cmd,
                # NIM-specific
                "nim_version": metadata.nim_version,
                "model_name": metadata.model_name,
                "model_version": metadata.model_version,
                "quantization": metadata.quantization,
                # Layer info
                "layer_count": len(metadata.manifest.layers) if metadata.manifest else 0,
                "total_size": metadata.total_size,
            }

            return ExtractorResult.ok(self.name, data)

        except Exception as e:
            return ExtractorResult.fail(
                self.name,
                [
                    AuditError(
                        code="METADATA_EXTRACTION_ERROR",
                        message=f"Failed to extract metadata: {e}",
                        details={"image_id": image_id},
                    )
                ],
            )
