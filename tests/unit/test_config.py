"""Unit tests for the ConfigAnalyzer."""

import pytest

from nim_audit.core.config import ConfigAnalyzer
from nim_audit.core.image import NIMImage
from nim_audit.models.config import ImpactLevel


class TestConfigAnalyzer:
    """Tests for ConfigAnalyzer."""

    def test_analyze_basic(self, sample_nim_image: NIMImage):
        """Test basic config analysis."""
        analyzer = ConfigAnalyzer()
        result = analyzer.analyze(sample_nim_image)

        assert result.success
        assert result.report is not None
        assert len(result.report.entries) > 0

    def test_analyze_with_env(self, sample_nim_image: NIMImage):
        """Test config analysis with custom env vars."""
        analyzer = ConfigAnalyzer()
        result = analyzer.analyze(
            sample_nim_image,
            env={"NIM_MAX_BATCH_SIZE": "64", "NIM_LOG_LEVEL": "DEBUG"},
        )

        assert result.success
        assert result.report is not None

        # Find the batch size entry
        batch_entry = next(
            (e for e in result.report.entries if e.name == "NIM_MAX_BATCH_SIZE"),
            None,
        )
        assert batch_entry is not None
        assert batch_entry.value == "64"

    def test_analyze_with_env_file(self, sample_nim_image: NIMImage, sample_env_file: str):
        """Test config analysis with env file."""
        analyzer = ConfigAnalyzer()
        result = analyzer.analyze(sample_nim_image, env_file=sample_env_file)

        assert result.success
        assert result.report is not None

        # Check that env file values are loaded
        batch_entry = next(
            (e for e in result.report.entries if e.name == "NIM_MAX_BATCH_SIZE"),
            None,
        )
        assert batch_entry is not None
        assert batch_entry.value == "32"

    def test_analyze_detects_deprecated(self, sample_nim_image: NIMImage):
        """Test that deprecated config vars are detected."""
        analyzer = ConfigAnalyzer()
        result = analyzer.analyze(
            sample_nim_image,
            env={"NIM_BATCH_SIZE": "16"},  # Deprecated
        )

        assert result.success
        assert result.report is not None

        deprecated = result.report.deprecated_entries
        assert len(deprecated) > 0
        assert any(e.name == "NIM_BATCH_SIZE" for e in deprecated)

    def test_analyze_high_impact_entries(self, sample_nim_image: NIMImage):
        """Test that high impact entries are identified."""
        analyzer = ConfigAnalyzer()
        result = analyzer.analyze(sample_nim_image)

        assert result.success
        assert result.report is not None

        high_impact = result.report.high_impact_entries
        # Should include entries like NIM_TENSOR_PARALLEL_SIZE if set

    def test_validate_config(self, sample_nim_image: NIMImage):
        """Test config validation."""
        analyzer = ConfigAnalyzer()

        # Valid config
        errors = analyzer.validate(
            sample_nim_image,
            env={"NIM_LOG_LEVEL": "DEBUG"},
        )
        assert len(errors) == 0

    def test_validate_invalid_value(self, sample_nim_image: NIMImage):
        """Test validation catches invalid values."""
        analyzer = ConfigAnalyzer()

        errors = analyzer.validate(
            sample_nim_image,
            env={"NIM_LOG_LEVEL": "INVALID"},
        )
        assert len(errors) > 0
        assert any("NIM_LOG_LEVEL" in e for e in errors)

    def test_load_env_file(self, sample_env_file: str):
        """Test loading env file."""
        analyzer = ConfigAnalyzer()
        env = analyzer._load_env_file(sample_env_file)

        assert env["NIM_SERVER_PORT"] == "8000"
        assert env["NIM_LOG_LEVEL"] == "DEBUG"
        assert env["NIM_MAX_BATCH_SIZE"] == "32"
        assert env["NIM_MODEL_NAME"] == "llama3-8b"  # Quoted value

    def test_effective_value(self, sample_nim_image: NIMImage):
        """Test effective value calculation."""
        analyzer = ConfigAnalyzer()
        result = analyzer.analyze(sample_nim_image)

        assert result.success
        assert result.report is not None

        for entry in result.report.entries:
            if entry.value is not None:
                assert entry.effective_value == entry.value
            else:
                assert entry.effective_value == entry.default_value
