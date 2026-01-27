"""Unit tests for the plugin system."""

import pytest

from nim_audit.utils.plugins import (
    Plugin,
    PluginContext,
    PluginManager,
    get_plugin_manager,
)


class MockPlugin:
    """A mock plugin for testing."""

    name = "mock-plugin"
    version = "1.0.0"

    def __init__(self):
        self.initialized = False
        self.cleaned_up = False
        self.context = None

    def init(self, context: PluginContext) -> None:
        self.initialized = True
        self.context = context

    def cleanup(self) -> None:
        self.cleaned_up = True


class MockPlugin2:
    """Another mock plugin for testing."""

    name = "mock-plugin-2"
    version = "2.0.0"

    def init(self, context: PluginContext) -> None:
        pass

    def cleanup(self) -> None:
        pass


class TestPluginContext:
    """Tests for PluginContext."""

    @pytest.fixture
    def context(self):
        """Create a plugin context."""
        return PluginContext()

    def test_register_renderer(self, context):
        """Test registering a custom renderer."""
        mock_renderer = object()
        context.register_renderer("custom", mock_renderer)
        assert context._renderers["custom"] is mock_renderer

    def test_register_command(self, context):
        """Test registering a custom command."""
        mock_command = lambda: None
        context.register_command(mock_command)
        assert mock_command in context._commands

    def test_register_hook(self, context):
        """Test registering a hook callback."""
        callback = lambda: None
        context.register_hook("before_diff", callback)
        assert callback in context.get_hooks("before_diff")

    def test_get_hooks_empty(self, context):
        """Test getting hooks for unregistered event."""
        hooks = context.get_hooks("nonexistent")
        assert hooks == []

    def test_register_multiple_hooks(self, context):
        """Test registering multiple hooks for same event."""
        cb1 = lambda: 1
        cb2 = lambda: 2
        context.register_hook("before_diff", cb1)
        context.register_hook("before_diff", cb2)

        hooks = context.get_hooks("before_diff")
        assert len(hooks) == 2
        assert cb1 in hooks
        assert cb2 in hooks


class TestPluginManager:
    """Tests for PluginManager."""

    @pytest.fixture
    def manager(self):
        """Create a plugin manager."""
        return PluginManager()

    def test_manager_has_context(self, manager):
        """Test that manager has a context."""
        assert isinstance(manager.context, PluginContext)

    def test_loaded_plugins_initially_empty(self, manager):
        """Test that no plugins are loaded initially."""
        assert manager.loaded_plugins == []

    def test_register_plugin(self, manager):
        """Test registering a plugin from a module."""
        # Create a mock module
        import types
        module = types.ModuleType("test_module")
        module.plugin = MockPlugin()

        manager._register_module_plugin(module, "test_module")

        assert "mock-plugin" in manager.loaded_plugins
        assert manager.get_plugin("mock-plugin") is not None

    def test_register_plugin_via_class(self, manager):
        """Test registering a plugin via Plugin class in module."""
        import types
        module = types.ModuleType("test_module")
        module.Plugin = MockPlugin

        manager._register_module_plugin(module, "test_module")
        assert "mock-plugin" in manager.loaded_plugins

    def test_register_plugin_via_discovery(self, manager):
        """Test registering a plugin via class discovery."""
        import types
        module = types.ModuleType("test_module")
        module.MyCustomPlugin = MockPlugin

        manager._register_module_plugin(module, "test_module")
        assert "mock-plugin" in manager.loaded_plugins

    def test_plugin_init_called(self, manager):
        """Test that plugin.init() is called during registration."""
        plugin = MockPlugin()

        import types
        module = types.ModuleType("test_module")
        module.plugin = plugin

        manager._register_module_plugin(module, "test_module")

        assert plugin.initialized
        assert plugin.context is manager.context

    def test_unload_plugin(self, manager):
        """Test unloading a plugin."""
        plugin = MockPlugin()

        import types
        module = types.ModuleType("test_module")
        module.plugin = plugin

        manager._register_module_plugin(module, "test_module")
        assert "mock-plugin" in manager.loaded_plugins

        manager.unload_plugin("mock-plugin")

        assert "mock-plugin" not in manager.loaded_plugins
        assert plugin.cleaned_up

    def test_unload_nonexistent_plugin_raises(self, manager):
        """Test that unloading nonexistent plugin raises KeyError."""
        with pytest.raises(KeyError, match="not loaded"):
            manager.unload_plugin("nonexistent")

    def test_get_plugin_nonexistent(self, manager):
        """Test getting nonexistent plugin returns None."""
        assert manager.get_plugin("nonexistent") is None

    def test_duplicate_plugin_raises(self, manager):
        """Test that loading duplicate plugin raises ValueError."""
        import types
        module1 = types.ModuleType("test_module1")
        module1.plugin = MockPlugin()

        module2 = types.ModuleType("test_module2")
        module2.plugin = MockPlugin()

        manager._register_module_plugin(module1, "test_module1")

        with pytest.raises(ValueError, match="already loaded"):
            manager._register_module_plugin(module2, "test_module2")

    def test_module_without_plugin_raises(self, manager):
        """Test that module without plugin raises ValueError."""
        import types
        module = types.ModuleType("empty_module")

        with pytest.raises(ValueError, match="No plugin found"):
            manager._register_module_plugin(module, "empty_module")

    def test_plugin_missing_name_raises(self, manager):
        """Test that plugin without name raises ValueError."""

        class InvalidPlugin:
            version = "1.0.0"

            def init(self, context):
                pass

            def cleanup(self):
                pass

        import types
        module = types.ModuleType("test_module")
        module.plugin = InvalidPlugin()

        with pytest.raises(ValueError, match="missing required"):
            manager._register_module_plugin(module, "test_module")

    def test_cleanup_all(self, manager):
        """Test cleaning up all plugins."""
        plugin1 = MockPlugin()
        plugin2 = MockPlugin2()

        import types
        module1 = types.ModuleType("test1")
        module1.plugin = plugin1
        module2 = types.ModuleType("test2")
        module2.plugin = plugin2

        manager._register_module_plugin(module1, "test1")
        manager._register_module_plugin(module2, "test2")

        assert len(manager.loaded_plugins) == 2

        manager.cleanup_all()

        assert len(manager.loaded_plugins) == 0
        assert plugin1.cleaned_up

    def test_load_plugin_from_path(self, manager, tmp_path):
        """Test loading a plugin from a file path."""
        plugin_code = '''
class MyPlugin:
    name = "file-plugin"
    version = "1.0.0"

    def init(self, context):
        pass

    def cleanup(self):
        pass

plugin = MyPlugin()
'''
        plugin_file = tmp_path / "my_plugin.py"
        plugin_file.write_text(plugin_code)

        manager.load_plugin_from_path(plugin_file)

        assert "file-plugin" in manager.loaded_plugins

    def test_load_plugin_from_path_not_found(self, manager, tmp_path):
        """Test that loading nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            manager.load_plugin_from_path(tmp_path / "nonexistent.py")


class TestGetPluginManager:
    """Tests for get_plugin_manager function."""

    def test_returns_singleton(self):
        """Test that get_plugin_manager returns singleton."""
        # Reset the global manager
        import nim_audit.utils.plugins as plugins_module
        plugins_module._plugin_manager = None

        manager1 = get_plugin_manager()
        manager2 = get_plugin_manager()

        assert manager1 is manager2

        # Clean up
        plugins_module._plugin_manager = None


class TestPluginProtocol:
    """Tests for Plugin protocol."""

    def test_mock_plugin_implements_protocol(self):
        """Test that MockPlugin implements Plugin protocol."""
        plugin = MockPlugin()
        assert isinstance(plugin, Plugin)

    def test_plugin_has_required_attributes(self):
        """Test that protocol requires name and version."""
        plugin = MockPlugin()
        assert hasattr(plugin, "name")
        assert hasattr(plugin, "version")
        assert hasattr(plugin, "init")
        assert hasattr(plugin, "cleanup")
