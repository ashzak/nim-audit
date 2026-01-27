"""Configuration file support for nim-audit."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class CacheConfig(BaseModel):
    """Cache configuration."""

    enabled: bool = Field(default=True, description="Enable caching")
    directory: str | None = Field(default=None, description="Cache directory")
    ttl: int = Field(default=3600, description="Default TTL in seconds")


class RegistryConfig(BaseModel):
    """Registry configuration."""

    default_registry: str = Field(default="docker", description="Default registry type")
    ngc_api_key: str | None = Field(default=None, description="NGC API key")
    docker_config_path: str | None = Field(default=None, description="Docker config path")


class OutputConfig(BaseModel):
    """Output configuration."""

    default_format: str = Field(default="terminal", description="Default output format")
    color: bool = Field(default=True, description="Enable color output")
    verbose: bool = Field(default=False, description="Verbose output")


class LintConfig(BaseModel):
    """Lint configuration."""

    include_builtin: bool = Field(default=True, description="Include built-in rules")
    default_policy: str | None = Field(default=None, description="Default policy file")
    fail_on_warning: bool = Field(default=False, description="Fail on warnings")


class NimAuditConfig(BaseModel):
    """Main configuration for nim-audit."""

    cache: CacheConfig = Field(default_factory=CacheConfig)
    registry: RegistryConfig = Field(default_factory=RegistryConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    lint: LintConfig = Field(default_factory=LintConfig)

    # Custom settings
    plugins: list[str] = Field(default_factory=list, description="Plugins to load")
    aliases: dict[str, str] = Field(
        default_factory=dict, description="Image reference aliases"
    )


def get_config_paths() -> list[Path]:
    """Get possible configuration file paths.

    Returns:
        List of paths to check for configuration files
    """
    paths = []

    # Current directory
    paths.append(Path.cwd() / ".nim-audit.yaml")
    paths.append(Path.cwd() / ".nim-audit.yml")
    paths.append(Path.cwd() / "nim-audit.yaml")

    # Home directory
    home = Path.home()
    paths.append(home / ".nim-audit.yaml")
    paths.append(home / ".nim-audit" / "config.yaml")
    paths.append(home / ".config" / "nim-audit" / "config.yaml")

    # XDG config directory
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        paths.append(Path(xdg_config) / "nim-audit" / "config.yaml")

    return paths


def load_config(config_path: Path | str | None = None) -> NimAuditConfig:
    """Load configuration from file.

    Args:
        config_path: Explicit path to config file. If None, searches default locations.

    Returns:
        Loaded configuration
    """
    if config_path is not None:
        path = Path(config_path)
        if path.exists():
            return _load_config_file(path)
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Search default locations
    for path in get_config_paths():
        if path.exists():
            return _load_config_file(path)

    # Return default config
    return NimAuditConfig()


def _load_config_file(path: Path) -> NimAuditConfig:
    """Load configuration from a specific file.

    Args:
        path: Path to config file

    Returns:
        Loaded configuration
    """
    try:
        data = yaml.safe_load(path.read_text())
        if data is None:
            return NimAuditConfig()
        return NimAuditConfig.model_validate(data)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file: {e}")
    except Exception as e:
        raise ValueError(f"Failed to load config file: {e}")


def save_config(config: NimAuditConfig, config_path: Path | str | None = None) -> Path:
    """Save configuration to file.

    Args:
        config: Configuration to save
        config_path: Path to save to. Defaults to ~/.nim-audit/config.yaml

    Returns:
        Path where config was saved
    """
    if config_path is None:
        config_path = Path.home() / ".nim-audit" / "config.yaml"
    else:
        config_path = Path(config_path)

    # Create directory if needed
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict and save
    data = config.model_dump(mode="json", exclude_defaults=True)
    config_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))

    return config_path


def get_default_config() -> NimAuditConfig:
    """Get the default configuration.

    Returns:
        Default NimAuditConfig instance
    """
    return NimAuditConfig()


# Global config instance
_config: NimAuditConfig | None = None


def get_config() -> NimAuditConfig:
    """Get the global configuration instance.

    Loads from file on first call.

    Returns:
        Global configuration
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config


def set_config(config: NimAuditConfig) -> None:
    """Set the global configuration instance.

    Args:
        config: Configuration to set
    """
    global _config
    _config = config
