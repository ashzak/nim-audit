"""Tokenizer extractor for NIM containers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nim_audit.extractors.base import ExtractorResult
from nim_audit.models.common import AuditError
from nim_audit.utils.hashing import hash_file


class TokenizerExtractor:
    """Extractor for tokenizer files from NIM containers.

    Extracts tokenizer configuration, vocabulary, and special tokens
    from NIM containers.

    Example:
        extractor = TokenizerExtractor()
        result = extractor.extract("nvcr.io/nim/llama3:1.5.0")
        print(result.data["vocab_size"])
    """

    # Tokenizer file patterns
    TOKENIZER_FILES = [
        "tokenizer.json",
        "tokenizer_config.json",
        "tokenizer.model",
        "vocab.json",
        "vocab.txt",
        "merges.txt",
        "special_tokens_map.json",
        "added_tokens.json",
        "spiece.model",
    ]

    # Common tokenizer directories
    TOKENIZER_DIRS = [
        "/opt/nim/models",
        "/models",
        "/workspace/models",
        "/home/nim/models",
    ]

    @property
    def name(self) -> str:
        """Unique name for this extractor."""
        return "tokenizer"

    @property
    def description(self) -> str:
        """Human-readable description."""
        return "Extracts tokenizer files, vocabulary, and special tokens configuration"

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
        """Extract tokenizer information from the image.

        Args:
            image_id: Image identifier
            container_fs: Optional path to extracted container filesystem

        Returns:
            ExtractorResult with tokenizer information
        """
        try:
            data: dict[str, Any] = {
                "tokenizer_files": [],
                "tokenizer_type": None,
                "vocab_size": None,
                "special_tokens": {},
                "tokenizer_config": None,
                "bos_token": None,
                "eos_token": None,
                "pad_token": None,
                "unk_token": None,
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
                        code="TOKENIZER_EXTRACTION_ERROR",
                        message=f"Failed to extract tokenizer info: {e}",
                        details={"image_id": image_id},
                    )
                ],
            )

    def _extract_from_fs(self, container_fs: Path) -> dict[str, Any]:
        """Extract tokenizer info from a filesystem path."""
        data: dict[str, Any] = {
            "tokenizer_files": [],
            "tokenizer_type": None,
            "vocab_size": None,
            "special_tokens": {},
            "tokenizer_config": None,
            "bos_token": None,
            "eos_token": None,
            "pad_token": None,
            "unk_token": None,
        }

        # Search for tokenizer files
        for tokenizer_dir in self.TOKENIZER_DIRS:
            dir_path = container_fs / tokenizer_dir.lstrip("/")
            if dir_path.exists():
                self._scan_directory(dir_path, data)

        return data

    def _extract_from_image(self, image_id: str) -> dict[str, Any]:
        """Extract tokenizer info by inspecting image."""
        data: dict[str, Any] = {
            "tokenizer_files": [],
            "tokenizer_type": None,
            "vocab_size": None,
            "special_tokens": {},
            "tokenizer_config": None,
            "bos_token": None,
            "eos_token": None,
            "pad_token": None,
            "unk_token": None,
        }

        try:
            import docker

            client = docker.from_env()
            container = client.containers.create(image_id, command="sleep 1")

            try:
                for tokenizer_dir in self.TOKENIZER_DIRS:
                    for tokenizer_file in self.TOKENIZER_FILES:
                        file_path = f"{tokenizer_dir}/{tokenizer_file}"
                        exit_code, content = container.exec_run(f"cat {file_path} 2>/dev/null")

                        if exit_code == 0 and content:
                            data["tokenizer_files"].append(file_path)

                            # Parse JSON files
                            if tokenizer_file.endswith(".json"):
                                try:
                                    file_data = json.loads(content.decode())
                                    self._process_tokenizer_file(tokenizer_file, file_data, data)
                                except json.JSONDecodeError:
                                    pass
            finally:
                container.remove(force=True)

        except ImportError:
            pass
        except Exception:
            pass

        return data

    def _scan_directory(self, dir_path: Path, data: dict[str, Any]) -> None:
        """Scan a directory for tokenizer files."""
        for path in dir_path.rglob("*"):
            if path.is_file() and path.name in self.TOKENIZER_FILES:
                file_info = {
                    "path": str(path),
                    "size": path.stat().st_size,
                    "hash": hash_file(path)[:16],
                }
                data["tokenizer_files"].append(file_info)

                # Parse JSON files
                if path.suffix == ".json":
                    try:
                        file_data = json.loads(path.read_text())
                        self._process_tokenizer_file(path.name, file_data, data)
                    except (json.JSONDecodeError, OSError):
                        pass

    def _process_tokenizer_file(
        self,
        filename: str,
        file_data: dict[str, Any],
        data: dict[str, Any],
    ) -> None:
        """Process a tokenizer file and extract information."""
        if filename == "tokenizer_config.json":
            data["tokenizer_config"] = file_data
            data["tokenizer_type"] = file_data.get("tokenizer_class")
            data["bos_token"] = self._extract_token(file_data.get("bos_token"))
            data["eos_token"] = self._extract_token(file_data.get("eos_token"))
            data["pad_token"] = self._extract_token(file_data.get("pad_token"))
            data["unk_token"] = self._extract_token(file_data.get("unk_token"))

        elif filename == "tokenizer.json":
            # HuggingFace tokenizers format
            if "model" in file_data:
                model = file_data["model"]
                if "vocab" in model:
                    data["vocab_size"] = len(model["vocab"])

            # Get added tokens
            if "added_tokens" in file_data:
                for token in file_data["added_tokens"]:
                    if isinstance(token, dict) and "content" in token:
                        data["special_tokens"][token["content"]] = token.get("id")

        elif filename == "special_tokens_map.json":
            data["special_tokens"].update(file_data)

        elif filename == "vocab.json":
            data["vocab_size"] = len(file_data)

    @staticmethod
    def _extract_token(token_data: Any) -> str | None:
        """Extract token string from various formats."""
        if token_data is None:
            return None
        if isinstance(token_data, str):
            return token_data
        if isinstance(token_data, dict):
            return token_data.get("content")
        return str(token_data)
