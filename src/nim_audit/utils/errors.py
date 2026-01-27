"""Error handling utilities for nim-audit."""

from __future__ import annotations

import functools
import time
from typing import Any, Callable, TypeVar

from nim_audit.models.common import AuditError

T = TypeVar("T")


class NimAuditError(Exception):
    """Base exception for nim-audit."""

    def __init__(self, message: str, code: str = "UNKNOWN_ERROR", details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_audit_error(self) -> AuditError:
        """Convert to AuditError model."""
        return AuditError(code=self.code, message=self.message, details=self.details)


class ImageNotFoundError(NimAuditError):
    """Image was not found."""

    def __init__(self, reference: str):
        super().__init__(
            f"Image not found: {reference}",
            code="IMAGE_NOT_FOUND",
            details={"reference": reference},
        )


class AuthenticationError(NimAuditError):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, code="AUTH_ERROR")


class ValidationError(NimAuditError):
    """Validation failed."""

    def __init__(self, message: str, field: str | None = None):
        details = {"field": field} if field else {}
        super().__init__(message, code="VALIDATION_ERROR", details=details)


class ConfigurationError(NimAuditError):
    """Configuration error."""

    def __init__(self, message: str, config_key: str | None = None):
        details = {"config_key": config_key} if config_key else {}
        super().__init__(message, code="CONFIG_ERROR", details=details)


class NetworkError(NimAuditError):
    """Network operation failed."""

    def __init__(self, message: str, url: str | None = None):
        details = {"url": url} if url else {}
        super().__init__(message, code="NETWORK_ERROR", details=details)


class TimeoutError(NimAuditError):
    """Operation timed out."""

    def __init__(self, message: str = "Operation timed out", timeout: float | None = None):
        details = {"timeout": timeout} if timeout else {}
        super().__init__(message, code="TIMEOUT_ERROR", details=details)


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to retry a function on failure.

    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff

            if last_exception:
                raise last_exception
            raise RuntimeError("Retry failed without exception")

        return wrapper

    return decorator


def validate_image_reference(reference: str) -> None:
    """Validate an image reference string.

    Args:
        reference: Image reference to validate

    Raises:
        ValidationError: If reference is invalid
    """
    if not reference:
        raise ValidationError("Image reference cannot be empty", field="reference")

    if reference.startswith("-"):
        raise ValidationError("Image reference cannot start with '-'", field="reference")

    # Check for invalid characters
    invalid_chars = set("<>|\"'\\")
    for char in invalid_chars:
        if char in reference:
            raise ValidationError(
                f"Image reference contains invalid character: {char}",
                field="reference",
            )

    # Basic structure validation
    parts = reference.split("/")
    if len(parts) > 10:
        raise ValidationError("Image reference has too many path components", field="reference")


def validate_env_var_name(name: str) -> None:
    """Validate an environment variable name.

    Args:
        name: Environment variable name to validate

    Raises:
        ValidationError: If name is invalid
    """
    if not name:
        raise ValidationError("Environment variable name cannot be empty", field="name")

    if not name[0].isalpha() and name[0] != "_":
        raise ValidationError(
            "Environment variable name must start with a letter or underscore",
            field="name",
        )

    for char in name:
        if not (char.isalnum() or char == "_"):
            raise ValidationError(
                f"Environment variable name contains invalid character: {char}",
                field="name",
            )


def safe_get(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Safely get a nested value from a dictionary.

    Args:
        data: Dictionary to get value from
        *keys: Keys to traverse
        default: Default value if key not found

    Returns:
        Value at the nested key path, or default
    """
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
            if current is None:
                return default
        else:
            return default
    return current
