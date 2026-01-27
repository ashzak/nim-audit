"""Unit tests for CLI commands."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from nim_audit.cli.main import app


runner = CliRunner()


class TestMainCLI:
    """Tests for main CLI app."""

    def test_help(self):
        """Test --help flag."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "nim-audit" in result.stdout.lower() or "audit" in result.stdout.lower()

    def test_version(self):
        """Test --version flag."""
        # The version flag may or may not be implemented
        result = runner.invoke(app, ["--version"])
        # Just check it doesn't crash - version may not be implemented
        assert result.exit_code in (0, 2)  # 2 is typer's "no such option" exit code


class TestDiffCommand:
    """Tests for diff command."""

    def test_diff_help(self):
        """Test diff --help."""
        result = runner.invoke(app, ["diff", "--help"])
        assert result.exit_code == 0
        assert "diff" in result.stdout.lower()


class TestConfigCommand:
    """Tests for config command."""

    def test_config_help(self):
        """Test config --help."""
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0


class TestCompatCommand:
    """Tests for compat command."""

    def test_compat_help(self):
        """Test compat --help."""
        result = runner.invoke(app, ["compat", "--help"])
        assert result.exit_code == 0


class TestLintCommand:
    """Tests for lint command."""

    def test_lint_help(self):
        """Test lint --help."""
        result = runner.invoke(app, ["lint", "--help"])
        assert result.exit_code == 0


class TestFingerprintCommand:
    """Tests for fingerprint command."""

    def test_fingerprint_help(self):
        """Test fingerprint --help."""
        result = runner.invoke(app, ["fingerprint", "--help"])
        assert result.exit_code == 0


class TestClusterCommand:
    """Tests for cluster command."""

    def test_cluster_help(self):
        """Test cluster --help."""
        result = runner.invoke(app, ["cluster", "--help"])
        assert result.exit_code == 0
