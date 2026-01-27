"""GPU compatibility matrix for NIM containers."""

from typing import Any


def get_gpu_matrix() -> dict[str, dict[str, Any]]:
    """Get the GPU compatibility matrix.

    Returns:
        Dictionary mapping GPU names to their specifications
    """
    return {
        # NVIDIA Hopper Architecture (H Series)
        "H100": {
            "architecture": "Hopper",
            "compute_capability": "9.0",
            "memory_gb": 80,
            "tensor_cores": True,
            "fp8_support": True,
            "recommended_for": ["large_models", "high_throughput"],
        },
        "H100-80GB": {
            "architecture": "Hopper",
            "compute_capability": "9.0",
            "memory_gb": 80,
            "tensor_cores": True,
            "fp8_support": True,
            "recommended_for": ["large_models", "high_throughput"],
        },
        "H200": {
            "architecture": "Hopper",
            "compute_capability": "9.0",
            "memory_gb": 141,
            "tensor_cores": True,
            "fp8_support": True,
            "recommended_for": ["very_large_models", "high_throughput"],
        },
        # NVIDIA Ada Lovelace Architecture (L Series)
        "L40": {
            "architecture": "Ada Lovelace",
            "compute_capability": "8.9",
            "memory_gb": 48,
            "tensor_cores": True,
            "fp8_support": True,
            "recommended_for": ["inference", "mixed_workloads"],
        },
        "L40S": {
            "architecture": "Ada Lovelace",
            "compute_capability": "8.9",
            "memory_gb": 48,
            "tensor_cores": True,
            "fp8_support": True,
            "recommended_for": ["inference", "mixed_workloads"],
        },
        "L4": {
            "architecture": "Ada Lovelace",
            "compute_capability": "8.9",
            "memory_gb": 24,
            "tensor_cores": True,
            "fp8_support": True,
            "recommended_for": ["small_models", "cost_effective"],
        },
        # NVIDIA Ampere Architecture (A Series)
        "A100": {
            "architecture": "Ampere",
            "compute_capability": "8.0",
            "memory_gb": 80,
            "tensor_cores": True,
            "fp8_support": False,
            "recommended_for": ["large_models", "training_inference"],
        },
        "A100-80GB": {
            "architecture": "Ampere",
            "compute_capability": "8.0",
            "memory_gb": 80,
            "tensor_cores": True,
            "fp8_support": False,
            "recommended_for": ["large_models", "training_inference"],
        },
        "A100-40GB": {
            "architecture": "Ampere",
            "compute_capability": "8.0",
            "memory_gb": 40,
            "tensor_cores": True,
            "fp8_support": False,
            "recommended_for": ["medium_models", "training_inference"],
        },
        "A10": {
            "architecture": "Ampere",
            "compute_capability": "8.6",
            "memory_gb": 24,
            "tensor_cores": True,
            "fp8_support": False,
            "recommended_for": ["inference", "small_medium_models"],
        },
        "A10G": {
            "architecture": "Ampere",
            "compute_capability": "8.6",
            "memory_gb": 24,
            "tensor_cores": True,
            "fp8_support": False,
            "recommended_for": ["inference", "cloud_deployments"],
        },
        "A30": {
            "architecture": "Ampere",
            "compute_capability": "8.0",
            "memory_gb": 24,
            "tensor_cores": True,
            "fp8_support": False,
            "recommended_for": ["inference", "enterprise"],
        },
        "A40": {
            "architecture": "Ampere",
            "compute_capability": "8.6",
            "memory_gb": 48,
            "tensor_cores": True,
            "fp8_support": False,
            "recommended_for": ["medium_models", "professional"],
        },
        "A6000": {
            "architecture": "Ampere",
            "compute_capability": "8.6",
            "memory_gb": 48,
            "tensor_cores": True,
            "fp8_support": False,
            "recommended_for": ["professional", "workstation"],
        },
        # NVIDIA Turing Architecture (T Series)
        "T4": {
            "architecture": "Turing",
            "compute_capability": "7.5",
            "memory_gb": 16,
            "tensor_cores": True,
            "fp8_support": False,
            "recommended_for": ["small_models", "cost_effective", "inference"],
        },
        # NVIDIA Volta Architecture (V Series)
        "V100": {
            "architecture": "Volta",
            "compute_capability": "7.0",
            "memory_gb": 32,
            "tensor_cores": True,
            "fp8_support": False,
            "recommended_for": ["legacy", "small_medium_models"],
        },
        "V100-32GB": {
            "architecture": "Volta",
            "compute_capability": "7.0",
            "memory_gb": 32,
            "tensor_cores": True,
            "fp8_support": False,
            "recommended_for": ["legacy", "small_medium_models"],
        },
        "V100-16GB": {
            "architecture": "Volta",
            "compute_capability": "7.0",
            "memory_gb": 16,
            "tensor_cores": True,
            "fp8_support": False,
            "recommended_for": ["legacy", "small_models"],
        },
        # Consumer GPUs (for development/testing)
        "RTX 4090": {
            "architecture": "Ada Lovelace",
            "compute_capability": "8.9",
            "memory_gb": 24,
            "tensor_cores": True,
            "fp8_support": True,
            "recommended_for": ["development", "small_models"],
        },
        "RTX 3090": {
            "architecture": "Ampere",
            "compute_capability": "8.6",
            "memory_gb": 24,
            "tensor_cores": True,
            "fp8_support": False,
            "recommended_for": ["development", "small_models"],
        },
    }


def get_min_requirements() -> dict[str, Any]:
    """Get minimum GPU requirements for NIM.

    Returns:
        Dictionary with minimum requirements
    """
    return {
        "min_compute_capability": "7.0",
        "min_memory_gb": 8,
        "tensor_cores_recommended": True,
        "min_driver_version": "525.60",
        "min_cuda_version": "12.0",
    }


def get_recommended_gpus_for_model_size(params_billions: float) -> list[str]:
    """Get recommended GPUs for a model size.

    Args:
        params_billions: Model size in billions of parameters

    Returns:
        List of recommended GPU names
    """
    if params_billions >= 70:
        return ["H100", "H200", "A100-80GB"]
    elif params_billions >= 30:
        return ["H100", "A100-80GB", "A100-40GB", "L40S"]
    elif params_billions >= 13:
        return ["A100", "L40", "L40S", "A10", "A40"]
    elif params_billions >= 7:
        return ["A100", "L40", "A10", "L4", "T4"]
    else:
        return ["L4", "T4", "A10", "L40"]
