"""Configuration analysis data models."""

from enum import Enum

from pydantic import BaseModel, Field

from nim_audit.models.common import AuditError


class ImpactLevel(str, Enum):
    """Impact level of a configuration option."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConfigImpact(BaseModel):
    """Description of a configuration option's impact."""

    model_config = {"frozen": True}

    level: ImpactLevel = Field(description="Impact level")
    description: str = Field(description="Impact description")
    affects: list[str] = Field(
        default_factory=list,
        description="What aspects are affected (performance, memory, accuracy, etc)",
    )


class ConfigEntry(BaseModel):
    """A single configuration entry."""

    model_config = {"frozen": True}

    name: str = Field(description="Environment variable or config name")
    value: str | None = Field(default=None, description="Current value")
    default_value: str | None = Field(default=None, description="Default value")
    description: str = Field(default="", description="Description of this config")
    impact: ConfigImpact | None = Field(default=None, description="Impact analysis")
    is_required: bool = Field(default=False, description="Whether this config is required")
    is_deprecated: bool = Field(default=False, description="Whether this config is deprecated")
    deprecated_message: str | None = Field(
        default=None,
        description="Deprecation message if deprecated",
    )
    valid_values: list[str] | None = Field(
        default=None,
        description="List of valid values if constrained",
    )
    validation_pattern: str | None = Field(
        default=None,
        description="Regex pattern for validation",
    )

    @property
    def is_set(self) -> bool:
        """Check if this config has a non-default value."""
        return self.value is not None and self.value != self.default_value

    @property
    def effective_value(self) -> str | None:
        """Get the effective value (set value or default)."""
        return self.value if self.value is not None else self.default_value


class ConfigReport(BaseModel):
    """Complete configuration analysis report."""

    model_config = {"frozen": True}

    image_reference: str = Field(description="Image that was analyzed")
    entries: list[ConfigEntry] = Field(default_factory=list, description="All config entries")
    warnings: list[str] = Field(default_factory=list, description="Configuration warnings")
    recommendations: list[str] = Field(
        default_factory=list,
        description="Optimization recommendations",
    )

    @property
    def high_impact_entries(self) -> list[ConfigEntry]:
        """Get entries with high or critical impact."""
        return [
            e
            for e in self.entries
            if e.impact and e.impact.level in (ImpactLevel.HIGH, ImpactLevel.CRITICAL)
        ]

    @property
    def deprecated_entries(self) -> list[ConfigEntry]:
        """Get deprecated config entries that are set."""
        return [e for e in self.entries if e.is_deprecated and e.is_set]

    @property
    def required_missing(self) -> list[ConfigEntry]:
        """Get required entries that are not set."""
        return [e for e in self.entries if e.is_required and not e.is_set]


class ConfigResult(BaseModel):
    """Result of a configuration analysis operation."""

    model_config = {"frozen": True}

    success: bool = Field(description="Whether the analysis succeeded")
    report: ConfigReport | None = Field(default=None, description="The config report if successful")
    errors: list[AuditError] = Field(default_factory=list, description="Errors that occurred")

    @classmethod
    def ok(cls, report: ConfigReport) -> "ConfigResult":
        """Create a successful result."""
        return cls(success=True, report=report)

    @classmethod
    def fail(cls, errors: list[AuditError]) -> "ConfigResult":
        """Create a failed result."""
        return cls(success=False, errors=errors)
