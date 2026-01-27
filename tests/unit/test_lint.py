"""Unit tests for the PolicyLinter."""

import pytest

from nim_audit.core.lint import PolicyLinter
from nim_audit.core.image import NIMImage
from nim_audit.models.policy import Policy, Rule, RuleSeverity


class TestPolicyLinter:
    """Tests for PolicyLinter."""

    def test_lint_basic(self, sample_nim_image: NIMImage):
        """Test basic linting with built-in rules."""
        linter = PolicyLinter()
        result = linter.lint(sample_nim_image)

        assert result.success
        assert result.image_reference == sample_nim_image.reference

    def test_lint_with_custom_policy(
        self, sample_nim_image: NIMImage, sample_policy_file: str
    ):
        """Test linting with custom policy."""
        linter = PolicyLinter()
        policy = linter.load_policy(sample_policy_file)
        result = linter.lint(sample_nim_image, policy=policy)

        assert result.success
        assert result.policy.name == "test-policy"

    def test_lint_without_builtin(
        self, sample_nim_image: NIMImage, sample_policy_file: str
    ):
        """Test linting with only custom rules."""
        linter = PolicyLinter()
        policy = linter.load_policy(sample_policy_file)
        result = linter.lint(sample_nim_image, policy=policy, include_builtin=False)

        assert result.success
        # Should only have custom policy rules
        assert len(result.policy.rules) == len(policy.rules)

    def test_builtin_rules_exist(self):
        """Test that built-in rules are defined."""
        linter = PolicyLinter()
        assert len(linter.BUILTIN_RULES) > 0

        for rule in linter.BUILTIN_RULES:
            assert rule.id
            assert rule.name
            assert rule.condition

    def test_violation_detection(self, sample_nim_image: NIMImage):
        """Test that violations are detected."""
        linter = PolicyLinter()

        # Create a rule that will fail
        failing_rule = Rule(
            id="test-fail",
            name="always-fail",
            description="This rule always fails",
            severity=RuleSeverity.ERROR,
            condition="False",
        )

        policy = Policy(name="test", rules=[failing_rule])
        result = linter.lint(sample_nim_image, policy=policy, include_builtin=False)

        assert result.success
        assert len(result.violations) > 0
        assert not result.passed

    def test_passed_property(self, sample_nim_image: NIMImage):
        """Test the passed property."""
        linter = PolicyLinter()

        # Create a rule that will pass
        passing_rule = Rule(
            id="test-pass",
            name="always-pass",
            description="This rule always passes",
            severity=RuleSeverity.ERROR,
            condition="True",
        )

        policy = Policy(name="test", rules=[passing_rule])
        result = linter.lint(sample_nim_image, policy=policy, include_builtin=False)

        assert result.success
        assert result.passed
        assert len(result.violations) == 0

    def test_violation_counts(self, sample_nim_image: NIMImage):
        """Test violation counting."""
        linter = PolicyLinter()

        rules = [
            Rule(
                id="err-1",
                name="error-rule",
                description="Error rule",
                severity=RuleSeverity.ERROR,
                condition="False",
            ),
            Rule(
                id="warn-1",
                name="warning-rule",
                description="Warning rule",
                severity=RuleSeverity.WARNING,
                condition="False",
            ),
            Rule(
                id="info-1",
                name="info-rule",
                description="Info rule",
                severity=RuleSeverity.INFO,
                condition="False",
            ),
        ]

        policy = Policy(name="test", rules=rules)
        result = linter.lint(sample_nim_image, policy=policy, include_builtin=False)

        assert result.error_count == 1
        assert result.warning_count == 1

    def test_load_policy(self, sample_policy_file: str):
        """Test loading policy from YAML."""
        linter = PolicyLinter()
        policy = linter.load_policy(sample_policy_file)

        assert policy.name == "test-policy"
        assert policy.version == "1.0.0"
        assert len(policy.rules) == 2
        assert policy.rules[0].id == "test-001"

    def test_save_policy(self, tmp_path):
        """Test saving policy to YAML."""
        linter = PolicyLinter()

        policy = Policy(
            name="save-test",
            version="1.0.0",
            description="Test policy",
            rules=[
                Rule(
                    id="save-001",
                    name="test-rule",
                    description="A test rule",
                    severity=RuleSeverity.WARNING,
                    condition="True",
                )
            ],
        )

        path = tmp_path / "test-policy.yaml"
        linter.save_policy(policy, str(path))

        # Load it back
        loaded = linter.load_policy(str(path))
        assert loaded.name == "save-test"
        assert len(loaded.rules) == 1
        assert loaded.rules[0].id == "save-001"

    def test_enabled_rules(self):
        """Test filtering enabled rules."""
        policy = Policy(
            name="test",
            rules=[
                Rule(id="r1", name="enabled", description="Enabled rule", condition="True", enabled=True),
                Rule(id="r2", name="disabled", description="Disabled rule", condition="True", enabled=False),
            ],
        )

        assert len(policy.enabled_rules) == 1
        assert policy.enabled_rules[0].id == "r1"

    def test_rule_evaluation_with_labels(self, sample_nim_image: NIMImage):
        """Test rule evaluation accessing labels."""
        linter = PolicyLinter()

        rule = Rule(
            id="label-check",
            name="check-nim-version",
            description="Check NIM version label",
            condition="labels.get('com.nvidia.nim.version') == '1.5.0'",
        )

        policy = Policy(name="test", rules=[rule])
        result = linter.lint(sample_nim_image, policy=policy, include_builtin=False)

        assert result.success
        assert result.passed
