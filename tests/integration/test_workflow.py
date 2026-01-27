"""Integration tests for end-to-end workflows."""

from datetime import datetime

import pytest

from nim_audit.core.diff import DiffEngine
from nim_audit.core.config import ConfigAnalyzer
from nim_audit.core.compat import CompatChecker
from nim_audit.core.lint import PolicyLinter
from nim_audit.core.image import NIMImage
from nim_audit.models.image import ImageDigest, ImageManifest, ImageMetadata, LayerInfo
from nim_audit.models.policy import Policy, Rule, RuleSeverity


class TestDiffWorkflow:
    """Integration tests for diff workflow."""

    @pytest.fixture
    def v1_metadata(self):
        """Create v1 image metadata."""
        return ImageMetadata(
            reference="nvcr.io/nim/llama3:1.5.0",
            repository="nim/llama3",
            tag="1.5.0",
            digest=ImageDigest(hash="abc123"),
            labels={
                "com.nvidia.nim.version": "1.5.0",
                "com.nvidia.nim.model.name": "llama3-8b",
            },
            created=datetime(2024, 1, 1),
            architecture="amd64",
            os="linux",
            nim_version="1.5.0",
            model_name="llama3-8b",
            env={"NIM_MAX_BATCH_SIZE": "8"},
            exposed_ports=[8000],
            manifest=ImageManifest(
                schema_version=2,
                media_type="application/vnd.docker.distribution.manifest.v2+json",
                digest=ImageDigest(hash="manifest1"),
                config_digest=ImageDigest(hash="config1"),
                layers=[],
            ),
        )

    @pytest.fixture
    def v2_metadata(self):
        """Create v2 image metadata with changes."""
        return ImageMetadata(
            reference="nvcr.io/nim/llama3:1.6.0",
            repository="nim/llama3",
            tag="1.6.0",
            digest=ImageDigest(hash="def456"),
            labels={
                "com.nvidia.nim.version": "1.6.0",
                "com.nvidia.nim.model.name": "llama3-8b",
                "com.nvidia.nim.model.quantization": "int8",  # New label
            },
            created=datetime(2024, 2, 1),
            architecture="amd64",
            os="linux",
            nim_version="1.6.0",
            model_name="llama3-8b",
            quantization="int8",  # New
            env={
                "NIM_MAX_BATCH_SIZE": "16",  # Changed
                "NIM_ENABLE_CACHE": "true",  # New
            },
            exposed_ports=[8000, 8080],  # Added port
            manifest=ImageManifest(
                schema_version=2,
                media_type="application/vnd.docker.distribution.manifest.v2+json",
                digest=ImageDigest(hash="manifest2"),
                config_digest=ImageDigest(hash="config2"),
                layers=[],
            ),
        )

    def test_full_diff_workflow(self, v1_metadata, v2_metadata):
        """Test complete diff workflow from images to report."""
        # Create images from metadata
        img1 = NIMImage.from_metadata(v1_metadata)
        img2 = NIMImage.from_metadata(v2_metadata)

        # Run diff
        engine = DiffEngine()
        result = engine.diff(img1, img2)

        # Verify result
        assert result.success
        assert result.report is not None

        report = result.report
        assert report.source_image.reference == "nvcr.io/nim/llama3:1.5.0"
        assert report.target_image.reference == "nvcr.io/nim/llama3:1.6.0"
        assert report.total_changes > 0

        # Verify specific changes detected
        paths = [e.path for e in report.entries]
        assert "nim_version" in paths
        assert "env/NIM_MAX_BATCH_SIZE" in paths


class TestConfigWorkflow:
    """Integration tests for config analysis workflow."""

    @pytest.fixture
    def image_metadata(self):
        """Create image metadata."""
        return ImageMetadata(
            reference="nvcr.io/nim/llama3:1.5.0",
            repository="nim/llama3",
            tag="1.5.0",
            digest=ImageDigest(hash="abc123"),
            labels={},
            created=datetime(2024, 1, 1),
            architecture="amd64",
            os="linux",
            env={
                "NIM_MAX_BATCH_SIZE": "8",
                "NIM_LOG_LEVEL": "INFO",
            },
            manifest=ImageManifest(
                schema_version=2,
                media_type="application/vnd.docker.distribution.manifest.v2+json",
                digest=ImageDigest(hash="manifest1"),
                config_digest=ImageDigest(hash="config1"),
                layers=[],
            ),
        )

    def test_config_analysis_with_override(self, image_metadata):
        """Test config analysis with user overrides."""
        image = NIMImage.from_metadata(image_metadata)

        analyzer = ConfigAnalyzer()
        result = analyzer.analyze(
            image,
            env={"NIM_MAX_BATCH_SIZE": "32"},  # Override
        )

        assert result.success
        assert result.report is not None

        # Find the batch size entry
        batch_entries = [e for e in result.report.entries if "BATCH" in e.name]
        assert len(batch_entries) > 0


class TestLintWorkflow:
    """Integration tests for lint workflow."""

    @pytest.fixture
    def image_metadata_passing(self):
        """Create image metadata that passes lint."""
        return ImageMetadata(
            reference="nvcr.io/nim/llama3:1.5.0",
            repository="nim/llama3",
            tag="1.5.0",
            digest=ImageDigest(hash="abc123"),
            labels={
                "com.nvidia.nim.version": "1.5.0",
                "com.nvidia.nim.model.name": "llama3-8b",
            },
            created=datetime(2024, 1, 1),
            architecture="amd64",
            os="linux",
            nim_version="1.5.0",
            model_name="llama3-8b",
            env={"NIM_LOG_LEVEL": "INFO"},
            exposed_ports=[8000],
            raw_config={"Config": {"User": "nim"}},
            manifest=ImageManifest(
                schema_version=2,
                media_type="application/vnd.docker.distribution.manifest.v2+json",
                digest=ImageDigest(hash="manifest1"),
                config_digest=ImageDigest(hash="config1"),
                layers=[],
            ),
        )

    @pytest.fixture
    def image_metadata_failing(self):
        """Create image metadata that fails lint."""
        return ImageMetadata(
            reference="nvcr.io/nim/bad:1.0.0",
            repository="nim/bad",
            tag="1.0.0",
            digest=ImageDigest(hash="abc123"),
            labels={},  # Missing required labels
            created=datetime(2024, 1, 1),
            architecture="amd64",
            os="linux",
            env={"PASSWORD": "secret"},  # Sensitive env var
            exposed_ports=[],  # Missing port
            raw_config={"Config": {"User": "root"}},  # Running as root
            manifest=ImageManifest(
                schema_version=2,
                media_type="application/vnd.docker.distribution.manifest.v2+json",
                digest=ImageDigest(hash="manifest1"),
                config_digest=ImageDigest(hash="config1"),
                layers=[],
            ),
        )

    def test_lint_passing_image(self, image_metadata_passing):
        """Test linting an image that passes."""
        image = NIMImage.from_metadata(image_metadata_passing)

        linter = PolicyLinter()
        result = linter.lint(image)

        assert result.passed or len(result.violations) == 0 or all(
            v.rule.severity != RuleSeverity.ERROR for v in result.violations
        )

    def test_lint_failing_image(self, image_metadata_failing):
        """Test linting an image that fails."""
        image = NIMImage.from_metadata(image_metadata_failing)

        linter = PolicyLinter()
        result = linter.lint(image)

        # Should have violations
        assert len(result.violations) > 0

    def test_lint_with_custom_policy(self, image_metadata_passing, tmp_path):
        """Test linting with custom policy file."""
        # Create custom policy file
        policy_path = tmp_path / "custom.yaml"
        policy_path.write_text("""
name: custom-policy
version: "1.0.0"
description: Custom test policy

rules:
  - id: custom-001
    name: require-custom-label
    description: Must have custom label
    severity: warning
    category: metadata
    condition: "labels.get('custom.label') is not None"
""")

        image = NIMImage.from_metadata(image_metadata_passing)

        linter = PolicyLinter()
        policy = linter.load_policy(str(policy_path))
        result = linter.lint(image, policy=policy, include_builtin=False)

        # Should fail custom rule (no custom.label)
        custom_violations = [v for v in result.violations if v.rule.id == "custom-001"]
        assert len(custom_violations) == 1


class TestCompatWorkflow:
    """Integration tests for compatibility check workflow."""

    @pytest.fixture
    def image_metadata(self):
        """Create image metadata."""
        return ImageMetadata(
            reference="nvcr.io/nim/llama3:1.5.0",
            repository="nim/llama3",
            tag="1.5.0",
            digest=ImageDigest(hash="abc123"),
            labels={
                "com.nvidia.nim.model.name": "llama3-8b",
            },
            created=datetime(2024, 1, 1),
            architecture="amd64",
            os="linux",
            env={},
            manifest=ImageManifest(
                schema_version=2,
                media_type="application/vnd.docker.distribution.manifest.v2+json",
                digest=ImageDigest(hash="manifest1"),
                config_digest=ImageDigest(hash="config1"),
                layers=[],
            ),
        )

    def test_compat_check_a100(self, image_metadata):
        """Test compatibility check with A100 GPU."""
        image = NIMImage.from_metadata(image_metadata)

        checker = CompatChecker()
        result = checker.check(image, gpu="A100", driver_version="550.54.15")

        assert result.success
        assert result.report is not None
        # A100 should be compatible with most NIM images
        assert result.report.compatible

    def test_compat_check_older_gpu(self, image_metadata):
        """Test compatibility check with older GPU."""
        image = NIMImage.from_metadata(image_metadata)

        checker = CompatChecker()
        result = checker.check(image, gpu="V100", driver_version="450.00")

        assert result.success
        assert result.report is not None
        # May or may not be compatible depending on requirements


class TestCombinedWorkflow:
    """Integration tests combining multiple operations."""

    @pytest.fixture
    def metadata(self):
        """Create test image metadata."""
        return ImageMetadata(
            reference="nvcr.io/nim/llama3:1.5.0",
            repository="nim/llama3",
            tag="1.5.0",
            digest=ImageDigest(hash="abc123"),
            labels={
                "com.nvidia.nim.version": "1.5.0",
                "com.nvidia.nim.model.name": "llama3-8b",
            },
            created=datetime(2024, 1, 1),
            architecture="amd64",
            os="linux",
            nim_version="1.5.0",
            model_name="llama3-8b",
            env={"NIM_LOG_LEVEL": "INFO"},
            exposed_ports=[8000],
            raw_config={"Config": {"User": "nim"}},
            manifest=ImageManifest(
                schema_version=2,
                media_type="application/vnd.docker.distribution.manifest.v2+json",
                digest=ImageDigest(hash="manifest1"),
                config_digest=ImageDigest(hash="config1"),
                layers=[],
            ),
        )

    def test_lint_then_config(self, metadata):
        """Test lint followed by config analysis."""
        image = NIMImage.from_metadata(metadata)

        # First lint
        linter = PolicyLinter()
        lint_result = linter.lint(image)
        assert lint_result is not None

        # Then analyze config
        analyzer = ConfigAnalyzer()
        config_result = analyzer.analyze(image)
        assert config_result.success

    def test_compat_then_lint(self, metadata):
        """Test compat check followed by lint."""
        image = NIMImage.from_metadata(metadata)

        # First check compat
        checker = CompatChecker()
        compat_result = checker.check(image, gpu="A100")
        assert compat_result.success

        # Then lint
        linter = PolicyLinter()
        lint_result = linter.lint(image)
        assert lint_result is not None
