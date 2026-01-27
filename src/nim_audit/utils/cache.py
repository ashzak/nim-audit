"""Caching utilities for nim-audit."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class Cache:
    """Simple file-based cache for nim-audit.

    Caches expensive operations like image metadata fetching
    to speed up repeated audits.

    Example:
        cache = Cache()

        # Cache a value
        cache.set("key", {"data": "value"}, ttl=3600)

        # Get cached value
        value = cache.get("key")

        # Use decorator
        @cache.cached(ttl=3600)
        def expensive_operation(arg):
            return compute(arg)
    """

    def __init__(
        self,
        cache_dir: Path | str | None = None,
        default_ttl: int = 3600,
        enabled: bool = True,
    ) -> None:
        """Initialize the cache.

        Args:
            cache_dir: Directory for cache files. Defaults to ~/.cache/nim-audit
            default_ttl: Default time-to-live in seconds
            enabled: Whether caching is enabled
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "nim-audit"
        self._cache_dir = Path(cache_dir)
        self._default_ttl = default_ttl
        self._enabled = enabled
        self._memory_cache: dict[str, tuple[Any, float]] = {}

        # Create cache directory if it doesn't exist
        if self._enabled:
            self._cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def enabled(self) -> bool:
        """Whether caching is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable or disable caching."""
        self._enabled = value

    def _key_to_path(self, key: str) -> Path:
        """Convert a cache key to a file path."""
        # Hash the key to create a safe filename
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:32]
        return self._cache_dir / f"{key_hash}.json"

    def get(self, key: str, default: T | None = None) -> T | None:
        """Get a value from the cache.

        Args:
            key: Cache key
            default: Default value if not found or expired

        Returns:
            Cached value or default
        """
        if not self._enabled:
            return default

        # Check memory cache first
        if key in self._memory_cache:
            value, expires_at = self._memory_cache[key]
            if time.time() < expires_at:
                return value
            else:
                del self._memory_cache[key]

        # Check file cache
        cache_file = self._key_to_path(key)
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                if time.time() < data.get("expires_at", 0):
                    value = data["value"]
                    # Store in memory cache for faster access
                    self._memory_cache[key] = (value, data["expires_at"])
                    return value
                else:
                    # Expired - delete the file
                    cache_file.unlink(missing_ok=True)
            except (json.JSONDecodeError, KeyError, OSError):
                pass

        return default

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds. Uses default if not specified.
        """
        if not self._enabled:
            return

        if ttl is None:
            ttl = self._default_ttl

        expires_at = time.time() + ttl

        # Store in memory cache
        self._memory_cache[key] = (value, expires_at)

        # Store in file cache
        cache_file = self._key_to_path(key)
        try:
            data = {
                "key": key,
                "value": value,
                "expires_at": expires_at,
                "created_at": time.time(),
            }
            cache_file.write_text(json.dumps(data, default=str))
        except (OSError, TypeError):
            pass

    def delete(self, key: str) -> None:
        """Delete a value from the cache.

        Args:
            key: Cache key to delete
        """
        # Remove from memory cache
        self._memory_cache.pop(key, None)

        # Remove from file cache
        cache_file = self._key_to_path(key)
        cache_file.unlink(missing_ok=True)

    def clear(self) -> None:
        """Clear all cached values."""
        self._memory_cache.clear()

        if self._cache_dir.exists():
            for cache_file in self._cache_dir.glob("*.json"):
                cache_file.unlink(missing_ok=True)

    def cached(
        self,
        ttl: int | None = None,
        key_func: Callable[..., str] | None = None,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """Decorator to cache function results.

        Args:
            ttl: Time-to-live in seconds
            key_func: Function to generate cache key from arguments

        Returns:
            Decorated function
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            def wrapper(*args: Any, **kwargs: Any) -> T:
                if not self._enabled:
                    return func(*args, **kwargs)

                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    # Default key generation
                    key_parts = [func.__module__, func.__name__]
                    key_parts.extend(str(arg) for arg in args)
                    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    cache_key = ":".join(key_parts)

                # Check cache
                result = self.get(cache_key)
                if result is not None:
                    return result

                # Call function and cache result
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                return result

            return wrapper

        return decorator

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        file_count = 0
        total_size = 0

        if self._cache_dir.exists():
            for cache_file in self._cache_dir.glob("*.json"):
                file_count += 1
                total_size += cache_file.stat().st_size

        return {
            "enabled": self._enabled,
            "cache_dir": str(self._cache_dir),
            "memory_entries": len(self._memory_cache),
            "file_entries": file_count,
            "total_size_bytes": total_size,
        }


# Global cache instance
_default_cache: Cache | None = None


def get_cache() -> Cache:
    """Get the default cache instance.

    Returns:
        Default Cache instance
    """
    global _default_cache
    if _default_cache is None:
        _default_cache = Cache()
    return _default_cache
