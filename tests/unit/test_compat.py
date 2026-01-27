"""Unit tests for the CompatChecker."""

import pytest

from nim_audit.core.compat import CompatChecker
from nim_audit.core.image import NIMImage
from nim_audit.models.image import ImageMetadata, ImageDigest


class TestCompatChecker:
    """Tests for CompatChecker."""

    def test_check_basic(self, sample_nim_image: NIMImage):
        """Test basic compatibility check."""
        checker = CompatChecker()
        result = checker.check(sample_nim_image, gpu="A100")

        assert result.success
        assert result.report is not None

    def test_check_with_driver(self, sample_nim_image: NIMImage):
        """Test compatibility check with driver version."""
        checker = CompatChecker()
        result = checker.check(
            sample_nim_image,
            gpu="A100",
            driver_version="550.54",
        )

        assert result.success
        assert result.report is not None
        assert result.report.driver_version == "550.54"

    def test_check_gpu_info(self, sample_nim_image: NIMImage):
        """Test that GPU info is retrieved correctly."""
        checker = CompatChecker()
        result = checker.check(sample_nim_image, gpu="H100")

        assert result.success
        assert result.report is not None
        assert result.report.gpu is not None
        assert result.report.gpu.name == "H100"
        assert result.report.gpu.architecture == "Hopper"
        assert result.report.gpu.compute_capability == "9.0"

    def test_check_unknown_gpu(self, sample_nim_image: NIMImage):
        """Test check with unknown GPU."""
        checker = CompatChecker()
        result = checker.check(sample_nim_image, gpu="UNKNOWN_GPU")

        assert result.success
        assert result.report is not None
        assert result.report.gpu is not None
        assert result.report.gpu.name == "UNKNOWN_GPU"

    def test_version_comparison(self):
        """Test version comparison logic."""
        checker = CompatChecker()

        assert checker._version_gte("9.0", "8.0")
        assert checker._version_gte("8.0", "8.0")
        assert not checker._version_gte("7.5", "8.0")
        assert checker._version_gte("550.54", "525.60")
        assert checker._version_gte("12.0.1", "12.0")

    def test_compatibility_with_requirements(self):
        """Test compatibility with image requirements."""
        # Create image with explicit requirements
        metadata = ImageMetadata(
            reference="test/image:1.0",
            repository="test/image",
            tag="1.0",
            labels={
                "com.nvidia.nim.gpu.compute_capability": "8.0",
                "com.nvidia.nim.gpu.memory_gb": "24",
                "com.nvidia.nim.driver.version": "525.60",
            },
        )
        image = NIMImage.from_metadata(metadata)

        checker = CompatChecker()

        # Compatible GPU
        result = checker.check(image, gpu="A100", driver_version="550.54")
        assert result.success
        assert result.report is not None
        assert result.report.compatible

        # Incompatible driver (too old)
        result = checker.check(image, gpu="A100", driver_version="500.0")
        assert result.success
        assert result.report is not None
        assert not result.report.driver_compatible

    def test_compatibility_issues_list(self, sample_nim_image: NIMImage):
        """Test that compatibility issues are listed."""
        checker = CompatChecker()
        result = checker.check(sample_nim_image, gpu="A100")

        assert result.success
        assert result.report is not None
        # Should be a list (possibly empty)
        assert isinstance(result.report.compatibility_issues, list)


class TestGPUMatrix:
    """Tests for the GPU matrix knowledge base."""

    def test_get_gpu_matrix(self):
        """Test that GPU matrix is accessible."""
        from nim_audit.knowledge.gpu_matrix import get_gpu_matrix

        matrix = get_gpu_matrix()
        assert "H100" in matrix
        assert "A100" in matrix
        assert "T4" in matrix

    def test_gpu_info_complete(self):
        """Test that GPU info is complete."""
        from nim_audit.knowledge.gpu_matrix import get_gpu_matrix

        matrix = get_gpu_matrix()

        for gpu_name, info in matrix.items():
            assert "architecture" in info
            assert "compute_capability" in info
            assert "memory_gb" in info

    def test_recommended_gpus_for_model_size(self):
        """Test GPU recommendations by model size."""
        from nim_audit.knowledge.gpu_matrix import get_recommended_gpus_for_model_size

        # Large model
        large_gpus = get_recommended_gpus_for_model_size(70)
        assert "H100" in large_gpus or "H200" in large_gpus

        # Small model
        small_gpus = get_recommended_gpus_for_model_size(3)
        assert "T4" in small_gpus or "L4" in small_gpus
