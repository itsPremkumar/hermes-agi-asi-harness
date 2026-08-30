"""Plugin registry — discover, register, and retrieve plugins."""

from __future__ import annotations

import threading
import uuid
from typing import Any, Optional

from harness.plugin_base import Plugin, PluginMetadata, PluginStatus


class PluginRegistry:
    """Thread-safe registry for all plugins."""

    def __init__(self):
        self._lock = threading.RLock()
        self._plugins: dict[str, Plugin] = {}
        self._by_id: dict[str, str] = {}  # id -> internal key
        self._by_name: dict[str, str] = {}  # name -> key
        self._by_tag: dict[str, list[str]] = {}  # tag -> [keys]
        self._by_capability: dict[str, list[str]] = {}  # provides -> [keys]

    def _gen_key(self, plugin: Plugin) -> str:
        """Generate a unique internal key for a plugin."""
        key = f"{plugin.metadata.id}-{uuid.uuid4().hex[:8]}"
        return key

    def register(self, plugin: Plugin) -> str:
        """Register a plugin. Raises ValueError if ID or name already registered."""
        with self._lock:
            if plugin.metadata.id in self._by_id:
                raise ValueError(f"Plugin ID '{plugin.metadata.id}' already registered")
            if plugin.metadata.name in self._by_name:
                raise ValueError(f"Plugin name '{plugin.metadata.name}' already registered")
            key = self._gen_key(plugin)
            self._plugins[key] = plugin
            self._by_id[plugin.metadata.id] = key
            self._by_name[plugin.metadata.name] = key
            for tag in plugin.metadata.tags:
                self._by_tag.setdefault(tag, []).append(key)
            for cap in plugin.metadata.provides:
                self._by_capability.setdefault(cap, []).append(key)
            return key

    def unregister(self, plugin_id: str) -> bool:
        """Unregister a plugin by ID."""
        with self._lock:
            key = self._by_id.pop(plugin_id, None)
            if key is None:
                return False
            plugin = self._plugins.pop(key, None)
            if plugin:
                self._by_name.pop(plugin.metadata.name, None)
                for tag in plugin.metadata.tags:
                    tag_list = self._by_tag.get(tag, [])
                    if key in tag_list:
                        tag_list.remove(key)
                for cap in plugin.metadata.provides:
                    cap_list = self._by_capability.get(cap, [])
                    if key in cap_list:
                        cap_list.remove(key)
            return True

    def get(self, plugin_id: str) -> Optional[Plugin]:
        with self._lock:
            key = self._by_id.get(plugin_id)
            if key:
                return self._plugins.get(key)
            return None

    def get_by_name(self, name: str) -> Optional[Plugin]:
        with self._lock:
            key = self._by_name.get(name)
            if key:
                return self._plugins.get(key)
            return None

    def get_all(self) -> list[Plugin]:
        with self._lock:
            return list(self._plugins.values())

    def get_by_tag(self, tag: str) -> list[Plugin]:
        with self._lock:
            keys = self._by_tag.get(tag, [])
            return [self._plugins[k] for k in keys if k in self._plugins]

    def get_by_capability(self, capability: str) -> list[Plugin]:
        with self._lock:
            keys = self._by_capability.get(capability, [])
            return [self._plugins[k] for k in keys if k in self._plugins]

    def get_active(self) -> list[Plugin]:
        with self._lock:
            return [p for p in self._plugins.values() if p.status == PluginStatus.ACTIVE]

    def get_with_errors(self) -> list[Plugin]:
        with self._lock:
            return [p for p in self._plugins.values() if p.status == PluginStatus.ERROR]

    def count(self) -> int:
        return len(self._plugins)

    def count_by_status(self, status: PluginStatus) -> int:
        return sum(1 for p in self._plugins.values() if p.status == status)

    def is_registered(self, plugin_id: str) -> bool:
        return plugin_id in self._by_id

    def is_name_registered(self, name: str) -> bool:
        return name in self._by_name

    def clear(self) -> None:
        with self._lock:
            for p in self._plugins.values():
                if p.status == PluginStatus.ACTIVE:
                    try:
                        p.on_stop()
                    except Exception:
                        pass
            self._plugins.clear()
            self._by_id.clear()
            self._by_name.clear()
            self._by_tag.clear()
            self._by_capability.clear()
