"""API schema extractor for NIM containers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nim_audit.extractors.base import ExtractorResult
from nim_audit.models.common import AuditError


class APIExtractor:
    """Extractor for OpenAPI schemas from NIM containers.

    Extracts API schema information including endpoints, parameters,
    and response types from NIM containers.

    Example:
        extractor = APIExtractor()
        result = extractor.extract("nvcr.io/nim/llama3:1.5.0")
        print(result.data["endpoints"])
    """

    # Common API schema locations
    SCHEMA_PATHS = [
        "/opt/nim/openapi.json",
        "/opt/nim/api/openapi.json",
        "/app/openapi.json",
        "/openapi.json",
        "/swagger.json",
    ]

    # NIM standard endpoints
    NIM_ENDPOINTS = [
        "/v1/chat/completions",
        "/v1/completions",
        "/v1/embeddings",
        "/v1/models",
        "/health",
        "/metrics",
    ]

    @property
    def name(self) -> str:
        """Unique name for this extractor."""
        return "api"

    @property
    def description(self) -> str:
        """Human-readable description."""
        return "Extracts OpenAPI schema and endpoint information"

    def can_extract(self, image_id: str) -> bool:
        """Check if this extractor can handle the given image.

        Args:
            image_id: Image identifier

        Returns:
            True for NIM images
        """
        return "nim" in image_id.lower() or "nvcr.io" in image_id.lower()

    def extract(
        self,
        image_id: str,
        container_fs: Path | None = None,
    ) -> ExtractorResult:
        """Extract API schema from the image.

        Args:
            image_id: Image identifier
            container_fs: Optional path to extracted container filesystem

        Returns:
            ExtractorResult with API information
        """
        try:
            data: dict[str, Any] = {
                "openapi_version": None,
                "api_version": None,
                "title": None,
                "endpoints": [],
                "schemas": {},
                "has_chat_completions": False,
                "has_completions": False,
                "has_embeddings": False,
                "supported_parameters": {},
            }

            if container_fs and container_fs.exists():
                data = self._extract_from_fs(container_fs)
            else:
                data = self._extract_from_image(image_id)

            return ExtractorResult.ok(self.name, data)

        except Exception as e:
            return ExtractorResult.fail(
                self.name,
                [
                    AuditError(
                        code="API_EXTRACTION_ERROR",
                        message=f"Failed to extract API info: {e}",
                        details={"image_id": image_id},
                    )
                ],
            )

    def _extract_from_fs(self, container_fs: Path) -> dict[str, Any]:
        """Extract API info from a filesystem path."""
        data = self._default_data()

        # Search for OpenAPI schema
        for schema_path in self.SCHEMA_PATHS:
            file_path = container_fs / schema_path.lstrip("/")
            if file_path.exists():
                try:
                    schema = json.loads(file_path.read_text())
                    self._process_schema(schema, data)
                    break
                except (json.JSONDecodeError, OSError):
                    continue

        return data

    def _extract_from_image(self, image_id: str) -> dict[str, Any]:
        """Extract API info by inspecting image."""
        data = self._default_data()

        try:
            import docker

            client = docker.from_env()
            container = client.containers.create(image_id, command="sleep 1")

            try:
                for schema_path in self.SCHEMA_PATHS:
                    exit_code, content = container.exec_run(f"cat {schema_path} 2>/dev/null")

                    if exit_code == 0 and content:
                        try:
                            schema = json.loads(content.decode())
                            self._process_schema(schema, data)
                            break
                        except json.JSONDecodeError:
                            continue
            finally:
                container.remove(force=True)

        except ImportError:
            pass
        except Exception:
            pass

        # If no schema found, provide default NIM endpoints
        if not data["endpoints"]:
            data["endpoints"] = self.NIM_ENDPOINTS
            data["has_chat_completions"] = True
            data["has_completions"] = True

        return data

    def _default_data(self) -> dict[str, Any]:
        """Get default data structure."""
        return {
            "openapi_version": None,
            "api_version": None,
            "title": None,
            "endpoints": [],
            "schemas": {},
            "has_chat_completions": False,
            "has_completions": False,
            "has_embeddings": False,
            "supported_parameters": {},
        }

    def _process_schema(self, schema: dict[str, Any], data: dict[str, Any]) -> None:
        """Process an OpenAPI schema."""
        # Basic info
        data["openapi_version"] = schema.get("openapi") or schema.get("swagger")
        info = schema.get("info", {})
        data["api_version"] = info.get("version")
        data["title"] = info.get("title")

        # Extract paths/endpoints
        paths = schema.get("paths", {})
        for path, methods in paths.items():
            data["endpoints"].append(path)

            # Check for specific endpoints
            if "/chat/completions" in path:
                data["has_chat_completions"] = True
                self._extract_parameters(methods, "chat_completions", data)
            elif "/completions" in path and "chat" not in path:
                data["has_completions"] = True
                self._extract_parameters(methods, "completions", data)
            elif "/embeddings" in path:
                data["has_embeddings"] = True
                self._extract_parameters(methods, "embeddings", data)

        # Extract component schemas
        components = schema.get("components", {})
        schemas = components.get("schemas", {})

        # Store key schemas
        for name, schema_def in schemas.items():
            if any(
                keyword in name.lower()
                for keyword in ["request", "response", "completion", "message", "choice"]
            ):
                data["schemas"][name] = self._simplify_schema(schema_def)

    def _extract_parameters(
        self,
        methods: dict[str, Any],
        endpoint_type: str,
        data: dict[str, Any],
    ) -> None:
        """Extract supported parameters from endpoint definition."""
        params = []

        for method, definition in methods.items():
            if method.lower() not in ("get", "post", "put", "patch", "delete"):
                continue

            # Get request body schema
            request_body = definition.get("requestBody", {})
            content = request_body.get("content", {})

            for media_type, media_def in content.items():
                if "json" in media_type:
                    schema = media_def.get("schema", {})
                    properties = schema.get("properties", {})
                    required = schema.get("required", [])

                    for prop_name, prop_def in properties.items():
                        param_info = {
                            "name": prop_name,
                            "type": prop_def.get("type"),
                            "required": prop_name in required,
                            "default": prop_def.get("default"),
                            "description": prop_def.get("description"),
                        }
                        params.append(param_info)

        data["supported_parameters"][endpoint_type] = params

    def _simplify_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Simplify a schema for storage."""
        simplified = {
            "type": schema.get("type"),
        }

        if "properties" in schema:
            simplified["properties"] = list(schema["properties"].keys())

        if "required" in schema:
            simplified["required"] = schema["required"]

        if "enum" in schema:
            simplified["enum"] = schema["enum"]

        return simplified
