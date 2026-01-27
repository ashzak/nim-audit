"""Artifact extractors for NIM containers."""

from nim_audit.extractors.base import Extractor, ExtractorResult
from nim_audit.extractors.registry import ExtractorRegistry

__all__ = [
    "Extractor",
    "ExtractorResult",
    "ExtractorRegistry",
]
