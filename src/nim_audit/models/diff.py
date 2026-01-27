"""Diff-related data models."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from nim_audit.models.common import AuditError
from nim_audit.models.image import ImageMetadata


class ChangeType(str, Enum):
    """Type of change detected."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class ChangeCategory(str, Enum):
    """Category of the changed artifact."""

    METADATA = "metadata"
    MODEL = "model"
    TOKENIZER = "tokenizer"
    API = "api"
    RUNTIME = "runtime"
    LAYER = "layer"
    CONFIG = "config"
    ENVIRONMENT = "environment"


class Severity(str, Enum):
    """Severity level of a change."""

    INFO = "info"
    WARNING = "warning"
    BREAKING = "breaking"


class DiffEntry(BaseModel):
    """A single difference entry between two images."""

    model_config = {"frozen": True}

    category: ChangeCategory = Field(description="Category of the changed item")
    change_type: ChangeType = Field(description="Type of change")
    path: str = Field(description="Path or identifier of the changed item")
    old_value: str | None = Field(default=None, description="Previous value")
    new_value: str | None = Field(default=None, description="New value")
    severity: Severity = Field(default=Severity.INFO, description="Change severity")
    description: str = Field(default="", description="Human-readable description")


class BreakingChange(BaseModel):
    """A breaking change that may affect compatibility."""

    model_config = {"frozen": True}

    category: ChangeCategory = Field(description="Category of the breaking change")
    title: str = Field(description="Short title of the breaking change")
    description: str = Field(description="Detailed description")
    impact: str = Field(description="Expected impact on users")
    migration: str | None = Field(default=None, description="Migration guidance")
    related_entries: list[str] = Field(
        default_factory=list,
        description="Paths of related diff entries",
    )


class DiffReport(BaseModel):
    """Complete diff report between two images."""

    model_config = {"frozen": True}

    # Images compared
    source_image: ImageMetadata = Field(description="Source (old) image metadata")
    target_image: ImageMetadata = Field(description="Target (new) image metadata")

    # Timestamp
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Report generation timestamp",
    )

    # Changes
    entries: list[DiffEntry] = Field(default_factory=list, description="All diff entries")
    breaking_changes: list[BreakingChange] = Field(
        default_factory=list,
        description="Detected breaking changes",
    )

    # Summary statistics
    total_changes: int = Field(default=0, description="Total number of changes")
    added_count: int = Field(default=0, description="Number of additions")
    removed_count: int = Field(default=0, description="Number of removals")
    modified_count: int = Field(default=0, description="Number of modifications")

    @property
    def has_breaking_changes(self) -> bool:
        """Check if there are any breaking changes."""
        return len(self.breaking_changes) > 0

    def entries_by_category(self, category: ChangeCategory) -> list[DiffEntry]:
        """Filter entries by category."""
        return [e for e in self.entries if e.category == category]

    def entries_by_severity(self, severity: Severity) -> list[DiffEntry]:
        """Filter entries by severity."""
        return [e for e in self.entries if e.severity == severity]


class DiffResult(BaseModel):
    """Result of a diff operation."""

    model_config = {"frozen": True}

    success: bool = Field(description="Whether the diff operation succeeded")
    report: DiffReport | None = Field(default=None, description="The diff report if successful")
    errors: list[AuditError] = Field(default_factory=list, description="Errors that occurred")

    @classmethod
    def ok(cls, report: DiffReport) -> "DiffResult":
        """Create a successful result."""
        return cls(success=True, report=report)

    @classmethod
    def fail(cls, errors: list[AuditError]) -> "DiffResult":
        """Create a failed result."""
        return cls(success=False, errors=errors)
