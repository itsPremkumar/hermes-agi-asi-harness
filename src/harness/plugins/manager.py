"""
Plugin Manager — central orchestrator for the plugin system.

Manages the full plugin lifecycle: discovery, loading, initialization,
registration, execution, and shutdown. Provides isolation and rollback
on failure.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .base import (
    Plugin,
    PluginContext,
    PluginManifest,
    PluginType,
    ExecutionResult,
)
from .hooks import HookRegistry, HookEvent, Priority
from .loader import PluginLoader, PluginLoadError
from .registry import Registry


logger = logging.getLogger(__name__)


@dataclass
class PluginState:
    """Tracks the state of a managed plugin."""
    plugin: Plugin
    manifest: PluginManifest
    state: str = "loaded"  # loaded, initializing, active, error, shutting_down, shutdown
    error: Optional[str] = None
    loaded_at: float = field(default_factory=time.time)
    initialized_at: float = 0.0
    source: str = ""


class PluginManagerError(Exception):
    """Raised when plugin manager operations fail."""
    pass


class PluginManager:
    """Central manager for the plugin system.
    
    Coordinates plugin discovery, loading, initialization, and lifecycle.
    Provides isolation between plugins and rollback on failure.
    
    Usage::
    
        manager = PluginManager(harness_config={...})
        await manager.discover_and_load("/path/to/plugins")
        await manager.initialize_all()
        # ... use plugins ...
        await manager.shutdown_all()
    """

    def __init__(
        self,
        harness_config: Optional[dict[str, Any]] = None,
        hook_registry: Optional[HookRegistry] = None,
        loader: Optional[PluginLoader] = None,
    ) -> None:
        self._registry = Registry()
        self._hooks = hook_registry or HookRegistry()
        self._loader = loader or PluginLoader()
        self._harness_config: dict[str, Any] = harness_config or {}
        self._plugins: dict[str, PluginState] = {}  # name -> state
        self._lock = asyncio.Lock()
        self._event_log: list[dict[str, Any]] = []

    @property
    def registry(self) -> Registry:
        """The plugin registry."""
        return self._registry

    @property
    def hooks(self) -> HookRegistry:
        """The hook registry."""
        return self._hooks

    @property
    def loader(self) -> PluginLoader:
        """The plugin loader."""
        return self._loader

    def _log_event(self, event: str, plugin_name: str = "", **data: Any) -> None:
        """Log a plugin lifecycle event."""
        self._event_log.append({
            "event": event,
            "plugin": plugin_name,
            "timestamp": time.time(),
            "data": data,
        })

    async def load_plugin(
        self,
        plugin: Plugin,
        source: str = "",
        auto_initialize: bool = True,
    ) -> str:
        """Load and optionally initialize a plugin.
        
        Args:
            plugin: The plugin instance.
            source: Where the plugin was loaded from.
            auto_initialize: Whether to initialize immediately.
            
        Returns:
            The plugin name.
            
        Raises:
            PluginManagerError: If the plugin cannot be loaded.
        """
        manifest = plugin.get_manifest()
        name = manifest.name

        if name in self._plugins:
            raise PluginManagerError(f"Plugin {name!r} is already loaded")

        state = PluginState(
            plugin=plugin,
            manifest=manifest,
            source=source,
        )
        self._plugins[name] = state

        try:
            self._registry.register(plugin, source=source)
        except ValueError as e:
            del self._plugins[name]
            raise PluginManagerError(str(e)) from e

        self._log_event("loaded", name, source=source)

        if auto_initialize:
            await self._initialize_plugin(name)

        return name

    async def load_from_directory(
        self, directory: str | Path, recursive: bool = False
    ) -> list[str]:
        """Discover and load plugins from a directory.
        
        Args:
            directory: Path to the plugins directory.
            recursive: Whether to scan subdirectories.
            
        Returns:
            List of loaded plugin names.
        """
        plugins = self._loader.load_from_directory(directory, recursive=recursive)
        names: list[str] = []
        for plugin in plugins:
            try:
                name = await self.load_plugin(plugin, source=str(directory))
                names.append(name)
            except PluginManagerError as e:
                logger.warning("Failed to load plugin: %s", e)
        return names

    async def load_from_file(self, path: str | Path) -> str:
        """Load a plugin from a file.
        
        Args:
            path: Path to the plugin file.
            
        Returns:
            The plugin name.
        """
        plugin = self._loader.load_from_file(path)
        if plugin is None:
            raise PluginManagerError(f"No plugin found in {path}")
        return await self.load_plugin(plugin, source=str(path))

    async def load_from_config(self, config: dict[str, Any]) -> list[str]:
        """Load plugins from a configuration dictionary.
        
        Args:
            config: Configuration with plugin specifications.
            
        Returns:
            List of loaded plugin names.
        """
        plugins = self._loader.load_from_config(config)
        names: list[str] = []
        for plugin in plugins:
            try:
                name = await self.load_plugin(plugin, source="config")
                names.append(name)
            except PluginManagerError as e:
                logger.warning("Failed to load plugin from config: %s", e)
        return names

    async def _initialize_plugin(self, name: str) -> None:
        """Initialize a loaded plugin.
        
        Creates the plugin context and calls the plugin's initialize method.
        Fires on_plugin_load hooks.
        
        Args:
            name: The plugin name.
            
        Raises:
            PluginManagerError: If initialization fails.
        """
        state = self._plugins.get(name)
        if state is None:
            raise PluginManagerError(f"Plugin {name!r} not found")
        if state.state in ("active", "initializing"):
            return  # Already initialized or initializing

        state.state = "initializing"
        
        context = PluginContext(
            plugin_id=state.manifest.id,
            config={},
            harness_config=dict(self._harness_config),
            registry=self._registry,
        )

        try:
            await state.plugin._do_initialize(context)
            state.state = "active"
            state.initialized_at = time.time()
            self._log_event("initialized", name)
        except Exception as e:
            state.state = "error"
            state.error = str(e)
            self._log_event("init_failed", name, error=str(e))
            raise PluginManagerError(
                f"Failed to initialize plugin {name!r}: {e}"
            ) from e

        # Fire hooks
        await self._hooks.fire(
            "on_plugin_load",
            plugin_name=name,
            plugin_type=state.manifest.plugin_type.value,
        )

    async def initialize_all(self) -> dict[str, Optional[str]]:
        """Initialize all loaded plugins.
        
        Returns:
            Dict mapping plugin names to error messages (None = success).
        """
        results: dict[str, Optional[str]] = {}
        for name in list(self._plugins.keys()):
            try:
                await self._initialize_plugin(name)
                results[name] = None
            except PluginManagerError as e:
                results[name] = str(e)
        return results

    async def unload_plugin(self, name: str, force: bool = False) -> bool:
        """Unload a plugin.
        
        Shuts down the plugin, unregisters its hooks, and removes it
        from the registry.
        
        Args:
            name: The plugin name.
            force: If True, unload even if shutdown fails.
            
        Returns:
            True if the plugin was unloaded.
        """
        state = self._plugins.get(name)
        if state is None:
            return False

        state.state = "shutting_down"
        self._registry.deactivate(name)

        # Unregister hooks
        self._hooks.unregister_all(state.manifest.id)

        # Shutdown the plugin
        shutdown_error: Optional[str] = None
        try:
            await state.plugin._do_shutdown()
        except Exception as e:
            shutdown_error = str(e)
            logger.exception("Error shutting down plugin %s: %s", name, e)
            if not force:
                state.state = "error"
                state.error = shutdown_error
                raise PluginManagerError(
                    f"Failed to shutdown plugin {name!r}: {e}"
                ) from e

        # Remove from registry
        self._registry.unregister(name)
        del self._plugins[name]

        self._log_event("unloaded", name, error=shutdown_error)
        await self._hooks.fire(
            "on_plugin_unload",
            plugin_name=name,
            error=shutdown_error,
        )
        return True

    async def unload_all(self, force: bool = True) -> None:
        """Unload all plugins.
        
        Args:
            force: If True, continue unloading even if some fail.
        """
        for name in list(self._plugins.keys()):
            try:
                await self.unload_plugin(name, force=force)
            except PluginManagerError:
                if not force:
                    raise

    async def shutdown_all(self, force: bool = True) -> None:
        """Shutdown all plugins (alias for unload_all)."""
        await self.unload_all(force=force)

    def get_state(self, name: str) -> Optional[PluginState]:
        """Get the state of a plugin."""
        return self._plugins.get(name)

    def get_active_plugins(self) -> list[str]:
        """Get names of all active plugins."""
        return [
            name for name, state in self._plugins.items()
            if state.state == "active"
        ]

    def get_plugins_by_type(self, plugin_type: PluginType) -> list[Plugin]:
        """Get all active plugins of a specific type."""
        return [
            state.plugin
            for state in self._plugins.values()
            if state.state == "active" and state.manifest.plugin_type == plugin_type
        ]

    def list_plugins(self) -> list[dict[str, Any]]:
        """List all plugins with their state."""
        return [
            {
                "name": name,
                "version": state.manifest.version,
                "type": state.manifest.plugin_type.value,
                "state": state.state,
                "source": state.source,
                "error": state.error,
            }
            for name, state in self._plugins.items()
        ]

    def get_event_log(self) -> list[dict[str, Any]]:
        """Get the plugin lifecycle event log."""
        return list(self._event_log)

    async def execute_capability(
        self,
        plugin_name: str,
        capability: str,
        params: Optional[dict[str, Any]] = None,
    ) -> ExecutionResult:
        """Execute a capability on a plugin.
        
        Fires on_before_execute and on_after_execute hooks.
        
        Args:
            plugin_name: The plugin name.
            capability: The capability name.
            params: Parameters for the capability.
            
        Returns:
            The execution result.
        """
        state = self._plugins.get(plugin_name)
        if state is None or state.state != "active":
            return ExecutionResult(
                success=False,
                error=f"Plugin {plugin_name!r} is not active",
            )

        params = params or {}
        start_time = time.time()

        # Fire before_execute hook
        hook_result = await self._hooks.fire(
            "on_before_execute",
            plugin_name=plugin_name,
            capability=capability,
            params=params,
        )
        if hook_result.cancelled:
            return ExecutionResult(
                success=False,
                error="Execution cancelled by hook",
                duration=time.time() - start_time,
            )

        # Execute
        try:
            result = await state.plugin.execute(
                capability, params, state.plugin.context
            )
        except Exception as e:
            result = ExecutionResult(
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )
            # Fire error hook
            await self._hooks.fire(
                "on_error",
                plugin_name=plugin_name,
                capability=capability,
                error=str(e),
            )

        result.duration = time.time() - start_time

        # Fire after_execute hook
        await self._hooks.fire(
            "on_after_execute",
            plugin_name=plugin_name,
            capability=capability,
            result=result.to_dict(),
        )

        return result

    def __repr__(self) -> str:
        active = sum(1 for s in self._plugins.values() if s.state == "active")
        return (
            f"PluginManager(plugins={len(self._plugins)}, active={active})"
        )
