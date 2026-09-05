"""
Plugin Loader — discovers and loads plugins from multiple sources.

Supports:
- Filesystem scan (directories containing plugin modules)
- Entry points (package metadata)
- Config-driven loading (explicit plugin lists)
- Dynamic import with isolation
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any, Optional

from .base import Plugin, PluginManifest

logger = logging.getLogger(__name__)


class PluginLoadError(Exception):
    """Raised when a plugin fails to load."""
    pass


class PluginLoader:
    """Discovers and loads plugins from various sources.
    
    The loader supports multiple discovery strategies and provides
    isolation between loaded plugins.
    """

    def __init__(self, plugin_base: type[Plugin] = Plugin) -> None:
        self._plugin_base = plugin_base
        self._loaded_modules: dict[str, Any] = {}

    def load_from_directory(
        self, directory: str | Path, recursive: bool = False
    ) -> list[Plugin]:
        """Load all plugins from a directory.
        
        Each .py file in the directory is treated as a potential
        plugin module. The module must define a ``plugin_class``
        attribute or a ``create_plugin()`` factory function.
        
        Args:
            directory: Path to the plugins directory.
            recursive: Whether to scan subdirectories.
            
        Returns:
            List of loaded plugin instances.
        """
        directory = Path(directory)
        if not directory.is_dir():
            logger.warning("Plugin directory not found: %s", directory)
            return []
        
        plugins: list[Plugin] = []
        pattern = "**/*.py" if recursive else "*.py"
        
        for py_file in sorted(directory.glob(pattern)):
            if py_file.name.startswith("_"):
                continue  # Skip __init__.py and private modules
            try:
                plugin = self.load_from_file(py_file)
                if plugin is not None:
                    plugins.append(plugin)
            except PluginLoadError as e:
                logger.warning("Failed to load plugin from %s: %s", py_file, e)
            except Exception as e:
                logger.exception("Unexpected error loading %s: %s", py_file, e)
        
        return plugins

    def load_from_file(self, path: str | Path) -> Optional[Plugin]:
        """Load a plugin from a Python file.
        
        The file must define either:
        - A ``plugin_class`` attribute pointing to a Plugin subclass
        - A ``create_plugin()`` factory function returning a Plugin
        
        Args:
            path: Path to the Python file.
            
        Returns:
            A plugin instance, or None if the file is not a plugin.
        """
        path = Path(path)
        if not path.is_file():
            raise PluginLoadError(f"File not found: {path}")
        
        module_name = f"_harness_plugin_{path.stem}_{id(path)}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise PluginLoadError(f"Cannot create module spec for {path}")
        
        module = importlib.util.module_from_spec(spec)
        self._loaded_modules[module_name] = module
        
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            del self._loaded_modules[module_name]
            raise PluginLoadError(f"Failed to execute module {path}: {e}") from e
        
        # Try factory function first
        if hasattr(module, "create_plugin"):
            try:
                plugin = module.create_plugin()
                if isinstance(plugin, self._plugin_base):
                    return plugin
            except Exception as e:
                raise PluginLoadError(
                    f"create_plugin() in {path} raised: {e}"
                ) from e
        
        # Try plugin_class attribute
        if hasattr(module, "plugin_class"):
            cls = module.plugin_class
            if isinstance(cls, type) and issubclass(cls, self._plugin_base):
                try:
                    return cls()
                except Exception as e:
                    raise PluginLoadError(
                        f"Failed to instantiate {cls.__name__}: {e}"
                    ) from e
        
        return None

    def load_from_module(self, module_path: str) -> Optional[Plugin]:
        """Load a plugin from an installed module by dotted path.
        
        Args:
            module_path: Dotted module path (e.g., 'my_pkg.plugins.my_plugin').
            
        Returns:
            A plugin instance, or None if the module is not a plugin.
        """
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise PluginLoadError(f"Cannot import {module_path}: {e}") from e
        
        self._loaded_modules[module_path] = module
        
        if hasattr(module, "create_plugin"):
            return module.create_plugin()
        if hasattr(module, "plugin_class"):
            cls = module.plugin_class
            if isinstance(cls, type) and issubclass(cls, self._plugin_base):
                return cls()
        
        return None

    def load_from_manifest(self, manifest: PluginManifest) -> Optional[Plugin]:
        """Load a plugin from its manifest.
        
        Uses the manifest's entry_point to locate and load the plugin.
        
        Args:
            manifest: The plugin manifest.
            
        Returns:
            A plugin instance.
        """
        if not manifest.entry_point:
            raise PluginLoadError(
                f"Manifest for {manifest.name} has no entry_point"
            )
        
        if ":" in manifest.entry_point:
            module_path, factory_name = manifest.entry_point.split(":", 1)
        else:
            module_path = manifest.entry_point
            factory_name = "create_plugin"
        
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise PluginLoadError(
                f"Cannot import {module_path} for {manifest.name}: {e}"
            ) from e
        
        self._loaded_modules[manifest.name] = module
        
        factory = getattr(module, factory_name, None)
        if factory is None:
            raise PluginLoadError(
                f"Module {module_path} has no {factory_name}()"
            )
        
        plugin = factory()
        if not isinstance(plugin, self._plugin_base):
            raise PluginLoadError(
                f"{factory_name}() in {module_path} did not return a Plugin"
            )
        
        return plugin

    def load_from_config(self, config: dict[str, Any]) -> list[Plugin]:
        """Load plugins from a configuration dictionary.
        
        Expected format::
        
            {
                "plugins": [
                    {"module": "my_pkg.plugins.foo", "config": {...}},
                    {"file": "/path/to/bar.py", "config": {...}},
                    {"manifest": {...}, "config": {...}},
                ]
            }
        
        Args:
            config: Configuration dictionary.
            
        Returns:
            List of loaded plugin instances.
        """
        plugins: list[Plugin] = []
        plugin_configs = config.get("plugins", [])
        
        for entry in plugin_configs:
            plugin = None
            try:
                if "file" in entry:
                    plugin = self.load_from_file(entry["file"])
                elif "module" in entry:
                    plugin = self.load_from_module(entry["module"])
                elif "manifest" in entry:
                    manifest = PluginManifest.from_dict(entry["manifest"])
                    plugin = self.load_from_manifest(manifest)
                else:
                    logger.warning("Plugin config entry has no source: %s", entry)
                    continue
            except PluginLoadError as e:
                logger.warning("Failed to load plugin from config: %s", e)
                continue
            
            if plugin is not None:
                plugins.append(plugin)
        
        return plugins

    def load_from_entry_points(self, group: str = "harness.plugins") -> list[Plugin]:
        """Load plugins from package entry points.
        
        Args:
            group: The entry point group name.
            
        Returns:
            List of loaded plugin instances.
        """
        plugins: list[Plugin] = []
        try:
            from importlib.metadata import entry_points
        except ImportError:
            logger.debug("importlib.metadata not available")
            return plugins
        
        try:
            eps = entry_points(group=group)
        except TypeError:
            # Python < 3.12 returns a SelectableGroups or dict
            all_eps = entry_points()
            eps = all_eps.get(group, [])
        
        for ep in eps:
            try:
                cls = ep.load()
                if isinstance(cls, type) and issubclass(cls, self._plugin_base):
                    plugins.append(cls())
                elif callable(cls):
                    result = cls()
                    if isinstance(result, self._plugin_base):
                        plugins.append(result)
            except Exception as e:
                logger.warning("Failed to load entry point %s: %s", ep.name, e)
        
        return plugins

    def get_loaded_modules(self) -> dict[str, Any]:
        """Get all modules loaded by this loader."""
        return dict(self._loaded_modules)

    def unload_module(self, name: str) -> bool:
        """Remove a loaded module from sys.modules."""
        if name in self._loaded_modules:
            del self._loaded_modules[name]
            if name in sys.modules:
                del sys.modules[name]
            return True
        return False
