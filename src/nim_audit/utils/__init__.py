"""Utility functions for nim-audit."""

from nim_audit.utils.hashing import compute_hash, hash_dict, hash_file, short_hash
from nim_audit.utils.logging import configure_logging, get_logger, get_logger_with_context
from nim_audit.utils.errors import (
    NimAuditError,
    ImageNotFoundError,
    AuthenticationError,
    ValidationError,
    ConfigurationError,
    NetworkError,
    TimeoutError,
    retry,
    validate_image_reference,
    validate_env_var_name,
    safe_get,
)
from nim_audit.utils.expression import SafeExpressionEvaluator, safe_eval
from nim_audit.utils.cache import Cache, get_cache
from nim_audit.utils.config import (
    NimAuditConfig,
    CacheConfig,
    RegistryConfig,
    OutputConfig,
    LintConfig,
    load_config,
    save_config,
    get_config,
    set_config,
)
from nim_audit.utils.plugins import (
    Plugin,
    PluginContext,
    PluginManager,
    get_plugin_manager,
)

__all__ = [
    # Hashing
    "compute_hash",
    "hash_dict",
    "hash_file",
    "short_hash",
    # Logging
    "configure_logging",
    "get_logger",
    "get_logger_with_context",
    # Errors
    "NimAuditError",
    "ImageNotFoundError",
    "AuthenticationError",
    "ValidationError",
    "ConfigurationError",
    "NetworkError",
    "TimeoutError",
    "retry",
    "validate_image_reference",
    "validate_env_var_name",
    "safe_get",
    # Expression
    "SafeExpressionEvaluator",
    "safe_eval",
    # Cache
    "Cache",
    "get_cache",
    # Config
    "NimAuditConfig",
    "CacheConfig",
    "RegistryConfig",
    "OutputConfig",
    "LintConfig",
    "load_config",
    "save_config",
    "get_config",
    "set_config",
    # Plugins
    "Plugin",
    "PluginContext",
    "PluginManager",
    "get_plugin_manager",
]
