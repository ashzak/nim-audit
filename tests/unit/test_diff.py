"""Unit tests for the DiffEngine."""

import pytest

from nim_audit.core.diff import DiffEngine
from nim_audit.core.image import NIMImage
from nim_audit.models.diff import ChangeCategory, ChangeType, Severity


class TestDiffEngine:
    """Tests for DiffEngine."""

    def test_diff_identical_images(self, sample_nim_image: NIMImage):
        """Test diffing identical images produces no changes."""
        engine = DiffEngine()
        result = engine.diff(sample_nim_image, sample_nim_image)

        assert result.success
        assert result.report is not None
        assert result.report.total_changes == 0
        assert len(result.report.breaking_changes) == 0

    def test_diff_detects_version_changes(
        self, sample_nim_image: NIMImage, sample_nim_image_v2: NIMImage
    ):
        """Test that version changes are detected."""
        engine = DiffEngine()
        result = engine.diff(sample_nim_image, sample_nim_image_v2)

        assert result.success
        assert result.report is not None
        assert result.report.total_changes > 0

        # Find NIM version change
        version_changes = [
            e for e in result.report.entries
            if e.path == "nim_version"
        ]
        assert len(version_changes) == 1
        assert version_changes[0].old_value == "1.5.0"
        assert version_changes[0].new_value == "1.6.0"

    def test_diff_detects_env_changes(
        self, sample_nim_image: NIMImage, sample_nim_image_v2: NIMImage
    ):
        """Test that environment variable changes are detected."""
        engine = DiffEngine()
        result = engine.diff(sample_nim_image, sample_nim_image_v2)

        assert result.success
        assert result.report is not None

        # Find batch size change
        batch_changes = [
            e for e in result.report.entries
            if e.path == "env/NIM_MAX_BATCH_SIZE"
        ]
        assert len(batch_changes) == 1
        assert batch_changes[0].change_type == ChangeType.MODIFIED
        assert batch_changes[0].old_value == "8"
        assert batch_changes[0].new_value == "16"

        # Find new env var
        new_env = [
            e for e in result.report.entries
            if e.path == "env/NIM_ENABLE_PREFIX_CACHING"
        ]
        assert len(new_env) == 1
        assert new_env[0].change_type == ChangeType.ADDED

    def test_diff_detects_quantization_changes(
        self, sample_nim_image: NIMImage, sample_nim_image_v2: NIMImage
    ):
        """Test that quantization changes are detected."""
        engine = DiffEngine()
        result = engine.diff(sample_nim_image, sample_nim_image_v2)

        assert result.success
        assert result.report is not None

        quant_changes = [
            e for e in result.report.entries
            if e.path == "quantization"
        ]
        assert len(quant_changes) == 1
        assert quant_changes[0].old_value == "fp16"
        assert quant_changes[0].new_value == "int8"

    def test_diff_detects_port_changes(
        self, sample_nim_image: NIMImage, sample_nim_image_v2: NIMImage
    ):
        """Test that exposed port changes are detected."""
        engine = DiffEngine()
        result = engine.diff(sample_nim_image, sample_nim_image_v2)

        assert result.success
        assert result.report is not None

        port_changes = [
            e for e in result.report.entries
            if "exposed_ports" in e.path
        ]
        # Port 8080 was added
        added_ports = [e for e in port_changes if e.change_type == ChangeType.ADDED]
        assert len(added_ports) == 1

    def test_diff_counts_are_correct(
        self, sample_nim_image: NIMImage, sample_nim_image_v2: NIMImage
    ):
        """Test that diff counts are calculated correctly."""
        engine = DiffEngine()
        result = engine.diff(sample_nim_image, sample_nim_image_v2)

        assert result.success
        assert result.report is not None

        report = result.report
        assert report.total_changes == len(report.entries)
        assert report.added_count == sum(
            1 for e in report.entries if e.change_type == ChangeType.ADDED
        )
        assert report.removed_count == sum(
            1 for e in report.entries if e.change_type == ChangeType.REMOVED
        )
        assert report.modified_count == sum(
            1 for e in report.entries if e.change_type == ChangeType.MODIFIED
        )

    def test_entries_by_category(
        self, sample_nim_image: NIMImage, sample_nim_image_v2: NIMImage
    ):
        """Test filtering entries by category."""
        engine = DiffEngine()
        result = engine.diff(sample_nim_image, sample_nim_image_v2)

        assert result.success
        assert result.report is not None

        env_entries = result.report.entries_by_category(ChangeCategory.ENVIRONMENT)
        assert all(e.category == ChangeCategory.ENVIRONMENT for e in env_entries)

    def test_entries_by_severity(
        self, sample_nim_image: NIMImage, sample_nim_image_v2: NIMImage
    ):
        """Test filtering entries by severity."""
        engine = DiffEngine()
        result = engine.diff(sample_nim_image, sample_nim_image_v2)

        assert result.success
        assert result.report is not None

        warning_entries = result.report.entries_by_severity(Severity.WARNING)
        assert all(e.severity == Severity.WARNING for e in warning_entries)
