"""Base extractor protocol and types."""

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from nim_audit.models.common import AuditError


class ExtractorResult(BaseModel):
    """Result from an extractor."""

    model_config = {"frozen": True}

    extractor_name: str = Field(description="Name of the extractor that produced this result")
    success: bool = Field(description="Whether extraction succeeded")
    data: dict[str, Any] = Field(default_factory=dict, description="Extracted data")
    errors: list[AuditError] = Field(default_factory=list, description="Errors during extraction")

    @classmethod
    def ok(cls, name: str, data: dict[str, Any]) -> "ExtractorResult":
        """Create a successful result."""
        return cls(extractor_name=name, success=True, data=data)

    @classmethod
    def fail(cls, name: str, errors: list[AuditError]) -> "ExtractorResult":
        """Create a failed result."""
        return cls(extractor_name=name, success=False, errors=errors)


@runtime_checkable
class Extractor(Protocol):
    """Protocol for artifact extractors.

    Extractors are responsible for extracting specific types of artifacts
    from NIM container images (e.g., metadata, model files, tokenizers).

    To implement a custom extractor:
    1. Create a class that implements this protocol
    2. Register it with ExtractorRegistry

    Example:
        class MyExtractor:
            @property
            def name(self) -> str:
                return "my_extractor"

            @property
            def description(self) -> str:
                return "Extracts my custom data"

            def can_extract(self, image_id: str) -> bool:
                return True  # or check if image has required artifacts

            def extract(self, image_id: str, container_fs: Path | None = None) -> ExtractorResult:
                # Extract data from image
                return ExtractorResult.ok(self.name, {"key": "value"})
    """

    @property
    def name(self) -> str:
        """Unique name for this extractor."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description of what this extractor does."""
        ...

    def can_extract(self, image_id: str) -> bool:
        """Check if this extractor can handle the given image.

        Args:
            image_id: Image identifier (can be reference or ID)

        Returns:
            True if this extractor can extract from the image
        """
        ...

    def extract(self, image_id: str, container_fs: "Path | None" = None) -> ExtractorResult:
        """Extract artifacts from the image.

        Args:
            image_id: Image identifier (can be reference or ID)
            container_fs: Optional path to extracted container filesystem

        Returns:
            ExtractorResult with extracted data or errors
        """
        ...


# Import Path for type hints without circular imports
from pathlib import Path
