"""
Plugin Registry — manages plugin discovery, versioning, and dependency resolution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from .base import Plugin, PluginManifest, PluginType


logger = logging.getLogger(__name__)


@dataclass
class PluginEntry:
    """A registered plugin entry."""
    plugin: Plugin
    manifest: PluginManifest
    source: str = ""  # where the plugin was loaded from
    active: bool = True
    load_order: int = 0


class Registry:
    """Manages plugin registration, versioning, and lookup.
    
    The registry tracks all loaded plugins and provides methods
    for querying, activating, and deactivating them.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, PluginEntry] = {}  # name -> entry
        self._by_id: dict[str, str] = {}  # id -> name
        self._by_type: dict[PluginType, list[str]] = {}
        self._load_counter: int = 0

    def register(self, plugin: Plugin, source: str = "") -> str:
        """Register a plugin.
        
        Args:
            plugin: The plugin instance.
            source: Where the plugin was loaded from.
            
        Returns:
            The plugin ID.
            
        Raises:
            ValueError: If a plugin with the same name is already registered.
        """
        manifest = plugin.get_manifest()
        name = manifest.name
        
        if name in self._plugins:
            raise ValueError(f"Plugin {name!r} is already registered")
        
        self._load_counter += 1
        entry = PluginEntry(
            plugin=plugin,
            manifest=manifest,
            source=source,
            load_order=self._load_counter,
        )
        self._plugins[name] = entry
        self._by_id[manifest.id] = name
        
        ptype = manifest.plugin_type
        if ptype not in self._by_type:
            self._by_type[ptype] = []
        self._by_type[ptype].append(name)
        
        logger.info("Registered plugin %s (type=%s)", name, ptype.value)
        return manifest.id

    def unregister(self, name: str) -> Optional[PluginEntry]:
        """Unregister a plugin by name.
        
        Args:
            name: The plugin name.
            
        Returns:
            The removed entry, or None if not found.
        """
        entry = self._plugins.pop(name, None)
        if entry is None:
            return None
        
        self._by_id.pop(entry.manifest.id, None)
        ptype = entry.manifest.plugin_type
        if ptype in self._by_type:
            self._by_type[ptype] = [n for n in self._by_type[ptype] if n != name]
        
        logger.info("Unregistered plugin %s", name)
        return entry

    def get(self, name: str) -> Optional[PluginEntry]:
        """Get a plugin entry by name."""
        return self._plugins.get(name)

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get a plugin instance by name."""
        entry = self._plugins.get(name)
        return entry.plugin if entry else None

    def get_by_id(self, plugin_id: str) -> Optional[Plugin]:
        """Get a plugin instance by its full ID (name@version)."""
        name = self._by_id.get(plugin_id)
        return self.get_plugin(name) if name else None

    def get_by_type(self, plugin_type: PluginType) -> list[Plugin]:
        """Get all plugins of a specific type."""
        names = self._by_type.get(plugin_type, [])
        return [self._plugins[n].plugin for n in names if n in self._plugins]

    def get_active(self, name: str) -> Optional[Plugin]:
        """Get an active plugin by name."""
        entry = self._plugins.get(name)
        if entry and entry.active:
            return entry.plugin
        return None

    def activate(self, name: str) -> bool:
        """Activate a plugin."""
        entry = self._plugins.get(name)
        if entry:
            entry.active = True
            logger.debug("Activated plugin %s", name)
            return True
        return False

    def deactivate(self, name: str) -> bool:
        """Deactivate a plugin without removing it."""
        entry = self._plugins.get(name)
        if entry:
            entry.active = False
            logger.debug("Deactivated plugin %s", name)
            return True
        return False

    def list_plugins(self, active_only: bool = False) -> list[PluginEntry]:
        """List all registered plugins."""
        entries = list(self._plugins.values())
        if active_only:
            entries = [e for e in entries if e.active]
        return entries

    def list_names(self) -> list[str]:
        """List all registered plugin names."""
        return list(self._plugins.keys())

    def has(self, name: str) -> bool:
        """Check if a plugin is registered."""
        return name in self._plugins

    def count(self) -> int:
        """Number of registered plugins."""
        return len(self._plugins)

    def clear(self) -> None:
        """Clear all registered plugins."""
        self._plugins.clear()
        self._by_id.clear()
        self._by_type.clear()
        self._load_counter = 0

    def check_dependencies(self, manifest: PluginManifest) -> list[str]:
        """Check if a plugin's dependencies are satisfied.
        
        Returns:
            List of missing dependency names (empty if all satisfied).
        """
        missing = []
        for dep in manifest.dependencies:
            if dep not in self._plugins:
                missing.append(dep)
        return missing

    def __repr__(self) -> str:
        return f"Registry(plugins={len(self._plugins)})"
