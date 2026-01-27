"""Model artifact extractor for NIM containers."""

from __future__ import annotations

import json
import tarfile
import tempfile
from pathlib import Path
from typing import Any

from nim_audit.extractors.base import ExtractorResult
from nim_audit.models.common import AuditError
from nim_audit.utils.hashing import hash_file


class ModelExtractor:
    """Extractor for model artifacts from NIM containers.

    Extracts information about model weights, configuration files,
    and quantization settings from NIM containers.

    Example:
        extractor = ModelExtractor()
        result = extractor.extract("nvcr.io/nim/llama3:1.5.0")
        print(result.data["model_files"])
    """

    # Common model file patterns
    MODEL_FILE_PATTERNS = [
        "*.safetensors",
        "*.bin",
        "*.pt",
        "*.pth",
        "*.gguf",
        "*.onnx",
        "model.safetensors.index.json",
        "pytorch_model.bin.index.json",
    ]

    # Model config files
    CONFIG_FILES = [
        "config.json",
        "model_config.json",
        "generation_config.json",
        "quantization_config.json",
    ]

    # Common model directories in NIM containers
    MODEL_DIRS = [
        "/opt/nim/models",
        "/models",
        "/workspace/models",
        "/home/nim/models",
    ]

    @property
    def name(self) -> str:
        """Unique name for this extractor."""
        return "model"

    @property
    def description(self) -> str:
        """Human-readable description."""
        return "Extracts model weights, configuration, and quantization information"

    def can_extract(self, image_id: str) -> bool:
        """Check if this extractor can handle the given image.

        Args:
            image_id: Image identifier

        Returns:
            True for NIM images
        """
        # Check if it's a NIM image
        return "nim" in image_id.lower() or "nvcr.io" in image_id.lower()

    def extract(
        self,
        image_id: str,
        container_fs: Path | None = None,
    ) -> ExtractorResult:
        """Extract model information from the image.

        Args:
            image_id: Image identifier
            container_fs: Optional path to extracted container filesystem

        Returns:
            ExtractorResult with model information
        """
        try:
            data: dict[str, Any] = {
                "model_files": [],
                "config_files": {},
                "total_model_size": 0,
                "quantization_info": None,
                "model_format": None,
            }

            if container_fs and container_fs.exists():
                # Extract from filesystem
                data = self._extract_from_fs(container_fs)
            else:
                # Extract from image layers
                data = self._extract_from_image(image_id)

            return ExtractorResult.ok(self.name, data)

        except Exception as e:
            return ExtractorResult.fail(
                self.name,
                [
                    AuditError(
                        code="MODEL_EXTRACTION_ERROR",
                        message=f"Failed to extract model info: {e}",
                        details={"image_id": image_id},
                    )
                ],
            )

    def _extract_from_fs(self, container_fs: Path) -> dict[str, Any]:
        """Extract model info from a filesystem path."""
        data: dict[str, Any] = {
            "model_files": [],
            "config_files": {},
            "total_model_size": 0,
            "quantization_info": None,
            "model_format": None,
        }

        # Search for model directories
        for model_dir in self.MODEL_DIRS:
            dir_path = container_fs / model_dir.lstrip("/")
            if dir_path.exists():
                self._scan_directory(dir_path, data)

        # Determine model format
        if data["model_files"]:
            extensions = {Path(f["path"]).suffix for f in data["model_files"]}
            if ".safetensors" in extensions:
                data["model_format"] = "safetensors"
            elif ".gguf" in extensions:
                data["model_format"] = "gguf"
            elif ".onnx" in extensions:
                data["model_format"] = "onnx"
            elif ".bin" in extensions or ".pt" in extensions:
                data["model_format"] = "pytorch"

        return data

    def _extract_from_image(self, image_id: str) -> dict[str, Any]:
        """Extract model info by inspecting image layers."""
        data: dict[str, Any] = {
            "model_files": [],
            "config_files": {},
            "total_model_size": 0,
            "quantization_info": None,
            "model_format": None,
        }

        try:
            import docker

            client = docker.from_env()
            image = client.images.get(image_id)

            # Create a temporary container to inspect
            container = client.containers.create(image_id, command="sleep 1")

            try:
                # Get file listing from container
                for model_dir in self.MODEL_DIRS:
                    try:
                        # Try to list files in model directory
                        exit_code, output = container.exec_run(
                            f"find {model_dir} -type f 2>/dev/null || true"
                        )
                        if exit_code == 0 and output:
                            files = output.decode().strip().split("\n")
                            for f in files:
                                if f:
                                    # Check if it's a model file
                                    for pattern in self.MODEL_FILE_PATTERNS:
                                        if self._matches_pattern(f, pattern):
                                            data["model_files"].append(
                                                {
                                                    "path": f,
                                                    "size": 0,  # Can't get size without extracting
                                                }
                                            )
                                            break

                                    # Check for config files
                                    for config_name in self.CONFIG_FILES:
                                        if f.endswith(config_name):
                                            # Try to read config
                                            exit_code, content = container.exec_run(f"cat {f}")
                                            if exit_code == 0:
                                                try:
                                                    data["config_files"][config_name] = json.loads(
                                                        content.decode()
                                                    )
                                                except json.JSONDecodeError:
                                                    pass
                    except Exception:
                        continue
            finally:
                container.remove(force=True)

            # Extract quantization info from config
            if "quantization_config.json" in data["config_files"]:
                data["quantization_info"] = data["config_files"]["quantization_config.json"]
            elif "config.json" in data["config_files"]:
                config = data["config_files"]["config.json"]
                if "quantization_config" in config:
                    data["quantization_info"] = config["quantization_config"]

        except ImportError:
            pass  # Docker not available
        except Exception:
            pass  # Best effort extraction

        return data

    def _scan_directory(self, dir_path: Path, data: dict[str, Any]) -> None:
        """Scan a directory for model files."""
        for path in dir_path.rglob("*"):
            if path.is_file():
                # Check model files
                for pattern in self.MODEL_FILE_PATTERNS:
                    if self._matches_pattern(str(path), pattern):
                        file_info = {
                            "path": str(path),
                            "size": path.stat().st_size,
                            "hash": hash_file(path)[:16] if path.stat().st_size < 100_000_000 else None,
                        }
                        data["model_files"].append(file_info)
                        data["total_model_size"] += path.stat().st_size
                        break

                # Check config files
                for config_name in self.CONFIG_FILES:
                    if path.name == config_name:
                        try:
                            data["config_files"][config_name] = json.loads(path.read_text())
                        except (json.JSONDecodeError, OSError):
                            pass

    @staticmethod
    def _matches_pattern(path: str, pattern: str) -> bool:
        """Check if a path matches a glob pattern."""
        import fnmatch

        return fnmatch.fnmatch(Path(path).name, pattern)
