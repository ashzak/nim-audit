"""Policy and linting data models."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from nim_audit.models.common import AuditError


class RuleSeverity(str, Enum):
    """Severity of a lint rule."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Rule(BaseModel):
    """A single policy rule."""

    model_config = {"frozen": True}

    id: str = Field(description="Unique rule identifier")
    name: str = Field(description="Human-readable rule name")
    description: str = Field(description="Rule description")
    severity: RuleSeverity = Field(default=RuleSeverity.WARNING, description="Rule severity")
    category: str = Field(default="general", description="Rule category")
    enabled: bool = Field(default=True, description="Whether rule is enabled")

    # Rule configuration
    condition: str = Field(description="Rule condition expression")
    params: dict[str, Any] = Field(default_factory=dict, description="Rule parameters")

    # Documentation
    rationale: str | None = Field(default=None, description="Why this rule exists")
    remediation: str | None = Field(default=None, description="How to fix violations")


class Policy(BaseModel):
    """A collection of policy rules."""

    model_config = {"frozen": True}

    name: str = Field(description="Policy name")
    version: str = Field(default="1.0.0", description="Policy version")
    description: str = Field(default="", description="Policy description")
    rules: list[Rule] = Field(default_factory=list, description="Policy rules")

    # Inheritance
    extends: list[str] = Field(
        default_factory=list,
        description="Parent policies to extend",
    )

    # Metadata
    author: str | None = Field(default=None, description="Policy author")
    tags: list[str] = Field(default_factory=list, description="Policy tags")

    def get_rule(self, rule_id: str) -> Rule | None:
        """Get a rule by ID."""
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None

    @property
    def enabled_rules(self) -> list[Rule]:
        """Get all enabled rules."""
        return [r for r in self.rules if r.enabled]

    def rules_by_severity(self, severity: RuleSeverity) -> list[Rule]:
        """Get rules by severity."""
        return [r for r in self.rules if r.severity == severity and r.enabled]


class LintViolation(BaseModel):
    """A single lint violation."""

    model_config = {"frozen": True}

    rule: Rule = Field(description="The violated rule")
    message: str = Field(description="Violation message")
    location: str | None = Field(default=None, description="Location of violation")
    actual_value: str | None = Field(default=None, description="Actual value found")
    expected_value: str | None = Field(default=None, description="Expected value")

    @property
    def severity(self) -> RuleSeverity:
        """Get violation severity from rule."""
        return self.rule.severity


class LintResult(BaseModel):
    """Result of a lint operation."""

    model_config = {"frozen": True}

    success: bool = Field(description="Whether linting succeeded without errors")
    image_reference: str = Field(description="Image that was linted")
    policy: Policy = Field(description="Policy used for linting")
    violations: list[LintViolation] = Field(
        default_factory=list,
        description="All violations found",
    )
    errors: list[AuditError] = Field(default_factory=list, description="Errors that occurred")

    @property
    def passed(self) -> bool:
        """Check if lint passed (no error-level violations)."""
        return not any(v.severity == RuleSeverity.ERROR for v in self.violations)

    @property
    def error_count(self) -> int:
        """Count error-level violations."""
        return sum(1 for v in self.violations if v.severity == RuleSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        """Count warning-level violations."""
        return sum(1 for v in self.violations if v.severity == RuleSeverity.WARNING)

    def violations_by_rule(self, rule_id: str) -> list[LintViolation]:
        """Get violations for a specific rule."""
        return [v for v in self.violations if v.rule.id == rule_id]

    @classmethod
    def ok(
        cls,
        image_reference: str,
        policy: Policy,
        violations: list[LintViolation] | None = None,
    ) -> "LintResult":
        """Create a successful result."""
        return cls(
            success=True,
            image_reference=image_reference,
            policy=policy,
            violations=violations or [],
        )

    @classmethod
    def fail(
        cls,
        image_reference: str,
        policy: Policy,
        errors: list[AuditError],
    ) -> "LintResult":
        """Create a failed result."""
        return cls(
            success=False,
            image_reference=image_reference,
            policy=policy,
            errors=errors,
        )
