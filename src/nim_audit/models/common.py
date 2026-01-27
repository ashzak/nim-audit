"""Common model types shared across modules."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AuditError(BaseModel):
    """Represents an error that occurred during an audit operation."""

    model_config = {"frozen": True}

    code: str = Field(description="Error code for programmatic handling")
    message: str = Field(description="Human-readable error message")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional error context",
    )

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"
