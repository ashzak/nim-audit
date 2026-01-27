"""NVIDIA NGC registry client implementation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from nim_audit.models.image import ImageManifest, ImageMetadata
from nim_audit.registry.base import (
    RegistryAuth,
    RegistryAuthError,
    RegistryError,
    RegistryNotFoundError,
)
from nim_audit.registry.oci import OCIRegistry


class NGCRegistry(OCIRegistry):
    """Registry client for NVIDIA NGC (NVIDIA GPU Cloud).

    NGC is NVIDIA's container registry for GPU-optimized containers.
    This client extends the OCI registry client with NGC-specific
    authentication and features.

    NGC requires an API key for authentication. Set the NGC_API_KEY
    environment variable or pass credentials via RegistryAuth.

    Example:
        registry = NGCRegistry()
        metadata = registry.get_metadata("nvcr.io/nim/llama3:1.5.0")
    """

    NGC_REGISTRY_URL = "https://nvcr.io"
    NGC_AUTH_URL = "https://authn.nvidia.com/token"

    def __init__(
        self,
        auth: RegistryAuth | None = None,
        timeout: float = 60.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize the NGC registry client.

        Args:
            auth: Authentication credentials (uses NGC_API_KEY env var if not provided)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        # NGC uses API key as password with $oauthtoken as username
        if auth is None:
            api_key = os.environ.get("NGC_API_KEY") or os.environ.get("NGC_CLI_API_KEY")
            if api_key:
                auth = RegistryAuth(username="$oauthtoken", password=api_key)

        super().__init__(
            base_url=self.NGC_REGISTRY_URL,
            auth=auth,
            timeout=timeout,
            max_retries=max_retries,
        )

    def _get_registry_url(self, registry: str | None) -> str:
        """Get the registry URL - always NGC for this client."""
        return self.NGC_REGISTRY_URL

    def get_metadata(self, reference: str) -> ImageMetadata:
        """Get comprehensive metadata for an NGC image.

        Extends the base implementation with NGC-specific metadata.

        Args:
            reference: Image reference (e.g., "nvcr.io/nim/llama3:1.5.0")

        Returns:
            The image metadata with NGC-specific fields
        """
        metadata = super().get_metadata(reference)

        # Enhance with NGC-specific label parsing
        labels = metadata.labels

        # NGC-specific labels
        ngc_labels = {
            "ngc.model.family": labels.get("com.nvidia.nim.model.family"),
            "ngc.model.variant": labels.get("com.nvidia.nim.model.variant"),
            "ngc.runtime.version": labels.get("com.nvidia.nim.runtime.version"),
            "ngc.cuda.version": labels.get("com.nvidia.cuda.version"),
            "ngc.tensorrt.version": labels.get("com.nvidia.tensorrt.version"),
        }

        # Add NGC metadata to raw_config
        raw_config = dict(metadata.raw_config)
        raw_config["ngc_metadata"] = {k: v for k, v in ngc_labels.items() if v is not None}

        # Return enhanced metadata
        return ImageMetadata(
            reference=metadata.reference,
            repository=metadata.repository,
            tag=metadata.tag,
            digest=metadata.digest,
            manifest=metadata.manifest,
            labels=metadata.labels,
            created=metadata.created,
            architecture=metadata.architecture,
            os=metadata.os,
            nim_version=metadata.nim_version,
            model_name=metadata.model_name,
            model_version=metadata.model_version,
            quantization=metadata.quantization,
            env=metadata.env,
            exposed_ports=metadata.exposed_ports,
            entrypoint=metadata.entrypoint,
            cmd=metadata.cmd,
            raw_config=raw_config,
        )

    def list_nim_images(self) -> list[str]:
        """List available NIM images from NGC.

        Returns:
            List of available NIM image names
        """
        # This would require NGC catalog API, not registry API
        # Return common NIM images for now
        return [
            "nvcr.io/nim/meta/llama3-8b-instruct",
            "nvcr.io/nim/meta/llama3-70b-instruct",
            "nvcr.io/nim/meta/llama-3.1-8b-instruct",
            "nvcr.io/nim/meta/llama-3.1-70b-instruct",
            "nvcr.io/nim/meta/llama-3.1-405b-instruct",
            "nvcr.io/nim/mistralai/mistral-7b-instruct-v0.3",
            "nvcr.io/nim/mistralai/mixtral-8x7b-instruct-v01",
            "nvcr.io/nim/google/gemma-7b",
            "nvcr.io/nim/microsoft/phi-3-mini-128k-instruct",
        ]

    def get_nim_info(self, reference: str) -> dict[str, Any]:
        """Get NIM-specific information about an image.

        Args:
            reference: Image reference

        Returns:
            Dictionary with NIM-specific information
        """
        metadata = self.get_metadata(reference)

        return {
            "reference": metadata.reference,
            "nim_version": metadata.nim_version,
            "model_name": metadata.model_name,
            "model_version": metadata.model_version,
            "quantization": metadata.quantization,
            "architecture": metadata.architecture,
            "cuda_version": metadata.labels.get("com.nvidia.cuda.version"),
            "tensorrt_version": metadata.labels.get("com.nvidia.tensorrt.version"),
            "supported_gpus": metadata.labels.get("com.nvidia.nim.gpu.supported", "").split(","),
            "min_gpu_memory": metadata.labels.get("com.nvidia.nim.gpu.memory_gb"),
            "default_env": {k: v for k, v in metadata.env.items() if k.startswith("NIM_")},
        }

    @classmethod
    def from_environment(cls) -> "NGCRegistry":
        """Create an NGC registry client from environment variables.

        Looks for NGC_API_KEY or NGC_CLI_API_KEY.

        Returns:
            Configured NGCRegistry instance

        Raises:
            RegistryAuthError: If no API key is found
        """
        api_key = os.environ.get("NGC_API_KEY") or os.environ.get("NGC_CLI_API_KEY")
        if not api_key:
            raise RegistryAuthError(
                "NGC API key not found. Set NGC_API_KEY environment variable."
            )

        return cls(auth=RegistryAuth(username="$oauthtoken", password=api_key))
