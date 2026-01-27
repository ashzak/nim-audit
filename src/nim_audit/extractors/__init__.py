"""Artifact extractors for NIM containers."""

from nim_audit.extractors.base import Extractor, ExtractorResult
from nim_audit.extractors.registry import ExtractorRegistry, get_default_registry
from nim_audit.extractors.metadata import MetadataExtractor
from nim_audit.extractors.model import ModelExtractor
from nim_audit.extractors.tokenizer import TokenizerExtractor
from nim_audit.extractors.api import APIExtractor
from nim_audit.extractors.runtime import RuntimeExtractor

__all__ = [
    "Extractor",
    "ExtractorResult",
    "ExtractorRegistry",
    "get_default_registry",
    "MetadataExtractor",
    "ModelExtractor",
    "TokenizerExtractor",
    "APIExtractor",
    "RuntimeExtractor",
]


def register_default_extractors(registry: ExtractorRegistry | None = None) -> ExtractorRegistry:
    """Register all default extractors with a registry.

    Args:
        registry: Optional registry to use. If None, uses the default registry.

    Returns:
        The registry with extractors registered
    """
    if registry is None:
        registry = get_default_registry()

    # Register extractors if not already registered
    extractors = [
        MetadataExtractor(),
        ModelExtractor(),
        TokenizerExtractor(),
        APIExtractor(),
        RuntimeExtractor(),
    ]

    for extractor in extractors:
        if extractor.name not in registry:
            registry.register(extractor)

    return registry
