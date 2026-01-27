"""Runtime configuration extractor for NIM containers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from nim_audit.extractors.base import ExtractorResult
from nim_audit.models.common import AuditError


class RuntimeExtractor:
    """Extractor for runtime configuration from NIM containers.

    Extracts configuration files, startup scripts, and default
    settings from NIM containers.

    Example:
        extractor = RuntimeExtractor()
        result = extractor.extract("nvcr.io/nim/llama3:1.5.0")
        print(result.data["config_files"])
    """

    # Configuration file patterns
    CONFIG_FILES = [
        "config.yaml",
        "config.yml",
        "config.json",
        "nim_config.yaml",
        "nim_config.json",
        "runtime_config.yaml",
        "model_config.yaml",
        "serving_config.yaml",
    ]

    # Configuration directories
    CONFIG_DIRS = [
        "/opt/nim",
        "/opt/nim/config",
        "/etc/nim",
        "/app/config",
        "/workspace/config",
    ]

    # Startup scripts
    STARTUP_SCRIPTS = [
        "/opt/nim/start.sh",
        "/opt/nim/entrypoint.sh",
        "/entrypoint.sh",
        "/start.sh",
        "/run.sh",
    ]

    @property
    def name(self) -> str:
        """Unique name for this extractor."""
        return "runtime"

    @property
    def description(self) -> str:
        """Human-readable description."""
        return "Extracts runtime configuration files and startup settings"

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
        """Extract runtime configuration from the image.

        Args:
            image_id: Image identifier
            container_fs: Optional path to extracted container filesystem

        Returns:
            ExtractorResult with runtime configuration
        """
        try:
            data: dict[str, Any] = {
                "config_files": {},
                "startup_scripts": [],
                "environment_defaults": {},
                "resource_limits": {},
                "health_check": None,
                "volumes": [],
                "working_dir": None,
                "user": None,
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
                        code="RUNTIME_EXTRACTION_ERROR",
                        message=f"Failed to extract runtime config: {e}",
                        details={"image_id": image_id},
                    )
                ],
            )

    def _extract_from_fs(self, container_fs: Path) -> dict[str, Any]:
        """Extract runtime config from a filesystem path."""
        data = self._default_data()

        # Search for config files
        for config_dir in self.CONFIG_DIRS:
            dir_path = container_fs / config_dir.lstrip("/")
            if dir_path.exists():
                self._scan_config_dir(dir_path, data)

        # Search for startup scripts
        for script_path in self.STARTUP_SCRIPTS:
            file_path = container_fs / script_path.lstrip("/")
            if file_path.exists():
                data["startup_scripts"].append(
                    {
                        "path": script_path,
                        "content_preview": self._get_script_preview(file_path),
                    }
                )

        return data

    def _extract_from_image(self, image_id: str) -> dict[str, Any]:
        """Extract runtime config by inspecting image."""
        data = self._default_data()

        try:
            import docker

            client = docker.from_env()
            image = client.images.get(image_id)
            config = image.attrs.get("Config", {})

            # Extract environment defaults
            env_list = config.get("Env", []) or []
            for item in env_list:
                if "=" in item:
                    key, value = item.split("=", 1)
                    if key.startswith("NIM_") or key.startswith("NVIDIA_"):
                        data["environment_defaults"][key] = value

            # Extract other config
            data["working_dir"] = config.get("WorkingDir")
            data["user"] = config.get("User")

            # Check for healthcheck
            healthcheck = config.get("Healthcheck")
            if healthcheck:
                data["health_check"] = {
                    "test": healthcheck.get("Test"),
                    "interval": healthcheck.get("Interval"),
                    "timeout": healthcheck.get("Timeout"),
                    "retries": healthcheck.get("Retries"),
                }

            # Check for volumes
            volumes = config.get("Volumes")
            if volumes:
                data["volumes"] = list(volumes.keys())

            # Try to extract config files from container
            container = client.containers.create(image_id, command="sleep 1")

            try:
                for config_dir in self.CONFIG_DIRS:
                    for config_file in self.CONFIG_FILES:
                        file_path = f"{config_dir}/{config_file}"
                        exit_code, content = container.exec_run(f"cat {file_path} 2>/dev/null")

                        if exit_code == 0 and content:
                            try:
                                if config_file.endswith((".yaml", ".yml")):
                                    data["config_files"][file_path] = yaml.safe_load(
                                        content.decode()
                                    )
                                elif config_file.endswith(".json"):
                                    data["config_files"][file_path] = json.loads(content.decode())
                            except (yaml.YAMLError, json.JSONDecodeError):
                                data["config_files"][file_path] = content.decode()[:500]

                # Check startup scripts
                for script_path in self.STARTUP_SCRIPTS:
                    exit_code, content = container.exec_run(f"head -20 {script_path} 2>/dev/null")
                    if exit_code == 0 and content:
                        data["startup_scripts"].append(
                            {
                                "path": script_path,
                                "content_preview": content.decode()[:500],
                            }
                        )
            finally:
                container.remove(force=True)

        except ImportError:
            pass
        except Exception:
            pass

        return data

    def _default_data(self) -> dict[str, Any]:
        """Get default data structure."""
        return {
            "config_files": {},
            "startup_scripts": [],
            "environment_defaults": {},
            "resource_limits": {},
            "health_check": None,
            "volumes": [],
            "working_dir": None,
            "user": None,
        }

    def _scan_config_dir(self, dir_path: Path, data: dict[str, Any]) -> None:
        """Scan a directory for config files."""
        for config_file in self.CONFIG_FILES:
            file_path = dir_path / config_file
            if file_path.exists():
                try:
                    if config_file.endswith((".yaml", ".yml")):
                        data["config_files"][str(file_path)] = yaml.safe_load(
                            file_path.read_text()
                        )
                    elif config_file.endswith(".json"):
                        data["config_files"][str(file_path)] = json.loads(file_path.read_text())
                except (yaml.YAMLError, json.JSONDecodeError, OSError):
                    pass

    def _get_script_preview(self, script_path: Path) -> str:
        """Get a preview of a script file."""
        try:
            lines = script_path.read_text().split("\n")[:20]
            return "\n".join(lines)
        except OSError:
            return ""
