"""OCI registry client implementation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from nim_audit.models.image import ImageDigest, ImageManifest, ImageMetadata, LayerInfo
from nim_audit.registry.base import (
    Registry,
    RegistryAuth,
    RegistryAuthError,
    RegistryError,
    RegistryNotFoundError,
)


class OCIRegistry:
    """Registry client for OCI-compliant container registries.

    Implements the OCI Distribution Specification for interacting
    with container registries like Docker Hub, GHCR, ECR, etc.

    Example:
        registry = OCIRegistry("https://registry-1.docker.io")
        metadata = registry.get_metadata("library/nginx:latest")
    """

    # Well-known registry URLs
    REGISTRY_URLS = {
        "docker.io": "https://registry-1.docker.io",
        "registry-1.docker.io": "https://registry-1.docker.io",
        "ghcr.io": "https://ghcr.io",
        "gcr.io": "https://gcr.io",
        "quay.io": "https://quay.io",
        "nvcr.io": "https://nvcr.io",
    }

    # Media types
    MANIFEST_V2 = "application/vnd.docker.distribution.manifest.v2+json"
    MANIFEST_LIST = "application/vnd.docker.distribution.manifest.list.v2+json"
    OCI_MANIFEST = "application/vnd.oci.image.manifest.v1+json"
    OCI_INDEX = "application/vnd.oci.image.index.v1+json"

    def __init__(
        self,
        base_url: str | None = None,
        auth: RegistryAuth | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize the OCI registry client.

        Args:
            base_url: Base URL of the registry (auto-detected from reference if None)
            auth: Authentication credentials
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self._base_url = base_url
        self._auth = auth or RegistryAuth.from_env()
        self._timeout = timeout
        self._max_retries = max_retries
        self._token_cache: dict[str, str] = {}

    def _get_registry_url(self, registry: str | None) -> str:
        """Get the registry URL for a registry hostname."""
        if not registry:
            return self.REGISTRY_URLS["docker.io"]

        if registry in self.REGISTRY_URLS:
            return self.REGISTRY_URLS[registry]

        # Assume HTTPS for unknown registries
        if not registry.startswith("http"):
            return f"https://{registry}"
        return registry

    def _get_client(self) -> httpx.Client:
        """Create an HTTP client with retry support."""
        transport = httpx.HTTPTransport(retries=self._max_retries)
        return httpx.Client(
            timeout=self._timeout,
            transport=transport,
            follow_redirects=True,
        )

    def _get_token(self, client: httpx.Client, www_authenticate: str, repository: str) -> str:
        """Get a bearer token for authentication.

        Args:
            client: HTTP client
            www_authenticate: WWW-Authenticate header value
            repository: Repository name for scope

        Returns:
            Bearer token
        """
        # Parse WWW-Authenticate header
        # Format: Bearer realm="...",service="...",scope="..."
        params = {}
        for part in www_authenticate.replace("Bearer ", "").split(","):
            if "=" in part:
                key, value = part.split("=", 1)
                params[key.strip()] = value.strip().strip('"')

        realm = params.get("realm")
        if not realm:
            raise RegistryAuthError("No realm in WWW-Authenticate header")

        # Build token request
        token_params = {
            "service": params.get("service", ""),
            "scope": f"repository:{repository}:pull",
        }

        auth = None
        if self._auth:
            if self._auth.token:
                # Use token directly
                return self._auth.token
            elif self._auth.username and self._auth.password:
                auth = (self._auth.username, self._auth.password)

        response = client.get(realm, params=token_params, auth=auth)

        if response.status_code == 401:
            raise RegistryAuthError("Token authentication failed")
        elif response.status_code != 200:
            raise RegistryError(f"Token request failed: {response.status_code}")

        data = response.json()
        return data.get("token") or data.get("access_token", "")

    def _request(
        self,
        client: httpx.Client,
        method: str,
        url: str,
        repository: str,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make an authenticated request to the registry.

        Args:
            client: HTTP client
            method: HTTP method
            url: Request URL
            repository: Repository name (for token scope)
            headers: Additional headers
            **kwargs: Additional request arguments

        Returns:
            HTTP response
        """
        headers = headers or {}

        # Try with cached token first
        cache_key = f"{url}:{repository}"
        if cache_key in self._token_cache:
            headers["Authorization"] = f"Bearer {self._token_cache[cache_key]}"

        response = client.request(method, url, headers=headers, **kwargs)

        # Handle 401 - need to authenticate
        if response.status_code == 401:
            www_auth = response.headers.get("www-authenticate", "")
            if "bearer" in www_auth.lower():
                token = self._get_token(client, www_auth, repository)
                self._token_cache[cache_key] = token
                headers["Authorization"] = f"Bearer {token}"
                response = client.request(method, url, headers=headers, **kwargs)

        return response

    def get_manifest(self, reference: str) -> ImageManifest:
        """Get the manifest for an image.

        Args:
            reference: Image reference (e.g., "nginx:latest")

        Returns:
            The image manifest
        """
        parsed = self._parse_reference(reference)
        registry_url = self._get_registry_url(parsed["registry"])
        repository = parsed["repository"]
        tag = parsed["tag"] or parsed["digest"] or "latest"

        # Handle Docker Hub library images
        if "docker.io" in registry_url and "/" not in repository:
            repository = f"library/{repository}"

        url = f"{registry_url}/v2/{repository}/manifests/{tag}"

        with self._get_client() as client:
            headers = {
                "Accept": ", ".join(
                    [self.MANIFEST_V2, self.OCI_MANIFEST, self.MANIFEST_LIST, self.OCI_INDEX]
                )
            }

            response = self._request(client, "GET", url, repository, headers=headers)

            if response.status_code == 404:
                raise RegistryNotFoundError(reference)
            elif response.status_code == 401:
                raise RegistryAuthError(f"Authentication failed for {reference}")
            elif response.status_code != 200:
                raise RegistryError(f"Failed to get manifest: {response.status_code}")

            data = response.json()
            content_type = response.headers.get("content-type", "")

            # Handle manifest list/index - get first amd64/linux manifest
            if "list" in content_type or "index" in content_type:
                manifests = data.get("manifests", [])
                for m in manifests:
                    platform = m.get("platform", {})
                    if platform.get("architecture") == "amd64" and platform.get("os") == "linux":
                        # Fetch the actual manifest
                        digest = m.get("digest")
                        url = f"{registry_url}/v2/{repository}/manifests/{digest}"
                        response = self._request(
                            client, "GET", url, repository, headers={"Accept": self.MANIFEST_V2}
                        )
                        data = response.json()
                        break

            # Parse manifest
            layers = []
            for layer in data.get("layers", []):
                layers.append(
                    LayerInfo(
                        digest=ImageDigest.from_string(layer.get("digest", "")),
                        size=layer.get("size", 0),
                        media_type=layer.get("mediaType", ""),
                    )
                )

            # Calculate manifest digest
            manifest_bytes = response.content
            manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()

            config_digest_str = data.get("config", {}).get("digest", "")

            return ImageManifest(
                schema_version=data.get("schemaVersion", 2),
                media_type=data.get("mediaType", self.MANIFEST_V2),
                digest=ImageDigest(hash=manifest_digest),
                config_digest=ImageDigest.from_string(config_digest_str)
                if config_digest_str
                else ImageDigest(hash=""),
                layers=layers,
            )

    def get_metadata(self, reference: str) -> ImageMetadata:
        """Get comprehensive metadata for an image.

        Args:
            reference: Image reference

        Returns:
            The image metadata
        """
        parsed = self._parse_reference(reference)
        registry_url = self._get_registry_url(parsed["registry"])
        repository = parsed["repository"]

        # Handle Docker Hub library images
        if "docker.io" in registry_url and "/" not in repository:
            repository = f"library/{repository}"

        # Get manifest first
        manifest = self.get_manifest(reference)

        # Fetch config blob
        config_url = f"{registry_url}/v2/{repository}/blobs/{manifest.config_digest}"

        with self._get_client() as client:
            response = self._request(client, "GET", config_url, repository)

            if response.status_code != 200:
                raise RegistryError(f"Failed to get config blob: {response.status_code}")

            config = response.json()

        # Parse config
        container_config = config.get("config", {})
        labels = container_config.get("Labels", {}) or {}

        # Parse environment
        env_list = container_config.get("Env", []) or []
        env = {}
        for item in env_list:
            if "=" in item:
                key, value = item.split("=", 1)
                env[key] = value

        # Parse exposed ports
        exposed_ports = []
        ports_config = container_config.get("ExposedPorts", {}) or {}
        for port_spec in ports_config.keys():
            import re

            port_match = re.match(r"(\d+)", port_spec)
            if port_match:
                exposed_ports.append(int(port_match.group(1)))

        # Parse creation timestamp
        created = None
        created_str = config.get("created")
        if created_str:
            try:
                from datetime import datetime

                created_str = created_str.replace("Z", "+00:00")
                created = datetime.fromisoformat(created_str[:26] + created_str[-6:])
            except (ValueError, TypeError):
                pass

        # Extract NIM-specific metadata
        nim_version = labels.get("com.nvidia.nim.version")
        model_name = labels.get("com.nvidia.nim.model.name")
        model_version = labels.get("com.nvidia.nim.model.version")
        quantization = labels.get("com.nvidia.nim.model.quantization")

        return ImageMetadata(
            reference=reference,
            repository=parsed["repository"] or reference,
            tag=parsed["tag"],
            digest=manifest.digest,
            manifest=manifest,
            labels=labels,
            created=created,
            architecture=config.get("architecture"),
            os=config.get("os"),
            nim_version=nim_version,
            model_name=model_name,
            model_version=model_version,
            quantization=quantization,
            env=env,
            exposed_ports=exposed_ports,
            entrypoint=container_config.get("Entrypoint", []) or [],
            cmd=container_config.get("Cmd", []) or [],
            raw_config=config,
        )

    def pull_layer(self, reference: str, digest: str, dest: Path) -> None:
        """Download a layer blob to the specified destination.

        Args:
            reference: Image reference
            digest: Layer digest
            dest: Destination path
        """
        parsed = self._parse_reference(reference)
        registry_url = self._get_registry_url(parsed["registry"])
        repository = parsed["repository"]

        if "docker.io" in registry_url and "/" not in repository:
            repository = f"library/{repository}"

        url = f"{registry_url}/v2/{repository}/blobs/{digest}"

        with self._get_client() as client:
            response = self._request(client, "GET", url, repository)

            if response.status_code == 404:
                raise RegistryNotFoundError(f"Layer {digest}")
            elif response.status_code != 200:
                raise RegistryError(f"Failed to pull layer: {response.status_code}")

            dest.write_bytes(response.content)

    def list_tags(self, repository: str) -> list[str]:
        """List all tags for a repository.

        Args:
            repository: Repository name

        Returns:
            List of tag names
        """
        parsed = self._parse_reference(repository)
        registry_url = self._get_registry_url(parsed["registry"])
        repo = parsed["repository"] or repository

        if "docker.io" in registry_url and "/" not in repo:
            repo = f"library/{repo}"

        url = f"{registry_url}/v2/{repo}/tags/list"

        with self._get_client() as client:
            response = self._request(client, "GET", url, repo)

            if response.status_code == 404:
                raise RegistryNotFoundError(repository)
            elif response.status_code != 200:
                raise RegistryError(f"Failed to list tags: {response.status_code}")

            data = response.json()
            return sorted(data.get("tags", []))

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
