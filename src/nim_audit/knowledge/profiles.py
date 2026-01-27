"""Optimized profiles for NIM deployments."""

from typing import Any


def get_profiles() -> dict[str, dict[str, Any]]:
    """Get optimized configuration profiles.

    Returns:
        Dictionary mapping profile names to their configurations
    """
    return {
        "high-throughput": {
            "name": "High Throughput",
            "description": "Optimized for maximum requests per second",
            "use_case": "Production deployments with high concurrency",
            "env": {
                "NIM_MAX_BATCH_SIZE": "32",
                "NIM_MAX_CONCURRENT_REQUESTS": "64",
                "NIM_GPU_MEMORY_UTILIZATION": "0.95",
                "NIM_ENABLE_CHUNKED_PREFILL": "true",
                "NIM_ENABLE_PREFIX_CACHING": "true",
            },
            "requirements": {
                "min_memory_gb": 40,
                "recommended_gpus": ["H100", "A100-80GB"],
            },
        },
        "low-latency": {
            "name": "Low Latency",
            "description": "Optimized for fastest time-to-first-token",
            "use_case": "Interactive applications requiring fast responses",
            "env": {
                "NIM_MAX_BATCH_SIZE": "1",
                "NIM_MAX_CONCURRENT_REQUESTS": "8",
                "NIM_GPU_MEMORY_UTILIZATION": "0.85",
                "NIM_ENABLE_CHUNKED_PREFILL": "false",
            },
            "requirements": {
                "min_memory_gb": 24,
                "recommended_gpus": ["H100", "L40S", "A10"],
            },
        },
        "memory-efficient": {
            "name": "Memory Efficient",
            "description": "Optimized for running larger models on smaller GPUs",
            "use_case": "Resource-constrained environments",
            "env": {
                "NIM_MAX_BATCH_SIZE": "4",
                "NIM_MAX_CONCURRENT_REQUESTS": "8",
                "NIM_GPU_MEMORY_UTILIZATION": "0.9",
                "NIM_QUANTIZATION": "int8",
                "NIM_KV_CACHE_DTYPE": "fp8",
                "NIM_SWAP_SPACE": "4",
            },
            "requirements": {
                "min_memory_gb": 16,
                "recommended_gpus": ["L4", "T4", "A10"],
            },
        },
        "balanced": {
            "name": "Balanced",
            "description": "Balanced configuration for general use",
            "use_case": "Default production configuration",
            "env": {
                "NIM_MAX_BATCH_SIZE": "8",
                "NIM_MAX_CONCURRENT_REQUESTS": "16",
                "NIM_GPU_MEMORY_UTILIZATION": "0.9",
                "NIM_ENABLE_CHUNKED_PREFILL": "true",
            },
            "requirements": {
                "min_memory_gb": 24,
                "recommended_gpus": ["H100", "A100", "L40", "A10"],
            },
        },
        "development": {
            "name": "Development",
            "description": "Configuration for development and testing",
            "use_case": "Local development and debugging",
            "env": {
                "NIM_MAX_BATCH_SIZE": "1",
                "NIM_MAX_CONCURRENT_REQUESTS": "4",
                "NIM_GPU_MEMORY_UTILIZATION": "0.7",
                "NIM_LOG_LEVEL": "DEBUG",
                "NIM_METRICS_ENABLED": "true",
            },
            "requirements": {
                "min_memory_gb": 8,
                "recommended_gpus": ["RTX 4090", "RTX 3090", "T4"],
            },
        },
        "multi-gpu": {
            "name": "Multi-GPU",
            "description": "Configuration for multi-GPU tensor parallelism",
            "use_case": "Large model inference across multiple GPUs",
            "env": {
                "NIM_TENSOR_PARALLEL_SIZE": "2",
                "NIM_MAX_BATCH_SIZE": "16",
                "NIM_MAX_CONCURRENT_REQUESTS": "32",
                "NIM_GPU_MEMORY_UTILIZATION": "0.9",
            },
            "requirements": {
                "min_gpus": 2,
                "min_memory_gb": 48,
                "recommended_gpus": ["H100", "A100-80GB"],
            },
        },
        "cost-optimized": {
            "name": "Cost Optimized",
            "description": "Configuration optimized for cloud cost efficiency",
            "use_case": "Cloud deployments with cost constraints",
            "env": {
                "NIM_MAX_BATCH_SIZE": "16",
                "NIM_MAX_CONCURRENT_REQUESTS": "32",
                "NIM_GPU_MEMORY_UTILIZATION": "0.95",
                "NIM_QUANTIZATION": "int8",
                "NIM_ENABLE_PREFIX_CACHING": "true",
            },
            "requirements": {
                "min_memory_gb": 16,
                "recommended_gpus": ["L4", "T4", "A10G"],
            },
        },
    }


def get_profile(name: str) -> dict[str, Any] | None:
    """Get a specific profile by name.

    Args:
        name: Profile name

    Returns:
        Profile configuration or None if not found
    """
    return get_profiles().get(name)


def suggest_profile(
    model_size_gb: float,
    gpu_memory_gb: float,
    priority: str = "balanced",
) -> str:
    """Suggest a profile based on requirements.

    Args:
        model_size_gb: Model size in GB
        gpu_memory_gb: Available GPU memory in GB
        priority: Priority ("throughput", "latency", "memory", "balanced")

    Returns:
        Suggested profile name
    """
    memory_ratio = model_size_gb / gpu_memory_gb

    if memory_ratio > 0.8:
        return "memory-efficient"

    if priority == "throughput":
        return "high-throughput"
    elif priority == "latency":
        return "low-latency"
    elif priority == "memory":
        return "memory-efficient"
    else:
        return "balanced"
