"""Consistent hashing utilities for artifacts."""

import hashlib
import json
from pathlib import Path
from typing import Any


def compute_hash(data: bytes, algorithm: str = "sha256") -> str:
    """Compute hash of bytes data.

    Args:
        data: Bytes to hash
        algorithm: Hash algorithm to use

    Returns:
        Hex digest of the hash
    """
    hasher = hashlib.new(algorithm)
    hasher.update(data)
    return hasher.hexdigest()


def hash_file(path: Path | str, algorithm: str = "sha256", chunk_size: int = 8192) -> str:
    """Compute hash of a file.

    Args:
        path: Path to the file
        algorithm: Hash algorithm to use
        chunk_size: Size of chunks to read

    Returns:
        Hex digest of the file hash
    """
    hasher = hashlib.new(algorithm)
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def hash_dict(data: dict[str, Any], algorithm: str = "sha256") -> str:
    """Compute hash of a dictionary.

    The dictionary is serialized to JSON with sorted keys for consistency.

    Args:
        data: Dictionary to hash
        algorithm: Hash algorithm to use

    Returns:
        Hex digest of the hash
    """
    serialized = json.dumps(data, sort_keys=True, default=str)
    return compute_hash(serialized.encode("utf-8"), algorithm)


def short_hash(data: bytes | str, length: int = 12) -> str:
    """Compute a short hash for display purposes.

    Args:
        data: Data to hash
        length: Length of the short hash

    Returns:
        Truncated hex digest
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    full_hash = compute_hash(data)
    return full_hash[:length]
