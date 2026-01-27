"""Environment variable analysis for NIM containers."""

from nim_audit.core.env.discovery import discover_env_vars, FilesystemView
from nim_audit.core.env.registry import load_registry, interactions_for, get_default_registry_path
from nim_audit.core.env.lint import lint_env, load_rules
from nim_audit.core.env.diff import env_surface, diff_surfaces, risk_delta
from nim_audit.core.env.cel import eval_cel, CelError

__all__ = [
    "discover_env_vars",
    "FilesystemView",
    "load_registry",
    "interactions_for",
    "get_default_registry_path",
    "lint_env",
    "load_rules",
    "env_surface",
    "diff_surfaces",
    "risk_delta",
    "eval_cel",
    "CelError",
]
