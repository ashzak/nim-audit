"""Docker registry client implementation."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from nim_audit.models.image import ImageDigest, ImageManifest, ImageMetadata, LayerInfo
from nim_audit.registry.base import (
    Registry,
    RegistryAuth,
    RegistryAuthError,
    RegistryError,
    RegistryNotFoundError,
)


class DockerRegistry:
    """Registry client for local Docker daemon.

    This client uses the Docker SDK to interact with the local
    Docker daemon for image inspection and layer access.

    Example:
        registry = DockerRegistry()
        metadata = registry.get_metadata("nginx:latest")
        print(metadata.labels)
    """

    def __init__(self, auth: RegistryAuth | None = None) -> None:
        """Initialize the Docker registry client.

        Args:
            auth: Optional authentication (not used for local daemon)
        """
        self._auth = auth
        self._client: Any = None

    @property
    def client(self) -> Any:
        """Get the Docker client, creating it if necessary."""
        if self._client is None:
            try:
                import docker

                self._client = docker.from_env()
            except ImportError:
                raise RegistryError(
                    "Docker SDK not available. Install with: pip install docker",
                    code="MISSING_DEPENDENCY",
                )
            except Exception as e:
                raise RegistryError(
                    f"Failed to connect to Docker daemon: {e}",
                    code="CONNECTION_ERROR",
                )
        return self._client

    def get_manifest(self, reference: str) -> ImageManifest:
        """Get the manifest for an image.

        Args:
            reference: Image reference (e.g., "nginx:latest")

        Returns:
            The image manifest

        Raises:
            RegistryNotFoundError: If image not found
            RegistryError: For other errors
        """
        try:
            image = self.client.images.get(reference)
            attrs = image.attrs

            # Build layers from RootFS
            layers = []
            for layer_digest in attrs.get("RootFS", {}).get("Layers", []):
                layers.append(
                    LayerInfo(
                        digest=ImageDigest.from_string(layer_digest),
                        size=0,  # Size not available from this API
                        media_type="application/vnd.docker.image.rootfs.diff.tar.gzip",
                    )
                )

            return ImageManifest(
                schema_version=2,
                media_type="application/vnd.docker.distribution.manifest.v2+json",
                digest=ImageDigest(hash=image.id.replace("sha256:", "")),
                config_digest=ImageDigest(hash=image.id.replace("sha256:", "")),
                layers=layers,
            )

        except Exception as e:
            if "not found" in str(e).lower() or "no such image" in str(e).lower():
                raise RegistryNotFoundError(reference)
            raise RegistryError(f"Failed to get manifest: {e}")

    def get_metadata(self, reference: str) -> ImageMetadata:
        """Get comprehensive metadata for an image.

        Args:
            reference: Image reference (e.g., "nginx:latest")

        Returns:
            The image metadata

        Raises:
            RegistryNotFoundError: If image not found
            RegistryError: For other errors
        """
        try:
            image = self.client.images.get(reference)
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
            created = self._parse_timestamp(config.get("Created"))

            # Get manifest
            manifest = self.get_manifest(reference)

            # Parse reference
            parsed = self._parse_reference(reference)

            # Extract NIM-specific metadata from labels
            nim_version = labels.get("com.nvidia.nim.version")
            model_name = labels.get("com.nvidia.nim.model.name")
            model_version = labels.get("com.nvidia.nim.model.version")
            quantization = labels.get("com.nvidia.nim.model.quantization")

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

        except RegistryNotFoundError:
            raise
        except RegistryError:
            raise
        except Exception as e:
            if "not found" in str(e).lower() or "no such image" in str(e).lower():
                raise RegistryNotFoundError(reference)
            raise RegistryError(f"Failed to get metadata: {e}")

    def pull_layer(self, reference: str, digest: str, dest: Path) -> None:
        """Download a layer blob to the specified destination.

        For local Docker daemon, this extracts the layer from the image.

        Args:
            reference: Image reference
            digest: Layer digest
            dest: Destination path for the downloaded layer

        Raises:
            RegistryNotFoundError: If layer not found
            RegistryError: For other errors
        """
        try:
            image = self.client.images.get(reference)

            # Export image and extract the specific layer
            # This is a simplified implementation
            import tarfile
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tmp:
                tmp_path = tmp.name

            try:
                # Export the entire image
                with open(tmp_path, "wb") as f:
                    for chunk in image.save():
                        f.write(chunk)

                # Extract the specific layer
                with tarfile.open(tmp_path, "r") as tar:
                    # Find the layer file
                    layer_file = None
                    for member in tar.getmembers():
                        if digest.replace("sha256:", "") in member.name and member.name.endswith(
                            "/layer.tar"
                        ):
                            layer_file = member
                            break

                    if layer_file:
                        extracted = tar.extractfile(layer_file)
                        if extracted:
                            dest.write_bytes(extracted.read())
                    else:
                        raise RegistryNotFoundError(f"Layer {digest} not found in image")
            finally:
                Path(tmp_path).unlink(missing_ok=True)

        except RegistryNotFoundError:
            raise
        except Exception as e:
            raise RegistryError(f"Failed to pull layer: {e}")

    def list_tags(self, repository: str) -> list[str]:
        """List all tags for a repository.

        For local Docker daemon, this lists local image tags.

        Args:
            repository: Repository name

        Returns:
            List of tag names
        """
        try:
            images = self.client.images.list(name=repository)
            tags = []
            for image in images:
                for tag in image.tags:
                    if ":" in tag:
                        _, tag_name = tag.rsplit(":", 1)
                        tags.append(tag_name)
                    else:
                        tags.append(tag)
            return sorted(set(tags))
        except Exception as e:
            raise RegistryError(f"Failed to list tags: {e}")

    def image_exists(self, reference: str) -> bool:
        """Check if an image exists locally.

        Args:
            reference: Image reference

        Returns:
            True if image exists
        """
        try:
            self.client.images.get(reference)
            return True
        except Exception:
            return False

    def pull_image(self, reference: str) -> None:
        """Pull an image from a remote registry.

        Args:
            reference: Image reference

        Raises:
            RegistryAuthError: If authentication fails
            RegistryError: For other errors
        """
        try:
            auth_config = None
            if self._auth:
                auth_config = {
                    "username": self._auth.username,
                    "password": self._auth.password,
                }

            self.client.images.pull(reference, auth_config=auth_config)

        except Exception as e:
            err_str = str(e).lower()
            if "unauthorized" in err_str or "authentication" in err_str:
                raise RegistryAuthError(f"Authentication failed for {reference}")
            raise RegistryError(f"Failed to pull image: {e}")

    @staticmethod
    def _parse_reference(reference: str) -> dict[str, str | None]:
        """Parse an image reference into components."""
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
            parts = reference.rsplit(":", 1)
            if "/" not in parts[1] and not parts[1].isdigit():
                reference = parts[0]
                result["tag"] = parts[1]

        # Handle registry and repository
        parts = reference.split("/")
        if len(parts) == 1:
            result["repository"] = parts[0]
        elif len(parts) == 2:
            if "." in parts[0] or ":" in parts[0] or parts[0] == "localhost":
                result["registry"] = parts[0]
                result["repository"] = parts[1]
            else:
                result["repository"] = reference
        else:
            result["registry"] = parts[0]
            result["repository"] = "/".join(parts[1:])

        return result

    @staticmethod
    def _parse_timestamp(timestamp: str | None) -> datetime | None:
        """Parse a Docker timestamp string."""
        if not timestamp:
            return None

        try:
            # Handle ISO format with timezone
            timestamp = timestamp.replace("Z", "+00:00")
            if "." in timestamp:
                # Truncate fractional seconds to 6 digits
                parts = timestamp.split(".")
                frac_and_tz = parts[1]
                tz_start = -1
                for i, c in enumerate(frac_and_tz):
                    if c in "+-":
                        tz_start = i
                        break
                if tz_start > 0:
                    frac = frac_and_tz[:tz_start][:6]
                    tz = frac_and_tz[tz_start:]
                    timestamp = f"{parts[0]}.{frac}{tz}"
            return datetime.fromisoformat(timestamp)
        except (ValueError, TypeError):
            return None
