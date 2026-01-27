"""Structured logging utilities."""

import logging
import sys
from typing import Any


class StructuredFormatter(logging.Formatter):
    """Formatter that outputs structured log messages."""

    def format(self, record: logging.LogRecord) -> str:
        # Add extra fields if present
        extra = ""
        if hasattr(record, "extra_fields"):
            fields = getattr(record, "extra_fields")
            if fields:
                extra = " " + " ".join(f"{k}={v}" for k, v in fields.items())

        # Format the base message
        message = super().format(record)
        return f"{message}{extra}"


def configure_logging(
    level: str = "INFO",
    format_string: str | None = None,
    structured: bool = False,
) -> None:
    """Configure logging for nim-audit.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string
        structured: Use structured logging format
    """
    if format_string is None:
        if structured:
            format_string = "%(asctime)s %(levelname)s %(name)s %(message)s"
        else:
            format_string = "%(levelname)s: %(message)s"

    handler = logging.StreamHandler(sys.stderr)

    if structured:
        handler.setFormatter(StructuredFormatter(format_string))
    else:
        handler.setFormatter(logging.Formatter(format_string))

    # Configure root logger for nim_audit
    logger = logging.getLogger("nim_audit")
    logger.setLevel(getattr(logging, level.upper()))
    logger.handlers = [handler]
    logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a nim-audit module.

    Args:
        name: Module name (will be prefixed with nim_audit)

    Returns:
        Configured logger
    """
    if not name.startswith("nim_audit"):
        name = f"nim_audit.{name}"
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds extra fields to log messages."""

    def process(
        self, msg: str, kwargs: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        # Add extra fields to the record
        extra = kwargs.get("extra", {})
        extra["extra_fields"] = self.extra
        kwargs["extra"] = extra
        return msg, kwargs


def get_logger_with_context(name: str, **context: Any) -> LoggerAdapter:
    """Get a logger with additional context fields.

    Args:
        name: Module name
        **context: Context fields to include in all log messages

    Returns:
        LoggerAdapter with context
    """
    logger = get_logger(name)
    return LoggerAdapter(logger, context)
