"""Core domain logic for nim-audit.

This module provides the main library API for auditing NIM containers.
"""

from nim_audit.core.image import NIMImage
from nim_audit.core.diff import DiffEngine
from nim_audit.core.config import ConfigAnalyzer
from nim_audit.core.compat import CompatChecker
from nim_audit.core.fingerprint import BehavioralFingerprinter
from nim_audit.core.lint import PolicyLinter
from nim_audit.core.env import (
    CelError,
    FilesystemView,
    diff_surfaces,
    discover_env_vars,
    env_surface,
    eval_cel,
    get_default_registry_path,
    interactions_for,
    lint_env,
    load_registry,
    load_rules,
    risk_delta,
)

__all__ = [
    "NIMImage",
    "DiffEngine",
    "ConfigAnalyzer",
    "CompatChecker",
    "BehavioralFingerprinter",
    "PolicyLinter",
    # Env
    "CelError",
    "FilesystemView",
    "diff_surfaces",
    "discover_env_vars",
    "env_surface",
    "eval_cel",
    "get_default_registry_path",
    "interactions_for",
    "lint_env",
    "load_registry",
    "load_rules",
    "risk_delta",
]
