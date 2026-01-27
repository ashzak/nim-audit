"""Unit tests for the errors module."""

import time
from unittest.mock import MagicMock

import pytest

from nim_audit.utils.errors import (
    AuthenticationError,
    ConfigurationError,
    ImageNotFoundError,
    NetworkError,
    NimAuditError,
    TimeoutError,
    ValidationError,
    retry,
    safe_get,
    validate_env_var_name,
    validate_image_reference,
)


class TestNimAuditError:
    """Tests for base NimAuditError."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = NimAuditError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.code == "UNKNOWN_ERROR"
        assert error.details == {}

    def test_error_with_code_and_details(self):
        """Test error with custom code and details."""
        error = NimAuditError(
            "Test error",
            code="TEST_ERROR",
            details={"key": "value"},
        )
        assert error.code == "TEST_ERROR"
        assert error.details == {"key": "value"}

    def test_to_audit_error(self):
        """Test conversion to AuditError model."""
        error = NimAuditError(
            "Test error",
            code="TEST_ERROR",
            details={"key": "value"},
        )
        audit_error = error.to_audit_error()

        assert audit_error.code == "TEST_ERROR"
        assert audit_error.message == "Test error"
        assert audit_error.details == {"key": "value"}


class TestImageNotFoundError:
    """Tests for ImageNotFoundError."""

    def test_error_message(self):
        """Test error message includes reference."""
        error = ImageNotFoundError("nvcr.io/nim/llama3:latest")
        assert "nvcr.io/nim/llama3:latest" in str(error)
        assert error.code == "IMAGE_NOT_FOUND"
        assert error.details["reference"] == "nvcr.io/nim/llama3:latest"


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_default_message(self):
        """Test default error message."""
        error = AuthenticationError()
        assert "Authentication failed" in str(error)
        assert error.code == "AUTH_ERROR"

    def test_custom_message(self):
        """Test custom error message."""
        error = AuthenticationError("Invalid token")
        assert str(error) == "Invalid token"


class TestValidationError:
    """Tests for ValidationError."""

    def test_basic_error(self):
        """Test basic validation error."""
        error = ValidationError("Invalid value")
        assert str(error) == "Invalid value"
        assert error.code == "VALIDATION_ERROR"

    def test_error_with_field(self):
        """Test validation error with field."""
        error = ValidationError("Must be positive", field="count")
        assert error.details["field"] == "count"


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_basic_error(self):
        """Test basic configuration error."""
        error = ConfigurationError("Invalid setting")
        assert error.code == "CONFIG_ERROR"

    def test_error_with_config_key(self):
        """Test error with config key."""
        error = ConfigurationError("Invalid value", config_key="cache.ttl")
        assert error.details["config_key"] == "cache.ttl"


class TestNetworkError:
    """Tests for NetworkError."""

    def test_basic_error(self):
        """Test basic network error."""
        error = NetworkError("Connection refused")
        assert error.code == "NETWORK_ERROR"

    def test_error_with_url(self):
        """Test error with URL."""
        error = NetworkError("Failed to connect", url="https://example.com")
        assert error.details["url"] == "https://example.com"


class TestTimeoutError:
    """Tests for TimeoutError."""

    def test_default_message(self):
        """Test default timeout message."""
        error = TimeoutError()
        assert "timed out" in str(error)
        assert error.code == "TIMEOUT_ERROR"

    def test_error_with_timeout(self):
        """Test error with timeout value."""
        error = TimeoutError("Request timed out", timeout=30.0)
        assert error.details["timeout"] == 30.0


class TestRetryDecorator:
    """Tests for retry decorator."""

    def test_retry_succeeds_first_time(self):
        """Test that successful function doesn't retry."""
        call_count = 0

        @retry(max_attempts=3, delay=0.01)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_failure(self):
        """Test retry on failure."""
        call_count = 0

        @retry(max_attempts=3, delay=0.01)
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"

        result = failing_func()
        assert result == "success"
        assert call_count == 3

    def test_retry_exhausted(self):
        """Test that exception is raised after max attempts."""
        call_count = 0

        @retry(max_attempts=3, delay=0.01)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_fails()

        assert call_count == 3

    def test_retry_specific_exceptions(self):
        """Test retry only catches specified exceptions."""
        call_count = 0

        @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        def fails_with_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("Wrong type")

        # Should not retry TypeError
        with pytest.raises(TypeError):
            fails_with_type_error()

        assert call_count == 1

    def test_retry_backoff(self):
        """Test exponential backoff."""
        call_count = 0
        timestamps = []

        @retry(max_attempts=3, delay=0.05, backoff=2.0)
        def fails_twice():
            nonlocal call_count
            call_count += 1
            timestamps.append(time.time())
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"

        result = fails_twice()
        assert result == "success"
        assert call_count == 3

        # Check delays (with some tolerance)
        delay1 = timestamps[1] - timestamps[0]
        delay2 = timestamps[2] - timestamps[1]

        assert delay1 >= 0.04  # First delay ~0.05
        assert delay2 >= 0.08  # Second delay ~0.10 (backoff)


class TestValidateImageReference:
    """Tests for validate_image_reference."""

    def test_valid_references(self):
        """Test valid image references."""
        valid_refs = [
            "nginx",
            "nginx:latest",
            "library/nginx",
            "docker.io/library/nginx",
            "nvcr.io/nim/llama3:1.5.0",
            "localhost:5000/myimage:tag",
            "gcr.io/project/image@sha256:abc123",
        ]
        for ref in valid_refs:
            validate_image_reference(ref)  # Should not raise

    def test_empty_reference(self):
        """Test empty reference raises error."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_image_reference("")

    def test_reference_starts_with_dash(self):
        """Test reference starting with dash raises error."""
        with pytest.raises(ValidationError, match="cannot start with"):
            validate_image_reference("-invalid")

    def test_reference_with_invalid_chars(self):
        """Test reference with invalid characters raises error."""
        invalid_refs = [
            "image<tag",
            "image>tag",
            'image"tag',
            "image'tag",
            "image|tag",
            "image\\tag",
        ]
        for ref in invalid_refs:
            with pytest.raises(ValidationError, match="invalid character"):
                validate_image_reference(ref)

    def test_reference_too_many_components(self):
        """Test reference with too many path components."""
        long_ref = "/".join(["a"] * 15)
        with pytest.raises(ValidationError, match="too many"):
            validate_image_reference(long_ref)


class TestValidateEnvVarName:
    """Tests for validate_env_var_name."""

    def test_valid_names(self):
        """Test valid environment variable names."""
        valid_names = [
            "FOO",
            "BAR_BAZ",
            "_PRIVATE",
            "MY_VAR_123",
            "a",
            "A1",
        ]
        for name in valid_names:
            validate_env_var_name(name)  # Should not raise

    def test_empty_name(self):
        """Test empty name raises error."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_env_var_name("")

    def test_name_starts_with_number(self):
        """Test name starting with number raises error."""
        with pytest.raises(ValidationError, match="must start with"):
            validate_env_var_name("1VAR")

    def test_name_with_invalid_chars(self):
        """Test name with invalid characters raises error."""
        invalid_names = [
            "FOO-BAR",
            "FOO.BAR",
            "FOO BAR",
            "FOO@BAR",
        ]
        for name in invalid_names:
            with pytest.raises(ValidationError, match="invalid character"):
                validate_env_var_name(name)


class TestSafeGet:
    """Tests for safe_get function."""

    def test_simple_get(self):
        """Test simple key access."""
        data = {"key": "value"}
        assert safe_get(data, "key") == "value"

    def test_nested_get(self):
        """Test nested key access."""
        data = {"level1": {"level2": {"level3": "value"}}}
        assert safe_get(data, "level1", "level2", "level3") == "value"

    def test_missing_key_returns_default(self):
        """Test missing key returns default."""
        data = {"key": "value"}
        assert safe_get(data, "nonexistent") is None
        assert safe_get(data, "nonexistent", default="default") == "default"

    def test_missing_nested_key_returns_default(self):
        """Test missing nested key returns default."""
        data = {"level1": {"level2": "value"}}
        assert safe_get(data, "level1", "level3") is None
        assert safe_get(data, "level1", "level2", "level3") is None

    def test_non_dict_in_path_returns_default(self):
        """Test non-dict value in path returns default."""
        data = {"key": "string_value"}
        assert safe_get(data, "key", "nested") is None

    def test_empty_keys(self):
        """Test with no keys returns data."""
        data = {"key": "value"}
        assert safe_get(data) == data
