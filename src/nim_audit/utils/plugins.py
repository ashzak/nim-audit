"""Plugin system for nim-audit."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from nim_audit.utils.logging import get_logger

logger = get_logger("plugins")


@runtime_checkable
class Plugin(Protocol):
    """Protocol for nim-audit plugins.

    Plugins can extend nim-audit with custom extractors, renderers,
    registry clients, and CLI commands.

    To create a plugin:
    1. Create a Python module/package
    2. Implement the Plugin protocol
    3. Register the plugin in the config file or via CLI

    Example:
        class MyPlugin:
            name = "my-plugin"
            version = "1.0.0"

            def init(self, context: PluginContext) -> None:
                # Register custom extractors, renderers, etc.
                context.register_extractor(MyExtractor())

            def cleanup(self) -> None:
                # Cleanup resources
                pass
    """

    name: str
    version: str

    def init(self, context: "PluginContext") -> None:
        """Initialize the plugin.

        Args:
            context: Plugin context for registration
        """
        ...

    def cleanup(self) -> None:
        """Cleanup plugin resources."""
        ...


class PluginContext:
    """Context provided to plugins for registration.

    Provides methods to register custom components with nim-audit.
    """

    def __init__(self) -> None:
        """Initialize the plugin context."""
        from nim_audit.extractors import get_default_registry as get_extractor_registry

        self._extractor_registry = get_extractor_registry()
        self._renderers: dict[str, Any] = {}
        self._commands: list[Any] = []
        self._hooks: dict[str, list[Any]] = {}

    def register_extractor(self, extractor: Any) -> None:
        """Register a custom extractor.

        Args:
            extractor: Extractor instance implementing the Extractor protocol
        """
        self._extractor_registry.register(extractor)
        logger.debug(f"Registered extractor: {extractor.name}")

    def register_renderer(self, name: str, renderer: Any) -> None:
        """Register a custom renderer.

        Args:
            name: Renderer name
            renderer: Renderer instance
        """
        self._renderers[name] = renderer
        logger.debug(f"Registered renderer: {name}")

    def register_command(self, command: Any) -> None:
        """Register a custom CLI command.

        Args:
            command: Typer command function
        """
        self._commands.append(command)
        logger.debug("Registered custom command")

    def register_hook(self, event: str, callback: Any) -> None:
        """Register a hook callback.

        Args:
            event: Event name (e.g., "before_diff", "after_lint")
            callback: Callback function
        """
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)
        logger.debug(f"Registered hook for event: {event}")

    def get_hooks(self, event: str) -> list[Any]:
        """Get all hooks for an event.

        Args:
            event: Event name

        Returns:
            List of hook callbacks
        """
        return self._hooks.get(event, [])


class PluginManager:
    """Manager for loading and managing plugins.

    Example:
        manager = PluginManager()
        manager.load_plugin("my_plugin")
        manager.load_plugin_from_path("/path/to/plugin.py")
    """

    def __init__(self) -> None:
        """Initialize the plugin manager."""
        self._plugins: dict[str, Plugin] = {}
        self._context = PluginContext()

    @property
    def context(self) -> PluginContext:
        """Get the plugin context."""
        return self._context

    def load_plugin(self, module_name: str) -> None:
        """Load a plugin by module name.

        Args:
            module_name: Python module name (e.g., "my_plugin" or "package.plugin")

        Raises:
            ImportError: If module cannot be imported
            ValueError: If module doesn't implement Plugin protocol
        """
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            raise ImportError(f"Failed to import plugin module '{module_name}': {e}")

        self._register_module_plugin(module, module_name)

    def load_plugin_from_path(self, path: Path | str) -> None:
        """Load a plugin from a file path.

        Args:
            path: Path to Python file

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file doesn't implement Plugin protocol
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Plugin file not found: {path}")

        # Generate a unique module name
        module_name = f"nim_audit_plugin_{path.stem}"

        # Load the module
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ValueError(f"Cannot load plugin from: {path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        self._register_module_plugin(module, str(path))

    def _register_module_plugin(self, module: Any, source: str) -> None:
        """Register a plugin from a loaded module.

        Args:
            module: Loaded Python module
            source: Source identifier for error messages
        """
        # Look for a Plugin class or instance
        plugin: Plugin | None = None

        # Check for a 'plugin' attribute
        if hasattr(module, "plugin"):
            plugin = module.plugin
        # Check for a 'Plugin' class
        elif hasattr(module, "Plugin"):
            plugin_class = module.Plugin
            plugin = plugin_class()
        # Check for any class implementing Plugin protocol
        else:
            for name in dir(module):
                obj = getattr(module, name)
                if (
                    isinstance(obj, type)
                    and name != "Plugin"
                    and hasattr(obj, "name")
                    and hasattr(obj, "version")
                    and hasattr(obj, "init")
                ):
                    plugin = obj()
                    break

        if plugin is None:
            raise ValueError(
                f"No plugin found in '{source}'. "
                "Module must export a 'plugin' instance, 'Plugin' class, "
                "or a class implementing the Plugin protocol."
            )

        # Validate plugin
        if not hasattr(plugin, "name") or not hasattr(plugin, "version"):
            raise ValueError(f"Plugin from '{source}' missing required 'name' or 'version'")

        # Check for duplicate
        if plugin.name in self._plugins:
            raise ValueError(f"Plugin '{plugin.name}' is already loaded")

        # Initialize and register
        plugin.init(self._context)
        self._plugins[plugin.name] = plugin
        logger.info(f"Loaded plugin: {plugin.name} v{plugin.version}")

    def unload_plugin(self, name: str) -> None:
        """Unload a plugin by name.

        Args:
            name: Plugin name

        Raises:
            KeyError: If plugin is not loaded
        """
        if name not in self._plugins:
            raise KeyError(f"Plugin '{name}' is not loaded")

        plugin = self._plugins.pop(name)
        plugin.cleanup()
        logger.info(f"Unloaded plugin: {name}")

    def get_plugin(self, name: str) -> Plugin | None:
        """Get a loaded plugin by name.

        Args:
            name: Plugin name

        Returns:
            Plugin instance or None
        """
        return self._plugins.get(name)

    @property
    def loaded_plugins(self) -> list[str]:
        """Get names of all loaded plugins."""
        return list(self._plugins.keys())

    def cleanup_all(self) -> None:
        """Cleanup all loaded plugins."""
        for name in list(self._plugins.keys()):
            self.unload_plugin(name)


# Global plugin manager
_plugin_manager: PluginManager | None = None


def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager.

    Returns:
        Global PluginManager instance
    """
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager
