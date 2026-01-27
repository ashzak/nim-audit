"""Unit tests for the config module."""

import os

import pytest

from nim_audit.utils.config import (
    CacheConfig,
    LintConfig,
    NimAuditConfig,
    OutputConfig,
    RegistryConfig,
    get_config,
    get_config_paths,
    get_default_config,
    load_config,
    save_config,
    set_config,
)


class TestCacheConfig:
    """Tests for CacheConfig model."""

    def test_default_values(self):
        """Test default values."""
        config = CacheConfig()
        assert config.enabled is True
        assert config.directory is None
        assert config.ttl == 3600

    def test_custom_values(self):
        """Test custom values."""
        config = CacheConfig(enabled=False, directory="/tmp/cache", ttl=7200)
        assert config.enabled is False
        assert config.directory == "/tmp/cache"
        assert config.ttl == 7200


class TestRegistryConfig:
    """Tests for RegistryConfig model."""

    def test_default_values(self):
        """Test default values."""
        config = RegistryConfig()
        assert config.default_registry == "docker"
        assert config.ngc_api_key is None
        assert config.docker_config_path is None

    def test_custom_values(self):
        """Test custom values."""
        config = RegistryConfig(
            default_registry="ngc",
            ngc_api_key="test-key",
            docker_config_path="/home/user/.docker/config.json",
        )
        assert config.default_registry == "ngc"
        assert config.ngc_api_key == "test-key"
        assert config.docker_config_path == "/home/user/.docker/config.json"


class TestOutputConfig:
    """Tests for OutputConfig model."""

    def test_default_values(self):
        """Test default values."""
        config = OutputConfig()
        assert config.default_format == "terminal"
        assert config.color is True
        assert config.verbose is False

    def test_custom_values(self):
        """Test custom values."""
        config = OutputConfig(default_format="json", color=False, verbose=True)
        assert config.default_format == "json"
        assert config.color is False
        assert config.verbose is True


class TestLintConfig:
    """Tests for LintConfig model."""

    def test_default_values(self):
        """Test default values."""
        config = LintConfig()
        assert config.include_builtin is True
        assert config.default_policy is None
        assert config.fail_on_warning is False

    def test_custom_values(self):
        """Test custom values."""
        config = LintConfig(
            include_builtin=False,
            default_policy="/path/to/policy.yaml",
            fail_on_warning=True,
        )
        assert config.include_builtin is False
        assert config.default_policy == "/path/to/policy.yaml"
        assert config.fail_on_warning is True


class TestNimAuditConfig:
    """Tests for NimAuditConfig model."""

    def test_default_values(self):
        """Test that all defaults are properly set."""
        config = NimAuditConfig()
        assert isinstance(config.cache, CacheConfig)
        assert isinstance(config.registry, RegistryConfig)
        assert isinstance(config.output, OutputConfig)
        assert isinstance(config.lint, LintConfig)
        assert config.plugins == []
        assert config.aliases == {}

    def test_with_plugins(self):
        """Test configuration with plugins."""
        config = NimAuditConfig(plugins=["plugin1", "plugin2"])
        assert config.plugins == ["plugin1", "plugin2"]

    def test_with_aliases(self):
        """Test configuration with aliases."""
        config = NimAuditConfig(aliases={"llama": "nvcr.io/nim/llama3:latest"})
        assert config.aliases == {"llama": "nvcr.io/nim/llama3:latest"}

    def test_nested_config(self):
        """Test nested configuration."""
        config = NimAuditConfig(
            cache=CacheConfig(ttl=1800),
            registry=RegistryConfig(default_registry="ngc"),
            output=OutputConfig(color=False),
        )
        assert config.cache.ttl == 1800
        assert config.registry.default_registry == "ngc"
        assert config.output.color is False


class TestConfigPaths:
    """Tests for config path functions."""

    def test_get_config_paths_includes_expected(self):
        """Test that expected config paths are included."""
        paths = get_config_paths()
        path_strs = [str(p) for p in paths]

        # Should include current directory options
        assert any(".nim-audit.yaml" in p for p in path_strs)
        assert any(".nim-audit.yml" in p for p in path_strs)

        # Should include home directory options
        home = os.path.expanduser("~")
        assert any(home in p for p in path_strs)


class TestLoadSaveConfig:
    """Tests for loading and saving configuration."""

    def test_load_config_default(self, tmp_path, monkeypatch):
        """Test loading default config when no file exists."""
        # Change to temp directory with no config
        monkeypatch.chdir(tmp_path)
        config = load_config()
        assert isinstance(config, NimAuditConfig)

    def test_load_config_from_file(self, tmp_path):
        """Test loading config from a specific file."""
        config_path = tmp_path / "test-config.yaml"
        config_path.write_text("""
cache:
  enabled: false
  ttl: 1800
registry:
  default_registry: ngc
plugins:
  - plugin1
  - plugin2
""")

        config = load_config(config_path)
        assert config.cache.enabled is False
        assert config.cache.ttl == 1800
        assert config.registry.default_registry == "ngc"
        assert config.plugins == ["plugin1", "plugin2"]

    def test_load_config_file_not_found(self, tmp_path):
        """Test that loading nonexistent config raises error."""
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nonexistent.yaml")

    def test_load_config_invalid_yaml(self, tmp_path):
        """Test that invalid YAML raises error."""
        config_path = tmp_path / "invalid.yaml"
        config_path.write_text("invalid: yaml: content: :")

        with pytest.raises(ValueError, match="Invalid YAML"):
            load_config(config_path)

    def test_load_config_empty_file(self, tmp_path):
        """Test loading empty config file returns default."""
        config_path = tmp_path / "empty.yaml"
        config_path.write_text("")

        config = load_config(config_path)
        assert isinstance(config, NimAuditConfig)

    def test_save_config(self, tmp_path):
        """Test saving configuration to file."""
        config = NimAuditConfig(
            cache=CacheConfig(ttl=1800),
            plugins=["test-plugin"],
        )

        config_path = tmp_path / "saved-config.yaml"
        result_path = save_config(config, config_path)

        assert result_path == config_path
        assert config_path.exists()

        # Load and verify
        loaded = load_config(config_path)
        assert loaded.cache.ttl == 1800
        assert loaded.plugins == ["test-plugin"]

    def test_save_config_creates_directory(self, tmp_path):
        """Test that save_config creates parent directories."""
        config = NimAuditConfig()
        config_path = tmp_path / "subdir" / "nested" / "config.yaml"

        save_config(config, config_path)
        assert config_path.exists()


class TestGlobalConfig:
    """Tests for global config functions."""

    def test_get_default_config(self):
        """Test getting default config."""
        config = get_default_config()
        assert isinstance(config, NimAuditConfig)

    def test_set_and_get_config(self, tmp_path, monkeypatch):
        """Test setting and getting global config."""
        # Reset global config
        import nim_audit.utils.config as config_module
        config_module._config = None

        custom_config = NimAuditConfig(
            cache=CacheConfig(ttl=9999)
        )
        set_config(custom_config)

        retrieved = get_config()
        assert retrieved.cache.ttl == 9999

        # Clean up
        config_module._config = None
