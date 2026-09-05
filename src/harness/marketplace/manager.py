"""Plugin manager stub."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PluginState(Enum):
    INSTALLED = "installed"
    AVAILABLE = "available"

@dataclass
class PluginEntry:
    plugin_id: str
    name: str
    state: PluginState

class PluginManager:
    def list_plugins(self) -> list[PluginEntry]:
        return []
