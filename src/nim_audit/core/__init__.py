"""Core domain logic for nim-audit.

This module provides the main library API for auditing NIM containers.
"""

from nim_audit.core.image import NIMImage
from nim_audit.core.diff import DiffEngine
from nim_audit.core.config import ConfigAnalyzer
from nim_audit.core.compat import CompatChecker
from nim_audit.core.fingerprint import BehavioralFingerprinter
from nim_audit.core.lint import PolicyLinter

__all__ = [
    "NIMImage",
    "DiffEngine",
    "ConfigAnalyzer",
    "CompatChecker",
    "BehavioralFingerprinter",
    "PolicyLinter",
]
