"""CompatChecker for GPU compatibility analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nim_audit.models.common import AuditError
from nim_audit.models.compat import (
    CompatReport,
    CompatResult,
    GPUInfo,
    GPURequirements,
)

if TYPE_CHECKING:
    from nim_audit.core.image import NIMImage


class CompatChecker:
    """Checker for GPU compatibility with NIM containers.

    The CompatChecker analyzes GPU requirements for NIM containers
    and validates them against target GPU configurations.

    Example:
        checker = CompatChecker()
        result = checker.check(
            image,
            gpu="A100",
            driver_version="550.54",
        )

        if result.success:
            print(f"Compatible: {result.report.compatible}")
            for warning in result.report.warnings:
                print(f"Warning: {warning}")
    """

    def __init__(self) -> None:
        """Initialize the compatibility checker."""
        # Import knowledge base lazily
        from nim_audit.knowledge.gpu_matrix import get_gpu_matrix

        self._gpu_matrix = get_gpu_matrix()

    def check(
        self,
        image: "NIMImage",
        gpu: str | None = None,
        driver_version: str | None = None,
        cuda_version: str | None = None,
    ) -> CompatResult:
        """Check GPU compatibility for a NIM image.

        Args:
            image: The NIM image to check
            gpu: Target GPU name (e.g., "A100", "H100")
            driver_version: NVIDIA driver version
            cuda_version: CUDA version

        Returns:
            CompatResult with compatibility report or errors
        """
        try:
            # Extract requirements from image
            requirements = self._extract_requirements(image)

            # Get GPU info
            gpu_info = None
            if gpu:
                gpu_info = self._get_gpu_info(gpu)

            # Perform compatibility checks
            compute_compatible = True
            memory_compatible = True
            driver_compatible = True
            gpu_supported = True
            warnings: list[str] = []
            recommendations: list[str] = []

            # Check compute capability
            if gpu_info and requirements.min_compute_capability:
                if gpu_info.compute_capability:
                    if not self._version_gte(
                        gpu_info.compute_capability,
                        requirements.min_compute_capability,
                    ):
                        compute_compatible = False

            # Check memory
            if gpu_info and requirements.min_memory_gb:
                if gpu_info.memory_gb and gpu_info.memory_gb < requirements.min_memory_gb:
                    memory_compatible = False
                    warnings.append(
                        f"GPU has {gpu_info.memory_gb}GB memory, "
                        f"but {requirements.min_memory_gb}GB is required"
                    )

            # Check driver version
            if driver_version and requirements.min_driver_version:
                if not self._version_gte(driver_version, requirements.min_driver_version):
                    driver_compatible = False
                    warnings.append(
                        f"Driver version {driver_version} is below "
                        f"minimum {requirements.min_driver_version}"
                    )

            # Check GPU support list
            if gpu and requirements.supported_gpus:
                gpu_upper = gpu.upper()
                supported_upper = [g.upper() for g in requirements.supported_gpus]
                if gpu_upper not in supported_upper:
                    gpu_supported = False
                    warnings.append(
                        f"GPU {gpu} not in explicitly supported list: "
                        f"{', '.join(requirements.supported_gpus)}"
                    )

            # Overall compatibility
            compatible = all(
                [compute_compatible, memory_compatible, driver_compatible, gpu_supported]
            )

            # Add recommendations
            if not compatible:
                if not compute_compatible:
                    recommendations.append(
                        f"Upgrade to a GPU with compute capability >= "
                        f"{requirements.min_compute_capability}"
                    )
                if not driver_compatible:
                    recommendations.append(
                        f"Upgrade NVIDIA driver to >= {requirements.min_driver_version}"
                    )
                if not memory_compatible:
                    recommendations.append(
                        f"Use a GPU with >= {requirements.min_memory_gb}GB memory"
                    )

            report = CompatReport(
                image_reference=image.reference,
                requirements=requirements,
                gpu=gpu_info,
                driver_version=driver_version,
                cuda_version=cuda_version,
                compatible=compatible,
                compute_compatible=compute_compatible,
                memory_compatible=memory_compatible,
                driver_compatible=driver_compatible,
                gpu_supported=gpu_supported,
                warnings=warnings,
                recommendations=recommendations,
            )

            return CompatResult.ok(report)

        except Exception as e:
            return CompatResult.fail(
                [
                    AuditError(
                        code="COMPAT_ERROR",
                        message=f"Failed to check compatibility: {e}",
                        details={"image": image.reference, "gpu": gpu},
                    )
                ]
            )

    def _extract_requirements(self, image: "NIMImage") -> GPURequirements:
        """Extract GPU requirements from image metadata."""
        labels = image.metadata.labels

        # Try to extract from labels
        min_compute = labels.get("com.nvidia.nim.gpu.compute_capability")
        min_memory = labels.get("com.nvidia.nim.gpu.memory_gb")
        min_driver = labels.get("com.nvidia.nim.driver.version")
        supported_gpus = labels.get("com.nvidia.nim.gpu.supported", "").split(",")
        supported_gpus = [g.strip() for g in supported_gpus if g.strip()]

        # Also check environment for hints
        env = image.metadata.env
        if not min_memory and "NIM_GPU_MEMORY" in env:
            try:
                min_memory = env["NIM_GPU_MEMORY"]
            except (ValueError, TypeError):
                pass

        return GPURequirements(
            min_compute_capability=min_compute,
            min_memory_gb=float(min_memory) if min_memory else None,
            min_driver_version=min_driver,
            supported_gpus=supported_gpus,
            supported_architectures=[],
            tensor_cores_required=False,
        )

    def _get_gpu_info(self, gpu_name: str) -> GPUInfo:
        """Get GPU information from the knowledge base."""
        gpu_upper = gpu_name.upper()

        # Look up in matrix
        if gpu_upper in self._gpu_matrix:
            info = self._gpu_matrix[gpu_upper]
            return GPUInfo(
                name=gpu_name,
                compute_capability=info.get("compute_capability"),
                memory_gb=info.get("memory_gb"),
                architecture=info.get("architecture"),
            )

        # Return basic info for unknown GPUs
        return GPUInfo(name=gpu_name)

    def _version_gte(self, version: str, min_version: str) -> bool:
        """Check if version >= min_version.

        Handles versions like "8.0", "550.54", etc.
        """
        try:
            v_parts = [int(x) for x in version.split(".")]
            m_parts = [int(x) for x in min_version.split(".")]

            # Pad to same length
            while len(v_parts) < len(m_parts):
                v_parts.append(0)
            while len(m_parts) < len(v_parts):
                m_parts.append(0)

            return v_parts >= m_parts
        except (ValueError, TypeError):
            # If we can't parse, assume compatible
            return True

    def check_cluster(
        self,
        image: "NIMImage",
        kubeconfig: str | None = None,
        namespace: str | None = None,
    ) -> list[CompatResult]:
        """Check compatibility across all GPUs in a Kubernetes cluster.

        Args:
            image: The NIM image to check
            kubeconfig: Path to kubeconfig file
            namespace: Kubernetes namespace to check

        Returns:
            List of CompatResult, one per node with GPUs
        """
        results: list[CompatResult] = []

        try:
            # This would use kubectl or kubernetes client
            # For now, return empty list as placeholder
            pass
        except Exception as e:
            results.append(
                CompatResult.fail(
                    [
                        AuditError(
                            code="CLUSTER_ERROR",
                            message=f"Failed to check cluster: {e}",
                        )
                    ]
                )
            )

        return results
