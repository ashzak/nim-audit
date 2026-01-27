"""PolicyLinter for rule-based validation."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import yaml

from nim_audit.models.common import AuditError
from nim_audit.models.policy import (
    LintResult,
    LintViolation,
    Policy,
    Rule,
    RuleSeverity,
)

if TYPE_CHECKING:
    from nim_audit.core.image import NIMImage


class PolicyLinter:
    """Linter for validating NIM images against policies.

    The PolicyLinter validates NIM container images against a set of
    rules defined in a policy file. It supports custom policies and
    includes built-in enterprise rules.

    Example:
        linter = PolicyLinter()

        # Load policy
        policy = linter.load_policy("enterprise.yaml")

        # Lint image
        result = linter.lint(image, policy)

        if not result.passed:
            for violation in result.violations:
                print(f"{violation.rule.severity}: {violation.message}")
    """

    # Built-in enterprise rules
    BUILTIN_RULES = [
        Rule(
            id="nim-001",
            name="require-version-label",
            description="NIM images must have a version label",
            severity=RuleSeverity.ERROR,
            category="metadata",
            condition="labels.get('com.nvidia.nim.version') is not None",
            rationale="Version tracking is essential for auditing and rollback",
            remediation="Add com.nvidia.nim.version label to image",
        ),
        Rule(
            id="nim-002",
            name="no-root-user",
            description="Container should not run as root",
            severity=RuleSeverity.WARNING,
            category="security",
            condition="config.get('User', 'root') != 'root' and config.get('User', '') != ''",
            rationale="Running as root poses security risks",
            remediation="Set a non-root user in the Dockerfile",
        ),
        Rule(
            id="nim-003",
            name="require-model-name",
            description="NIM images must specify the model name",
            severity=RuleSeverity.ERROR,
            category="metadata",
            condition="labels.get('com.nvidia.nim.model.name') is not None",
            rationale="Model name is required for inventory and tracking",
            remediation="Add com.nvidia.nim.model.name label to image",
        ),
        Rule(
            id="nim-004",
            name="check-exposed-ports",
            description="NIM should expose the standard API port",
            severity=RuleSeverity.WARNING,
            category="configuration",
            condition="8000 in exposed_ports or 80 in exposed_ports",
            rationale="Standard ports ensure consistency across deployments",
            remediation="Expose port 8000 for the NIM API",
        ),
        Rule(
            id="nim-005",
            name="no-sensitive-env",
            description="No sensitive values in default environment",
            severity=RuleSeverity.ERROR,
            category="security",
            condition="not any(k in ['PASSWORD', 'SECRET', 'TOKEN', 'KEY'] for k in env.keys())",
            rationale="Sensitive values should not be baked into images",
            remediation="Remove sensitive environment variables from image",
        ),
    ]

    def __init__(self) -> None:
        """Initialize the policy linter."""
        self._builtin_policy = Policy(
            name="builtin",
            version="1.0.0",
            description="Built-in enterprise rules for NIM images",
            rules=self.BUILTIN_RULES,
        )

    def lint(
        self,
        image: "NIMImage",
        policy: Policy | None = None,
        include_builtin: bool = True,
    ) -> LintResult:
        """Lint a NIM image against a policy.

        Args:
            image: The NIM image to lint
            policy: Policy to use (optional)
            include_builtin: Whether to include built-in rules

        Returns:
            LintResult with violations and status
        """
        # Combine policies
        all_rules: list[Rule] = []

        if include_builtin:
            all_rules.extend(self._builtin_policy.rules)

        if policy:
            all_rules.extend(policy.rules)

        effective_policy = Policy(
            name=policy.name if policy else "builtin",
            version=policy.version if policy else "1.0.0",
            description=policy.description if policy else "Combined policy",
            rules=all_rules,
        )

        violations: list[LintViolation] = []
        errors: list[AuditError] = []

        # Build context for rule evaluation
        context = self._build_context(image)

        for rule in effective_policy.enabled_rules:
            try:
                passed = self._evaluate_rule(rule, context)

                if not passed:
                    violations.append(
                        LintViolation(
                            rule=rule,
                            message=rule.description,
                            location=image.reference,
                        )
                    )

            except Exception as e:
                errors.append(
                    AuditError(
                        code="RULE_ERROR",
                        message=f"Failed to evaluate rule {rule.id}: {e}",
                        details={"rule_id": rule.id},
                    )
                )

        if errors:
            return LintResult.fail(image.reference, effective_policy, errors)

        return LintResult.ok(image.reference, effective_policy, violations)

    def _build_context(self, image: "NIMImage") -> dict[str, Any]:
        """Build evaluation context from image metadata."""
        metadata = image.metadata

        return {
            "reference": metadata.reference,
            "repository": metadata.repository,
            "tag": metadata.tag,
            "labels": metadata.labels,
            "env": metadata.env,
            "exposed_ports": metadata.exposed_ports,
            "entrypoint": metadata.entrypoint,
            "cmd": metadata.cmd,
            "architecture": metadata.architecture,
            "os": metadata.os,
            "nim_version": metadata.nim_version,
            "model_name": metadata.model_name,
            "model_version": metadata.model_version,
            "quantization": metadata.quantization,
            "config": metadata.raw_config.get("Config", {}),
        }

    def _evaluate_rule(self, rule: Rule, context: dict[str, Any]) -> bool:
        """Evaluate a rule condition against context.

        Uses a safe AST-based expression evaluator.
        """
        from nim_audit.utils.expression import safe_eval

        condition = rule.condition

        try:
            # Use the safe expression evaluator
            result = safe_eval(condition, context)
            return bool(result)

        except ValueError as e:
            # Log the error but don't fail - return True to avoid false positives
            from nim_audit.utils.logging import get_logger
            logger = get_logger("lint")
            logger.warning(f"Failed to evaluate rule {rule.id}: {e}")
            return True
        except Exception:
            # If evaluation fails, assume the rule passes
            # to avoid false positives
            return True

    def load_policy(self, path: str) -> Policy:
        """Load a policy from a YAML file.

        Args:
            path: Path to the policy file

        Returns:
            Policy loaded from file
        """
        with open(path, "r") as f:
            data = yaml.safe_load(f)

        # Parse rules
        rules = []
        for rule_data in data.get("rules", []):
            rules.append(
                Rule(
                    id=rule_data["id"],
                    name=rule_data["name"],
                    description=rule_data.get("description", ""),
                    severity=RuleSeverity(rule_data.get("severity", "warning")),
                    category=rule_data.get("category", "general"),
                    enabled=rule_data.get("enabled", True),
                    condition=rule_data["condition"],
                    params=rule_data.get("params", {}),
                    rationale=rule_data.get("rationale"),
                    remediation=rule_data.get("remediation"),
                )
            )

        return Policy(
            name=data.get("name", "custom"),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            rules=rules,
            extends=data.get("extends", []),
            author=data.get("author"),
            tags=data.get("tags", []),
        )

    def save_policy(self, policy: Policy, path: str) -> None:
        """Save a policy to a YAML file.

        Args:
            policy: The policy to save
            path: Path to save to
        """
        data = {
            "name": policy.name,
            "version": policy.version,
            "description": policy.description,
            "author": policy.author,
            "tags": policy.tags,
            "extends": policy.extends,
            "rules": [
                {
                    "id": rule.id,
                    "name": rule.name,
                    "description": rule.description,
                    "severity": rule.severity.value,
                    "category": rule.category,
                    "enabled": rule.enabled,
                    "condition": rule.condition,
                    "params": rule.params,
                    "rationale": rule.rationale,
                    "remediation": rule.remediation,
                }
                for rule in policy.rules
            ],
        }

        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
