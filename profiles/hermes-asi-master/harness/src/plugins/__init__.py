"""
Hermes Evolutionary AGI/ASI Harness — Plugin Subsystem (Ring 1)
"""
from .manifest_schema import PluginManifest, ToolContract, PermissionLevel
from .plugin_manager import PluginManager, BasePlugin

__all__ = [
    "PluginManifest",
    "ToolContract",
    "PermissionLevel",
    "PluginManager",
    "BasePlugin",
]
