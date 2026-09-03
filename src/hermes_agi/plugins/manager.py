"""Plugin Manager — manages plugin lifecycle."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PluginState(str, Enum):
    DISCOVERED = "discovered"
    LOADED = "loaded"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class PluginBase:
    """Base class for all plugins."""
    
    PLUGIN_CONFIG = {
        "name": "base",
        "description": "Base plugin",
        "version": "1.0.0",
        "capabilities": [],
    }
    
    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self._state = PluginState.LOADED
    
    async def load(self) -> bool:
        self._state = PluginState.LOADED
        return True
    
    async def start(self) -> bool:
        self._state = PluginState.RUNNING
        return True
    
    async def stop(self) -> bool:
        self._state = PluginState.STOPPED
        return True
    
    async def health(self) -> dict:
        return {"state": self._state.value}
    
    def get_capabilities(self) -> list[str]:
        return self.PLUGIN_CONFIG.get("capabilities", [])


class PluginManager:
    """Manages plugin lifecycle."""
    
    def __init__(self):
        self._plugins: dict[str, PluginBase] = {}
    
    def register(self, plugin: PluginBase) -> None:
        self._plugins[plugin.PLUGIN_CONFIG["name"]] = plugin
    
    def get(self, name: str) -> PluginBase | None:
        return self._plugins.get(name)
    
    def list_plugins(self) -> list[str]:
        return list(self._plugins.keys())
    
    async def status(self) -> dict:
        return {
            "total": len(self._plugins),
            "plugins": {name: p._state.value for name, p in self._plugins.items()},
        }
