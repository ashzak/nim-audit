"""Unit tests for the Cache module."""

import json
import time

import pytest

from nim_audit.utils.cache import Cache, get_cache


class TestCache:
    """Tests for Cache class."""

    @pytest.fixture
    def cache(self, tmp_path):
        """Create a cache instance with a temp directory."""
        return Cache(cache_dir=tmp_path / "cache", default_ttl=60, enabled=True)

    @pytest.fixture
    def disabled_cache(self, tmp_path):
        """Create a disabled cache instance."""
        return Cache(cache_dir=tmp_path / "cache", enabled=False)

    def test_cache_init_creates_directory(self, tmp_path):
        """Test that cache initialization creates the cache directory."""
        cache_dir = tmp_path / "test_cache"
        cache = Cache(cache_dir=cache_dir, enabled=True)
        assert cache_dir.exists()

    def test_cache_set_get_basic(self, cache):
        """Test basic set and get operations."""
        cache.set("key1", {"data": "value"})
        result = cache.get("key1")
        assert result == {"data": "value"}

    def test_cache_get_nonexistent_returns_default(self, cache):
        """Test that getting nonexistent key returns default."""
        assert cache.get("nonexistent") is None
        assert cache.get("nonexistent", "default") == "default"

    def test_cache_set_with_custom_ttl(self, cache):
        """Test setting a value with custom TTL."""
        cache.set("key1", "value1", ttl=1)
        assert cache.get("key1") == "value1"

    def test_cache_expiration(self, cache):
        """Test that cache entries expire."""
        cache.set("key1", "value1", ttl=1)
        assert cache.get("key1") == "value1"
        time.sleep(1.5)
        assert cache.get("key1") is None

    def test_cache_delete(self, cache):
        """Test deleting a cache entry."""
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_cache_delete_nonexistent(self, cache):
        """Test deleting nonexistent key doesn't raise."""
        cache.delete("nonexistent")  # Should not raise

    def test_cache_clear(self, cache):
        """Test clearing all cache entries."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_cache_disabled_set_noop(self, disabled_cache):
        """Test that set does nothing when cache is disabled."""
        disabled_cache.set("key1", "value1")
        assert disabled_cache.get("key1") is None

    def test_cache_disabled_get_returns_default(self, disabled_cache):
        """Test that get returns default when cache is disabled."""
        assert disabled_cache.get("key1") is None
        assert disabled_cache.get("key1", "default") == "default"

    def test_cache_enabled_property(self, cache, disabled_cache):
        """Test the enabled property."""
        assert cache.enabled is True
        assert disabled_cache.enabled is False

        cache.enabled = False
        assert cache.enabled is False

    def test_cache_memory_layer(self, cache):
        """Test that values are cached in memory."""
        cache.set("key1", "value1")

        # Access should use memory cache
        result = cache.get("key1")
        assert result == "value1"
        assert "key1" in cache._memory_cache

    def test_cache_file_persistence(self, tmp_path):
        """Test that values are persisted to file."""
        cache_dir = tmp_path / "cache"
        cache1 = Cache(cache_dir=cache_dir, default_ttl=3600)
        cache1.set("key1", "value1")

        # Create new cache instance to bypass memory cache
        cache2 = Cache(cache_dir=cache_dir, default_ttl=3600)
        result = cache2.get("key1")
        assert result == "value1"

    def test_cache_stats(self, cache):
        """Test cache statistics."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        stats = cache.get_stats()
        assert stats["enabled"] is True
        assert stats["memory_entries"] == 2
        assert stats["file_entries"] == 2
        assert stats["total_size_bytes"] > 0

    def test_cache_stats_disabled(self, disabled_cache):
        """Test stats when cache is disabled."""
        stats = disabled_cache.get_stats()
        assert stats["enabled"] is False
        assert stats["memory_entries"] == 0

    def test_cache_decorator_basic(self, cache):
        """Test the @cached decorator."""
        call_count = 0

        @cache.cached(ttl=60)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call - should execute function
        assert expensive_function(5) == 10
        assert call_count == 1

        # Second call - should use cache
        assert expensive_function(5) == 10
        assert call_count == 1

        # Different argument - should execute function
        assert expensive_function(10) == 20
        assert call_count == 2

    def test_cache_decorator_with_kwargs(self, cache):
        """Test decorator with keyword arguments."""
        call_count = 0

        @cache.cached(ttl=60)
        def func_with_kwargs(x, y=1):
            nonlocal call_count
            call_count += 1
            return x + y

        assert func_with_kwargs(5, y=3) == 8
        assert call_count == 1

        # Same arguments - use cache
        assert func_with_kwargs(5, y=3) == 8
        assert call_count == 1

        # Different kwargs - execute function
        assert func_with_kwargs(5, y=4) == 9
        assert call_count == 2

    def test_cache_decorator_custom_key_func(self, cache):
        """Test decorator with custom key function."""
        call_count = 0

        @cache.cached(ttl=60, key_func=lambda x, y: f"custom:{x}")
        def func(x, y):
            nonlocal call_count
            call_count += 1
            return x + y

        # First call
        assert func(5, 10) == 15
        assert call_count == 1

        # Same x, different y - should use cache (key only depends on x)
        assert func(5, 20) == 15
        assert call_count == 1

        # Different x - execute function
        assert func(10, 5) == 15
        assert call_count == 2

    def test_cache_decorator_disabled(self, disabled_cache):
        """Test decorator when cache is disabled."""
        call_count = 0

        @disabled_cache.cached(ttl=60)
        def func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        assert func(5) == 10
        assert call_count == 1

        # Should call function again (no caching)
        assert func(5) == 10
        assert call_count == 2

    def test_cache_handles_invalid_json_file(self, cache, tmp_path):
        """Test that cache handles corrupted cache files gracefully."""
        # Write invalid JSON to cache file
        cache.set("key1", "value1")
        cache_file = cache._key_to_path("key1")
        cache_file.write_text("invalid json")

        # Clear memory cache
        cache._memory_cache.clear()

        # Should return default, not raise
        assert cache.get("key1") is None

    def test_get_cache_singleton(self):
        """Test that get_cache returns a singleton."""
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2
