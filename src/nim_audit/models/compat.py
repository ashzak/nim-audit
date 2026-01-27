"""GPU compatibility data models."""

from pydantic import BaseModel, Field

from nim_audit.models.common import AuditError


class GPUInfo(BaseModel):
    """Information about a GPU."""

    model_config = {"frozen": True}

    name: str = Field(description="GPU name (e.g., 'A100', 'H100')")
    compute_capability: str | None = Field(
        default=None,
        description="CUDA compute capability (e.g., '8.0')",
    )
    memory_gb: float | None = Field(default=None, description="GPU memory in GB")
    architecture: str | None = Field(
        default=None,
        description="GPU architecture (e.g., 'Ampere', 'Hopper')",
    )


class GPURequirements(BaseModel):
    """GPU requirements for a NIM image."""

    model_config = {"frozen": True}

    min_compute_capability: str | None = Field(
        default=None,
        description="Minimum CUDA compute capability",
    )
    min_memory_gb: float | None = Field(default=None, description="Minimum GPU memory in GB")
    min_driver_version: str | None = Field(default=None, description="Minimum NVIDIA driver version")
    supported_gpus: list[str] = Field(
        default_factory=list,
        description="Explicitly supported GPU models",
    )
    supported_architectures: list[str] = Field(
        default_factory=list,
        description="Supported GPU architectures",
    )
    tensor_cores_required: bool = Field(
        default=False,
        description="Whether tensor cores are required",
    )


class CompatReport(BaseModel):
    """GPU compatibility report."""

    model_config = {"frozen": True}

    image_reference: str = Field(description="Image that was checked")
    requirements: GPURequirements = Field(description="Image GPU requirements")
    gpu: GPUInfo | None = Field(default=None, description="Target GPU info")
    driver_version: str | None = Field(default=None, description="NVIDIA driver version")
    cuda_version: str | None = Field(default=None, description="CUDA version")

    # Compatibility results
    compatible: bool = Field(description="Overall compatibility result")
    compute_compatible: bool = Field(default=True, description="Compute capability compatible")
    memory_compatible: bool = Field(default=True, description="Memory requirement met")
    driver_compatible: bool = Field(default=True, description="Driver version compatible")
    gpu_supported: bool = Field(default=True, description="GPU explicitly supported")

    # Warnings and recommendations
    warnings: list[str] = Field(default_factory=list, description="Compatibility warnings")
    recommendations: list[str] = Field(
        default_factory=list,
        description="Recommendations for optimal performance",
    )

    @property
    def compatibility_issues(self) -> list[str]:
        """Get list of compatibility issues."""
        issues = []
        if not self.compute_compatible:
            issues.append("Compute capability below minimum requirement")
        if not self.memory_compatible:
            issues.append("GPU memory below minimum requirement")
        if not self.driver_compatible:
            issues.append("NVIDIA driver version below minimum requirement")
        if not self.gpu_supported:
            issues.append("GPU not in explicitly supported list")
        return issues


class CompatResult(BaseModel):
    """Result of a compatibility check operation."""

    model_config = {"frozen": True}

    success: bool = Field(description="Whether the check succeeded")
    report: CompatReport | None = Field(
        default=None,
        description="The compatibility report if successful",
    )
    errors: list[AuditError] = Field(default_factory=list, description="Errors that occurred")

    @classmethod
    def ok(cls, report: CompatReport) -> "CompatResult":
        """Create a successful result."""
        return cls(success=True, report=report)

    @classmethod
    def fail(cls, errors: list[AuditError]) -> "CompatResult":
        """Create a failed result."""
        return cls(success=False, errors=errors)
