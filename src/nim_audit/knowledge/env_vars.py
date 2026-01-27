"""Knowledge base for NIM environment variables."""

from typing import Any


def get_env_var_knowledge() -> dict[str, dict[str, Any]]:
    """Get the knowledge base of NIM environment variables.

    Returns:
        Dictionary mapping env var names to their metadata
    """
    return {
        # Core NIM Configuration
        "NIM_SERVER_PORT": {
            "description": "Port for the NIM server to listen on",
            "default": "8000",
            "impact": {
                "level": "low",
                "description": "Changes the network port for API access",
                "affects": ["networking"],
            },
            "validation_pattern": r"^\d+$",
        },
        "NIM_LOG_LEVEL": {
            "description": "Logging verbosity level",
            "default": "INFO",
            "valid_values": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            "impact": {
                "level": "low",
                "description": "Affects logging output volume",
                "affects": ["logging", "disk"],
            },
        },
        "NIM_MODEL_NAME": {
            "description": "Name of the model to serve",
            "impact": {
                "level": "critical",
                "description": "Determines which model is loaded",
                "affects": ["model", "memory", "performance"],
            },
            "required": True,
        },
        # Performance Tuning
        "NIM_MAX_BATCH_SIZE": {
            "description": "Maximum batch size for inference requests",
            "default": "1",
            "impact": {
                "level": "high",
                "description": "Higher values increase throughput but require more memory",
                "affects": ["performance", "memory", "latency"],
            },
            "validation_pattern": r"^\d+$",
        },
        "NIM_MAX_CONCURRENT_REQUESTS": {
            "description": "Maximum number of concurrent requests",
            "default": "10",
            "impact": {
                "level": "high",
                "description": "Limits parallel request processing",
                "affects": ["performance", "memory"],
            },
            "validation_pattern": r"^\d+$",
        },
        "NIM_TENSOR_PARALLEL_SIZE": {
            "description": "Number of GPUs for tensor parallelism",
            "default": "1",
            "impact": {
                "level": "critical",
                "description": "Distributes model across multiple GPUs",
                "affects": ["performance", "memory", "hardware"],
            },
            "validation_pattern": r"^\d+$",
        },
        "NIM_PIPELINE_PARALLEL_SIZE": {
            "description": "Number of GPUs for pipeline parallelism",
            "default": "1",
            "impact": {
                "level": "critical",
                "description": "Distributes model layers across GPUs",
                "affects": ["performance", "memory", "hardware"],
            },
            "validation_pattern": r"^\d+$",
        },
        # Memory Configuration
        "NIM_GPU_MEMORY_UTILIZATION": {
            "description": "Fraction of GPU memory to use (0.0-1.0)",
            "default": "0.9",
            "impact": {
                "level": "high",
                "description": "Controls GPU memory allocation",
                "affects": ["memory", "performance"],
            },
            "validation_pattern": r"^0?\.\d+|1\.0$",
        },
        "NIM_MAX_MODEL_LEN": {
            "description": "Maximum sequence length for the model",
            "impact": {
                "level": "high",
                "description": "Limits context window size, affects memory",
                "affects": ["memory", "performance", "capabilities"],
            },
            "validation_pattern": r"^\d+$",
        },
        "NIM_SWAP_SPACE": {
            "description": "CPU swap space in GB for KV cache offloading",
            "default": "0",
            "impact": {
                "level": "medium",
                "description": "Enables KV cache offloading to CPU",
                "affects": ["memory", "performance"],
            },
            "validation_pattern": r"^\d+$",
        },
        # Quantization
        "NIM_QUANTIZATION": {
            "description": "Quantization method to use",
            "valid_values": ["none", "fp8", "int8", "int4", "awq", "gptq"],
            "impact": {
                "level": "critical",
                "description": "Affects model precision, memory, and quality",
                "affects": ["memory", "performance", "accuracy"],
            },
        },
        "NIM_KV_CACHE_DTYPE": {
            "description": "Data type for KV cache",
            "valid_values": ["auto", "fp8", "fp16", "bf16"],
            "impact": {
                "level": "medium",
                "description": "Affects KV cache memory usage",
                "affects": ["memory", "performance"],
            },
        },
        # API Configuration
        "NIM_ENABLE_CHUNKED_PREFILL": {
            "description": "Enable chunked prefill for long sequences",
            "default": "true",
            "valid_values": ["true", "false"],
            "impact": {
                "level": "medium",
                "description": "Improves long sequence handling",
                "affects": ["performance", "latency"],
            },
        },
        "NIM_ENABLE_PREFIX_CACHING": {
            "description": "Enable prefix caching for repeated prompts",
            "default": "false",
            "valid_values": ["true", "false"],
            "impact": {
                "level": "medium",
                "description": "Speeds up repeated prompt prefixes",
                "affects": ["performance", "memory"],
            },
        },
        # Deprecated Variables
        "NIM_BATCH_SIZE": {
            "description": "Deprecated: Use NIM_MAX_BATCH_SIZE instead",
            "deprecated": True,
            "deprecated_message": "Use NIM_MAX_BATCH_SIZE instead",
            "impact": {
                "level": "low",
                "description": "Legacy batch size setting",
                "affects": ["performance"],
            },
        },
        # Health and Monitoring
        "NIM_HEALTH_CHECK_INTERVAL": {
            "description": "Interval for health checks in seconds",
            "default": "30",
            "impact": {
                "level": "low",
                "description": "Frequency of internal health checks",
                "affects": ["monitoring"],
            },
            "validation_pattern": r"^\d+$",
        },
        "NIM_METRICS_ENABLED": {
            "description": "Enable Prometheus metrics endpoint",
            "default": "true",
            "valid_values": ["true", "false"],
            "impact": {
                "level": "low",
                "description": "Enables /metrics endpoint",
                "affects": ["monitoring"],
            },
        },
        # Security
        "NIM_API_KEY": {
            "description": "API key for authentication",
            "impact": {
                "level": "high",
                "description": "Enables API authentication",
                "affects": ["security"],
            },
        },
        "NIM_DISABLE_LOG_REQUESTS": {
            "description": "Disable request logging",
            "default": "false",
            "valid_values": ["true", "false"],
            "impact": {
                "level": "low",
                "description": "Reduces log output, may hide sensitive data",
                "affects": ["logging", "security"],
            },
        },
    }
