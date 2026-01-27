"""Shared test fixtures for nim-audit tests."""

from datetime import datetime
from typing import Any

import pytest

from nim_audit.models.image import ImageDigest, ImageManifest, ImageMetadata, LayerInfo
from nim_audit.core.image import NIMImage


@pytest.fixture
def sample_image_metadata() -> ImageMetadata:
    """Create sample image metadata for testing."""
    return ImageMetadata(
        reference="nvcr.io/nim/llama3:1.5.0",
        repository="nim/llama3",
        tag="1.5.0",
        digest=ImageDigest(hash="abc123def456"),
        labels={
            "com.nvidia.nim.version": "1.5.0",
            "com.nvidia.nim.model.name": "llama3-8b",
            "com.nvidia.nim.model.version": "1.0.0",
            "com.nvidia.nim.model.quantization": "fp16",
        },
        created=datetime(2024, 1, 15, 12, 0, 0),
        architecture="amd64",
        os="linux",
        nim_version="1.5.0",
        model_name="llama3-8b",
        model_version="1.0.0",
        quantization="fp16",
        env={
            "NIM_SERVER_PORT": "8000",
            "NIM_LOG_LEVEL": "INFO",
            "NIM_MAX_BATCH_SIZE": "8",
        },
        exposed_ports=[8000],
        entrypoint=["/opt/nim/start.sh"],
        cmd=[],
        manifest=ImageManifest(
            schema_version=2,
            media_type="application/vnd.docker.distribution.manifest.v2+json",
            digest=ImageDigest(hash="manifest123"),
            config_digest=ImageDigest(hash="config123"),
            layers=[
                LayerInfo(
                    digest=ImageDigest(hash="layer1"),
                    size=1000000,
                    media_type="application/vnd.docker.image.rootfs.diff.tar.gzip",
                ),
                LayerInfo(
                    digest=ImageDigest(hash="layer2"),
                    size=2000000,
                    media_type="application/vnd.docker.image.rootfs.diff.tar.gzip",
                ),
            ],
        ),
    )


@pytest.fixture
def sample_image_metadata_v2() -> ImageMetadata:
    """Create sample image metadata for a newer version."""
    return ImageMetadata(
        reference="nvcr.io/nim/llama3:1.6.0",
        repository="nim/llama3",
        tag="1.6.0",
        digest=ImageDigest(hash="xyz789uvw012"),
        labels={
            "com.nvidia.nim.version": "1.6.0",
            "com.nvidia.nim.model.name": "llama3-8b",
            "com.nvidia.nim.model.version": "1.1.0",
            "com.nvidia.nim.model.quantization": "int8",
        },
        created=datetime(2024, 2, 1, 12, 0, 0),
        architecture="amd64",
        os="linux",
        nim_version="1.6.0",
        model_name="llama3-8b",
        model_version="1.1.0",
        quantization="int8",
        env={
            "NIM_SERVER_PORT": "8000",
            "NIM_LOG_LEVEL": "INFO",
            "NIM_MAX_BATCH_SIZE": "16",
            "NIM_ENABLE_PREFIX_CACHING": "true",
        },
        exposed_ports=[8000, 8080],
        entrypoint=["/opt/nim/start.sh"],
        cmd=[],
        manifest=ImageManifest(
            schema_version=2,
            media_type="application/vnd.docker.distribution.manifest.v2+json",
            digest=ImageDigest(hash="manifest456"),
            config_digest=ImageDigest(hash="config456"),
            layers=[
                LayerInfo(
                    digest=ImageDigest(hash="layer1"),
                    size=1000000,
                    media_type="application/vnd.docker.image.rootfs.diff.tar.gzip",
                ),
                LayerInfo(
                    digest=ImageDigest(hash="layer3"),
                    size=2500000,
                    media_type="application/vnd.docker.image.rootfs.diff.tar.gzip",
                ),
            ],
        ),
    )


@pytest.fixture
def sample_nim_image(sample_image_metadata: ImageMetadata) -> NIMImage:
    """Create a sample NIMImage for testing."""
    return NIMImage.from_metadata(sample_image_metadata)


@pytest.fixture
def sample_nim_image_v2(sample_image_metadata_v2: ImageMetadata) -> NIMImage:
    """Create a sample NIMImage v2 for testing."""
    return NIMImage.from_metadata(sample_image_metadata_v2)


@pytest.fixture
def sample_env_file(tmp_path) -> str:
    """Create a sample .env file for testing."""
    env_content = """
# NIM Configuration
NIM_SERVER_PORT=8000
NIM_LOG_LEVEL=DEBUG
NIM_MAX_BATCH_SIZE=32
NIM_GPU_MEMORY_UTILIZATION=0.9

# Quoted values
NIM_MODEL_NAME="llama3-8b"
"""
    env_file = tmp_path / "test.env"
    env_file.write_text(env_content)
    return str(env_file)


@pytest.fixture
def sample_policy_file(tmp_path) -> str:
    """Create a sample policy YAML file for testing."""
    policy_content = """
name: test-policy
version: "1.0.0"
description: Test policy for nim-audit

rules:
  - id: test-001
    name: require-model-label
    description: Images must have a model name label
    severity: error
    category: metadata
    condition: "labels.get('com.nvidia.nim.model.name') is not None"
    rationale: Model name is required for tracking
    remediation: Add com.nvidia.nim.model.name label

  - id: test-002
    name: check-batch-size
    description: Batch size should be reasonable
    severity: warning
    category: configuration
    condition: "int(env.get('NIM_MAX_BATCH_SIZE', '1')) <= 64"
    rationale: Very large batch sizes may cause memory issues
    remediation: Reduce NIM_MAX_BATCH_SIZE to 64 or less
"""
    policy_file = tmp_path / "test-policy.yaml"
    policy_file.write_text(policy_content)
    return str(policy_file)
