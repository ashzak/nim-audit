"""Image-related data models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ImageDigest(BaseModel):
    """Container image digest information."""

    model_config = {"frozen": True}

    algorithm: str = Field(default="sha256", description="Hash algorithm")
    hash: str = Field(description="The digest hash value")

    def __str__(self) -> str:
        return f"{self.algorithm}:{self.hash}"

    @classmethod
    def from_string(cls, digest: str) -> "ImageDigest":
        """Parse a digest string like 'sha256:abc123...'."""
        if ":" in digest:
            algorithm, hash_value = digest.split(":", 1)
            return cls(algorithm=algorithm, hash=hash_value)
        return cls(hash=digest)


class LayerInfo(BaseModel):
    """Information about a container image layer."""

    model_config = {"frozen": True}

    digest: ImageDigest = Field(description="Layer digest")
    size: int = Field(description="Layer size in bytes")
    media_type: str = Field(description="Layer media type")
    created_by: str | None = Field(default=None, description="Command that created this layer")


class ImageManifest(BaseModel):
    """Container image manifest information."""

    model_config = {"frozen": True}

    schema_version: int = Field(description="Manifest schema version")
    media_type: str = Field(description="Manifest media type")
    digest: ImageDigest = Field(description="Manifest digest")
    config_digest: ImageDigest = Field(description="Config blob digest")
    layers: list[LayerInfo] = Field(default_factory=list, description="Image layers")
    annotations: dict[str, str] = Field(
        default_factory=dict,
        description="OCI annotations",
    )


class ImageMetadata(BaseModel):
    """Comprehensive metadata about a NIM container image."""

    model_config = {"frozen": True}

    # Identity
    reference: str = Field(description="Full image reference (registry/repo:tag)")
    repository: str = Field(description="Repository name")
    tag: str | None = Field(default=None, description="Image tag")
    digest: ImageDigest | None = Field(default=None, description="Image digest")

    # Manifest
    manifest: ImageManifest | None = Field(default=None, description="Image manifest")

    # Labels
    labels: dict[str, str] = Field(default_factory=dict, description="Container labels")

    # Build info
    created: datetime | None = Field(default=None, description="Image creation timestamp")
    architecture: str | None = Field(default=None, description="Target architecture")
    os: str | None = Field(default=None, description="Target operating system")

    # NIM-specific metadata
    nim_version: str | None = Field(default=None, description="NIM version")
    model_name: str | None = Field(default=None, description="Model name")
    model_version: str | None = Field(default=None, description="Model version")
    quantization: str | None = Field(default=None, description="Quantization type (fp16, int8, etc)")

    # Environment
    env: dict[str, str] = Field(default_factory=dict, description="Default environment variables")
    exposed_ports: list[int] = Field(default_factory=list, description="Exposed ports")

    # Entrypoint
    entrypoint: list[str] = Field(default_factory=list, description="Container entrypoint")
    cmd: list[str] = Field(default_factory=list, description="Container command")

    # Raw config for extensibility
    raw_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw container config for additional inspection",
    )

    @property
    def full_reference(self) -> str:
        """Get the full image reference with tag or digest."""
        if self.digest:
            return f"{self.reference}@{self.digest}"
        return self.reference

    @property
    def total_size(self) -> int:
        """Calculate total image size from layers."""
        if self.manifest:
            return sum(layer.size for layer in self.manifest.layers)
        return 0
