"""Base registry protocol and types."""

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from nim_audit.models.image import ImageManifest, ImageMetadata


class RegistryAuth(BaseModel):
    """Authentication credentials for a container registry."""

    model_config = {"frozen": True}

    username: str | None = Field(default=None, description="Registry username")
    password: str | None = Field(default=None, description="Registry password or token")
    token: str | None = Field(default=None, description="Bearer token")

    @classmethod
    def from_env(cls) -> "RegistryAuth | None":
        """Create auth from environment variables.

        Looks for REGISTRY_USERNAME and REGISTRY_PASSWORD,
        or REGISTRY_TOKEN for token auth.
        """
        import os

        username = os.environ.get("REGISTRY_USERNAME")
        password = os.environ.get("REGISTRY_PASSWORD")
        token = os.environ.get("REGISTRY_TOKEN")

        if token:
            return cls(token=token)
        if username and password:
            return cls(username=username, password=password)
        return None


class RegistryError(Exception):
    """Base exception for registry operations."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


class RegistryAuthError(RegistryError):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, code="AUTH_ERROR")


class RegistryNotFoundError(RegistryError):
    """Image or manifest not found."""

    def __init__(self, reference: str) -> None:
        super().__init__(f"Image not found: {reference}", code="NOT_FOUND")
        self.reference = reference


@runtime_checkable
class Registry(Protocol):
    """Protocol for container registry clients.

    Registry clients are responsible for interacting with container
    registries to fetch manifests, metadata, and image layers.

    To implement a custom registry client:
    1. Create a class that implements this protocol
    2. Handle authentication appropriately for your registry

    Example:
        class MyRegistry:
            def __init__(self, base_url: str, auth: RegistryAuth | None = None):
                self.base_url = base_url
                self.auth = auth

            def get_manifest(self, reference: str) -> ImageManifest:
                # Fetch and parse manifest
                ...

            def get_metadata(self, reference: str) -> ImageMetadata:
                # Fetch and parse metadata
                ...

            def pull_layer(self, reference: str, digest: str, dest: Path) -> None:
                # Download layer to destination
                ...
    """

    def get_manifest(self, reference: str) -> ImageManifest:
        """Get the manifest for an image.

        Args:
            reference: Image reference (e.g., "nvcr.io/nim/llama3:1.5.0")

        Returns:
            The image manifest

        Raises:
            RegistryNotFoundError: If image not found
            RegistryAuthError: If authentication fails
            RegistryError: For other errors
        """
        ...

    def get_metadata(self, reference: str) -> ImageMetadata:
        """Get comprehensive metadata for an image.

        Args:
            reference: Image reference (e.g., "nvcr.io/nim/llama3:1.5.0")

        Returns:
            The image metadata

        Raises:
            RegistryNotFoundError: If image not found
            RegistryAuthError: If authentication fails
            RegistryError: For other errors
        """
        ...

    def pull_layer(self, reference: str, digest: str, dest: "Path") -> None:
        """Download a layer blob to the specified destination.

        Args:
            reference: Image reference
            digest: Layer digest
            dest: Destination path for the downloaded layer

        Raises:
            RegistryNotFoundError: If layer not found
            RegistryAuthError: If authentication fails
            RegistryError: For other errors
        """
        ...

    def list_tags(self, repository: str) -> list[str]:
        """List all tags for a repository.

        Args:
            repository: Repository name (e.g., "nvcr.io/nim/llama3")

        Returns:
            List of tag names

        Raises:
            RegistryNotFoundError: If repository not found
            RegistryAuthError: If authentication fails
            RegistryError: For other errors
        """
        ...


# Import Path for type hints
from pathlib import Path
