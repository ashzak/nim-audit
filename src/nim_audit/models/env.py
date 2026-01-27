"""Environment variable analysis data models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ImpactMetric(str, Enum):
    """Metrics that environment variables can affect."""

    LATENCY = "latency"
    THROUGHPUT = "throughput"
    MEMORY = "memory"
    DETERMINISM = "determinism"
    NUMERICS = "numerics"
    COMPATIBILITY = "compatibility"


class ImpactLevel(str, Enum):
    """Impact level for a metric."""

    STRONG_POSITIVE = "++"
    POSITIVE = "+"
    NEUTRAL = "±"
    NEGATIVE = "-"
    STRONG_NEGATIVE = "--"
    NONE = "none"


class Severity(str, Enum):
    """Severity level for findings."""

    INFO = "INFO"
    WARN = "WARN"
    FAIL = "FAIL"


class Affect(BaseModel):
    """How an env var affects a metric."""

    model_config = {"frozen": True}

    metric: ImpactMetric = Field(description="The metric being affected")
    impact: ImpactLevel = Field(description="The impact level")


class Evidence(BaseModel):
    """Evidence of an env var's presence in a file."""

    model_config = {"frozen": True}

    path: str = Field(description="File path where var was found")
    count: int = Field(description="Number of occurrences")
    score: float = Field(description="Relevance score")
    sample_snippets: list[str] = Field(
        default_factory=list, description="Sample code snippets"
    )
    signals: dict[str, int] = Field(
        default_factory=dict,
        description="Signal types (conditional, assignment, help_context)",
    )


class DiscoveredVar(BaseModel):
    """An environment variable discovered in the container."""

    model_config = {"frozen": True}

    name: str = Field(description="Variable name")
    score: float = Field(description="Total relevance score")
    evidences: list[Evidence] = Field(
        default_factory=list, description="Evidence of usage"
    )


class DiscoveryResult(BaseModel):
    """Result of environment variable discovery."""

    model_config = {"frozen": True}

    prefixes: list[str] = Field(description="Prefixes searched for")
    vars: list[DiscoveredVar] = Field(description="Discovered variables")
    files_scanned: int = Field(description="Number of files scanned")


class RegistryEntry(BaseModel):
    """A known environment variable from the registry."""

    model_config = {"frozen": True}

    name: str = Field(description="Variable name")
    type: str | None = Field(default=None, description="Value type (enum, int, etc)")
    scope: str | None = Field(default=None, description="Scope (service, runtime)")
    precedence: str | None = Field(default=None, description="Precedence rules")
    default: str | None = Field(default=None, description="Default value")
    affects: list[Affect] = Field(
        default_factory=list, description="Metrics affected"
    )
    determinism: str | None = Field(default=None, description="Determinism notes")
    interactions: list[dict[str, Any]] = Field(
        default_factory=list, description="Variable interactions"
    )
    failure_modes: list[str] = Field(
        default_factory=list, description="Known failure modes"
    )
    confidence: str = Field(default="LOW", description="Confidence level (HIGH/MED/LOW)")
    evidence: list[dict[str, Any]] = Field(
        default_factory=list, description="Evidence sources"
    )


class InteractionEdge(BaseModel):
    """An interaction between two environment variables."""

    model_config = {"frozen": True}

    var_a: str = Field(description="First variable")
    var_b: str = Field(description="Second variable")
    interaction_type: str = Field(description="Type of interaction")
    description: str = Field(description="Description of the interaction")


class Registry(BaseModel):
    """Registry of known environment variables."""

    model_config = {"frozen": True}

    entries: dict[str, RegistryEntry] = Field(
        default_factory=dict, description="Registry entries by name"
    )
    interactions: list[InteractionEdge] = Field(
        default_factory=list, description="Variable interactions"
    )
    warnings: list[str] = Field(
        default_factory=list, description="Parse warnings"
    )


class Finding(BaseModel):
    """A lint finding."""

    model_config = {"frozen": True}

    id: str = Field(description="Finding ID")
    severity: Severity = Field(description="Severity level")
    env: str | None = Field(default=None, description="Related env var")
    message: str = Field(description="Finding message")


class LintResult(BaseModel):
    """Result of environment linting."""

    model_config = {"frozen": True}

    overall: str = Field(description="Overall status (PASS/WARN/FAIL)")
    findings: list[Finding] = Field(default_factory=list, description="Findings")
    counts: dict[str, int] = Field(
        default_factory=dict, description="Count by severity"
    )


class EnvSurface(BaseModel):
    """Environment variable surface for an image."""

    model_config = {"frozen": True}

    vars: dict[str, Any] = Field(
        default_factory=dict, description="All known variables"
    )


class EnvDiff(BaseModel):
    """Diff between two env surfaces."""

    model_config = {"frozen": True}

    added: list[str] = Field(default_factory=list, description="Added variables")
    removed: list[str] = Field(default_factory=list, description="Removed variables")
    changed: dict[str, list[Any]] = Field(
        default_factory=dict, description="Changed values [old, new]"
    )
    risky_changed: int = Field(default=0, description="Number of risky changes")


class EnvDescribeVar(BaseModel):
    """Detailed description of an environment variable."""

    model_config = {"frozen": True}

    name: str = Field(description="Variable name")
    effective: str | None = Field(default=None, description="Effective value")
    confidence: str = Field(default="LOW", description="Confidence level")
    affects: list[dict[str, str]] = Field(
        default_factory=list, description="Affected metrics"
    )
    interactions: list[dict[str, str]] = Field(
        default_factory=list, description="Variable interactions"
    )
    failure_modes: list[str] = Field(
        default_factory=list, description="Known failure modes"
    )
    discovered: bool = Field(default=False, description="Whether discovered in image")
    in_registry: bool = Field(default=False, description="Whether in registry")
