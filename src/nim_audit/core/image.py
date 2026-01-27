"""NIMImage class for container inspection."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from nim_audit.models.common import AuditError
from nim_audit.models.image import ImageDigest, ImageManifest, ImageMetadata, LayerInfo


class NIMImage:
    """Represents a NIM container image for inspection.

    This class provides methods to load and inspect NIM container images
    from various sources (local Docker daemon, remote registries).

    Example:
        # From registry
        image = NIMImage.from_registry("nvcr.io/nim/llama3:1.5.0")

        # From local Docker
        image = NIMImage.from_local("nvcr.io/nim/llama3:1.5.0")

        # Access metadata
        print(image.metadata.nim_version)
        print(image.metadata.model_name)
    """

    def __init__(self, metadata: ImageMetadata) -> None:
        """Initialize with image metadata.

        Args:
            metadata: The image metadata
        """
        self._metadata = metadata
        self._extracted_fs: Path | None = None

    @property
    def metadata(self) -> ImageMetadata:
        """Get the image metadata."""
        return self._metadata

    @property
    def reference(self) -> str:
        """Get the image reference."""
        return self._metadata.reference

    @property
    def tag(self) -> str | None:
        """Get the image tag."""
        return self._metadata.tag

    @property
    def digest(self) -> ImageDigest | None:
        """Get the image digest."""
        return self._metadata.digest

    @classmethod
    def from_registry(
        cls,
        reference: str,
        auth: dict[str, str] | None = None,
    ) -> "NIMImage":
        """Load an image from a container registry.

        Args:
            reference: Image reference (e.g., "nvcr.io/nim/llama3:1.5.0")
            auth: Optional authentication credentials

        Returns:
            NIMImage instance

        Raises:
            ValueError: If the reference is invalid
        """
        parsed = cls._parse_reference(reference)
        metadata = cls._fetch_registry_metadata(reference, auth)
        return cls(metadata)

    @classmethod
    def from_local(cls, reference: str) -> "NIMImage":
        """Load an image from the local Docker daemon.

        Args:
            reference: Image reference or ID

        Returns:
            NIMImage instance

        Raises:
            ValueError: If the image is not found locally
        """
        metadata = cls._fetch_local_metadata(reference)
        return cls(metadata)

    @classmethod
    def from_metadata(cls, metadata: ImageMetadata) -> "NIMImage":
        """Create an image from existing metadata.

        Args:
            metadata: Pre-existing image metadata

        Returns:
            NIMImage instance
        """
        return cls(metadata)

    @staticmethod
    def _parse_reference(reference: str) -> dict[str, str | None]:
        """Parse an image reference into components.

        Args:
            reference: Image reference string

        Returns:
            Dict with registry, repository, tag, and digest
        """
        result: dict[str, str | None] = {
            "registry": None,
            "repository": None,
            "tag": None,
            "digest": None,
        }

        # Handle digest
        if "@" in reference:
            ref_part, digest = reference.rsplit("@", 1)
            result["digest"] = digest
            reference = ref_part

        # Handle tag
        if ":" in reference:
            # Check if it's a port or a tag
            parts = reference.rsplit(":", 1)
            if "/" in parts[1] or parts[1].isdigit():
                # It's a port number, not a tag
                pass
            else:
                reference = parts[0]
                result["tag"] = parts[1]

        # Handle registry and repository
        parts = reference.split("/")
        if len(parts) == 1:
            # Just a repository name (e.g., "ubuntu")
            result["repository"] = parts[0]
        elif len(parts) == 2:
            # Could be registry/repo or namespace/repo
            if "." in parts[0] or ":" in parts[0] or parts[0] == "localhost":
                result["registry"] = parts[0]
                result["repository"] = parts[1]
            else:
                result["repository"] = reference
        else:
            # registry/namespace/repo or registry/namespace/.../repo
            result["registry"] = parts[0]
            result["repository"] = "/".join(parts[1:])

        return result

    @staticmethod
    def _fetch_registry_metadata(
        reference: str,
        auth: dict[str, str] | None = None,
    ) -> ImageMetadata:
        """Fetch metadata from a container registry.

        This is a placeholder implementation. In production, this would
        use the OCI registry API or Docker registry API.
        """
        parsed = NIMImage._parse_reference(reference)

        # For now, return placeholder metadata
        # Real implementation would fetch from registry
        return ImageMetadata(
            reference=reference,
            repository=parsed.get("repository") or reference,
            tag=parsed.get("tag"),
            digest=ImageDigest.from_string(parsed["digest"]) if parsed.get("digest") else None,
            labels={},
            env={},
        )

    @staticmethod
    def _fetch_local_metadata(reference: str) -> ImageMetadata:
        """Fetch metadata from local Docker daemon.

        This implementation uses the Docker SDK to inspect images.
        """
        try:
            import docker

            client = docker.from_env()
            image = client.images.get(reference)
            config = image.attrs

            # Parse labels
            labels = config.get("Config", {}).get("Labels", {}) or {}

            # Parse environment variables
            env_list = config.get("Config", {}).get("Env", []) or []
            env = {}
            for item in env_list:
                if "=" in item:
                    key, value = item.split("=", 1)
                    env[key] = value

            # Parse exposed ports
            exposed_ports = []
            ports_config = config.get("Config", {}).get("ExposedPorts", {}) or {}
            for port_spec in ports_config.keys():
                port_match = re.match(r"(\d+)", port_spec)
                if port_match:
                    exposed_ports.append(int(port_match.group(1)))

            # Parse creation timestamp
            created = None
            created_str = config.get("Created")
            if created_str:
                try:
                    # Handle both formats: with and without fractional seconds
                    created_str = created_str.replace("Z", "+00:00")
                    if "." in created_str:
                        # Truncate fractional seconds to 6 digits
                        parts = created_str.split(".")
                        frac_and_tz = parts[1]
                        # Find where timezone starts
                        tz_start = -1
                        for i, c in enumerate(frac_and_tz):
                            if c in "+-":
                                tz_start = i
                                break
                        if tz_start > 0:
                            frac = frac_and_tz[:tz_start][:6]
                            tz = frac_and_tz[tz_start:]
                            created_str = f"{parts[0]}.{frac}{tz}"
                    created = datetime.fromisoformat(created_str)
                except (ValueError, TypeError):
                    pass

            # Build manifest from layer info
            layers = []
            for layer_digest in image.attrs.get("RootFS", {}).get("Layers", []):
                layers.append(
                    LayerInfo(
                        digest=ImageDigest.from_string(layer_digest),
                        size=0,  # Size not available from this API
                        media_type="application/vnd.docker.image.rootfs.diff.tar.gzip",
                    )
                )

            manifest = None
            if layers:
                manifest = ImageManifest(
                    schema_version=2,
                    media_type="application/vnd.docker.distribution.manifest.v2+json",
                    digest=ImageDigest(hash=image.id.replace("sha256:", "")),
                    config_digest=ImageDigest(hash=image.id.replace("sha256:", "")),
                    layers=layers,
                )

            # Extract NIM-specific metadata from labels
            nim_version = labels.get("com.nvidia.nim.version")
            model_name = labels.get("com.nvidia.nim.model.name")
            model_version = labels.get("com.nvidia.nim.model.version")
            quantization = labels.get("com.nvidia.nim.model.quantization")

            parsed = NIMImage._parse_reference(reference)

            return ImageMetadata(
                reference=reference,
                repository=parsed.get("repository") or reference,
                tag=parsed.get("tag"),
                digest=ImageDigest(hash=image.id.replace("sha256:", "")),
                manifest=manifest,
                labels=labels,
                created=created,
                architecture=config.get("Architecture"),
                os=config.get("Os"),
                nim_version=nim_version,
                model_name=model_name,
                model_version=model_version,
                quantization=quantization,
                env=env,
                exposed_ports=exposed_ports,
                entrypoint=config.get("Config", {}).get("Entrypoint", []) or [],
                cmd=config.get("Config", {}).get("Cmd", []) or [],
                raw_config=config,
            )

        except ImportError:
            raise RuntimeError("Docker SDK not available. Install with: pip install docker")
        except Exception as e:
            raise ValueError(f"Failed to load image '{reference}': {e}")

    def __repr__(self) -> str:
        return f"NIMImage(reference='{self.reference}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NIMImage):
            return NotImplemented
        # Compare by digest if available, otherwise by reference
        if self.digest and other.digest:
            return self.digest == other.digest
        return self.reference == other.reference
