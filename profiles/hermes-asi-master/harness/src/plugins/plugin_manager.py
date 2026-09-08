#!/usr/bin/env python3
"""
plugin_manager.py — Dynamic Plugin Loader & Capability Registry
Implements the Plugin-Everything architecture and lifecycle hook interception.
"""

from typing import Dict, List, Any, Optional, Callable, Tuple
from .manifest_schema import PluginManifest, ToolContract, PermissionLevel

class BasePlugin:
    def __init__(self, manifest: PluginManifest):
        self.manifest = manifest
        self.is_enabled = False

    def initialize(self) -> bool:
        """Called when plugin is loaded and registered."""
        self.is_enabled = True
        return True

    def shutdown(self):
        """Called when plugin is deactivated."""
        self.is_enabled = False

    def pre_step_hook(self, step_number: int, task: str) -> Optional[str]:
        return None

    def post_step_hook(self, step_number: int, observation: str):
        pass

    def pre_tool_hook(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        return args

    def post_tool_hook(self, tool_name: str, result: Any) -> Any:
        return result

    def on_error_hook(self, error: Exception) -> Optional[str]:
        return None

class PluginManager:
    def __init__(self):
        self._plugins: Dict[str, BasePlugin] = {}
        self._tool_registry: Dict[str, Tuple[ToolContract, Callable]] = {}
        self._capabilities: Dict[str, List[str]] = {}

    def register_plugin(self, plugin: BasePlugin) -> bool:
        """Validates and registers a plugin into the harness."""
        name = plugin.manifest.name
        if name in self._plugins:
            return False

        if not plugin.initialize():
            return False

        self._plugins[name] = plugin

        # Register capabilities
        for cap in plugin.manifest.capabilities:
            if cap not in self._capabilities:
                self._capabilities[cap] = []
            self._capabilities[cap].append(name)

        return True

    def unregister_plugin(self, name: str) -> bool:
        if name not in self._plugins:
            return False
        plugin = self._plugins.pop(name)
        plugin.shutdown()
        # Clean capabilities
        for cap in list(self._capabilities.keys()):
            if name in self._capabilities[cap]:
                self._capabilities[cap].remove(name)
        return True

    def list_plugins(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": p.manifest.name,
                "version": p.manifest.version,
                "description": p.manifest.description,
                "enabled": p.is_enabled,
                "permission": p.manifest.permission_ring.value,
                "capabilities": p.manifest.capabilities
            }
            for p in self._plugins.values()
        ]

    def execute_pre_tool_hooks(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        curr_args = args
        for plugin in self._plugins.values():
            if plugin.is_enabled:
                curr_args = plugin.pre_tool_hook(tool_name, curr_args)
        return curr_args

    def execute_post_tool_hooks(self, tool_name: str, result: Any) -> Any:
        curr_res = result
        for plugin in self._plugins.values():
            if plugin.is_enabled:
                curr_res = plugin.post_tool_hook(tool_name, curr_res)
        return curr_res

    def has_capability(self, capability: str) -> bool:
        return bool(self._capabilities.get(capability))
