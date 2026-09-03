"""Plugin management — register, enable/disable, discover plugins."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PluginStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class Plugin:
    id: str
    name: str
    version: str
    description: str
    status: PluginStatus = PluginStatus.ACTIVE
    capabilities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class PluginManager:
    """Manage plugin lifecycle."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._plugins: dict[str, Plugin] = {}

    def register(self, name: str, version: str = "0.1.0",
                 description: str = "", capabilities: list[str] | None = None) -> Plugin:
        plugin = Plugin(
            id=str(uuid.uuid4()),
            name=name,
            version=version,
            description=description,
            capabilities=capabilities or [],
        )
        self._plugins[plugin.id] = plugin
        return plugin

    def unregister(self, plugin_id: str) -> bool:
        return self._plugins.pop(plugin_id, None) is not None

    def get(self, plugin_id: str) -> Plugin | None:
        return self._plugins.get(plugin_id)

    def list_all(self) -> list[Plugin]:
        return list(self._plugins.values())

    def list_active(self) -> list[Plugin]:
        return [p for p in self._plugins.values() if p.status == PluginStatus.ACTIVE]

    def enable(self, plugin_id: str) -> bool:
        if plugin_id in self._plugins:
            self._plugins[plugin_id].status = PluginStatus.ACTIVE
            return True
        return False

    def disable(self, plugin_id: str) -> bool:
        if plugin_id in self._plugins:
            self._plugins[plugin_id].status = PluginStatus.DISABLED
            return True
        return False

    def set_error(self, plugin_id: str) -> bool:
        if plugin_id in self._plugins:
            self._plugins[plugin_id].status = PluginStatus.ERROR
            return True
        return False

    def count(self) -> int:
        return len(self._plugins)

    def active_count(self) -> int:
        return len(self.list_active())

    def search(self, query: str) -> list[Plugin]:
        q = query.lower()
        return [p for p in self._plugins.values()
                if q in p.name.lower() or q in p.description.lower()]

    def get_state(self) -> dict[str, Any]:
        return {
            "total": self.count(),
            "active": self.active_count(),
            "disabled": sum(1 for p in self._plugins.values() if p.status == PluginStatus.DISABLED),
            "error": sum(1 for p in self._plugins.values() if p.status == PluginStatus.ERROR),
        }
