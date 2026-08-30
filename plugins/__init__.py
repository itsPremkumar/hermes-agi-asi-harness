#!/usr/bin/env python3
"""
HERMES AGI/ASI HARNESS — PLUGIN SYSTEM
=======================================
Dynamic plugin discovery, loading, and lifecycle management.

Extracted from:
- hermes-free-harness: PluginBase, PluginManifest, PluginPermissions
- agi-hermes-advanced-master: PluginManager with hooks
- agx-harness-main: Plugin registry, dynamic strategies
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import logging
import os
import sys
import yaml
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger("hermes_plugins")


class PluginState(str, Enum):
    REGISTERED = "registered"
    LOADED = "loaded"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    UNLOADED = "unloaded"


@dataclass
class PluginPermissions:
    """Plugin permission boundaries."""
    filesystem_read: str = "project"
    filesystem_write: str = "project"
    network_domains: List[str] = field(default_factory=list)
    shell_commands: List[str] = field(default_factory=list)
    secrets_access: str = "none"
    max_memory_mb: int = 512
    max_cpu_percent: int = 50


@dataclass
class PluginManifest:
    """Plugin metadata."""
    name: str
    version: str
    description: str
    license: str
    source: str
    capabilities: List[str]
    cost: str = "free"
    permissions: PluginPermissions = field(default_factory=PluginPermissions)
    dependencies: List[str] = field(default_factory=list)
    path: Optional[Path] = None

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "PluginManifest":
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        
        perms = data.get("permissions", {})
        fs = perms.get("filesystem", {})
        net = perms.get("network", {})
        shell = perms.get("shell", {})
        secrets = perms.get("secrets", {})
        
        return cls(
            name=data["name"],
            version=str(data["version"]),
            description=data.get("description", ""),
            license=data.get("license", "unknown"),
            source=data.get("source", ""),
            capabilities=data.get("capabilities", []),
            cost=data.get("cost", {}).get("default", "free") if isinstance(data.get("cost"), dict) else data.get("cost", "free"),
            permissions=PluginPermissions(
                filesystem_read=fs.get("read", "project") if isinstance(fs, dict) else "project",
                filesystem_write=fs.get("write", "project") if isinstance(fs, dict) else "project",
                network_domains=net.get("allowed", []) if isinstance(net, dict) else [],
                shell_commands=shell.get("allowed", []) if isinstance(shell, dict) else [],
                secrets_access=secrets.get("access", "none") if isinstance(secrets, dict) else "none",
            ),
            dependencies=data.get("dependencies", []),
            path=yaml_path.parent,
        )


class BasePlugin:
    """Base class for all plugins with hook system."""
    
    manifest: PluginManifest
    
    def __init__(self, manifest: PluginManifest, engine: Any = None):
        self.manifest = manifest
        self.engine = engine
        self.state = PluginState.REGISTERED
    
    async def load(self) -> bool:
        """Load the plugin."""
        self.state = PluginState.LOADED
        return True
    
    async def start(self) -> bool:
        """Start the plugin."""
        self.state = PluginState.RUNNING
        return True
    
    async def pause(self) -> bool:
        """Pause the plugin."""
        self.state = PluginState.PAUSED
        return True
    
    async def resume(self) -> bool:
        """Resume the plugin."""
        self.state = PluginState.RUNNING
        return True
    
    async def stop(self) -> bool:
        """Stop the plugin."""
        self.state = PluginState.UNLOADED
        return True
    
    async def health(self) -> Dict[str, Any]:
        """Health check."""
        return {
            "plugin": self.manifest.name,
            "version": self.manifest.version,
            "state": self.state.value,
            "healthy": self.state in (PluginState.LOADED, PluginState.RUNNING),
        }
    
    def capabilities(self) -> List[str]:
        """Return capabilities."""
        return self.manifest.capabilities
    
    # Hooks
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
    """Dynamic plugin loader and capability registry."""
    
    def __init__(self, plugins_root: str = "plugins"):
        self.plugins_root = Path(plugins_root)
        self._plugins: Dict[str, BasePlugin] = {}
        self._capabilities: Dict[str, List[str]] = {}
        self._tool_registry: Dict[str, tuple] = {}
    
    def discover_plugins(self) -> Dict[str, Any]:
        """Discover all plugins in the plugins directory."""
        discovered = {}
        
        if not self.plugins_root.exists():
            return discovered
        
        for child in self.plugins_root.iterdir():
            if child.is_dir() and not child.name.startswith("_"):
                yaml_path = child / "plugin.yaml"
                if yaml_path.exists():
                    try:
                        manifest = PluginManifest.from_yaml(yaml_path)
                        discovered[manifest.name] = {
                            "path": child,
                            "manifest": manifest,
                        }
                    except Exception as e:
                        logger.warning("Failed to parse plugin.yaml in %s: %s", child.name, e)
        
        return discovered
    
    def load_plugin(self, plugin_path: Path) -> bool:
        """Load a plugin from a directory."""
        try:
            init_file = plugin_path / "__init__.py"
            if not init_file.exists():
                return False
            
            spec = importlib.util.spec_from_file_location(
                f"plugins.{plugin_path.name}", str(init_file)
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"plugins.{plugin_path.name}"] = module
            spec.loader.exec_module(module)
            
            plugin_class = getattr(module, "Plugin", None)
            if not plugin_class:
                return False
            
            plugin = plugin_class()
            return self.register_plugin(plugin)
            
        except Exception as e:
            logger.error("Failed to load plugin %s: %s", plugin_path.name, e)
            return False
    
    def register_plugin(self, plugin: BasePlugin) -> bool:
        """Register a plugin."""
        name = plugin.manifest.name
        
        if name in self._plugins:
            logger.warning("Plugin '%s' already registered", name)
            return False
        
        self._plugins[name] = plugin
        
        # Register capabilities
        for cap in plugin.manifest.capabilities:
            if cap not in self._capabilities:
                self._capabilities[cap] = []
            self._capabilities[cap].append(name)
        
        logger.info("Plugin registered: %s", name)
        return True
    
    def unregister_plugin(self, name: str) -> bool:
        """Unregister a plugin."""
        if name not in self._plugins:
            return False
        
        plugin = self._plugins.pop(name)
        
        for cap in list(self._capabilities.keys()):
            if name in self._capabilities[cap]:
                self._capabilities[cap].remove(name)
        
        return True
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all registered plugins."""
        return [
            {
                "name": name,
                "version": p.manifest.version,
                "state": p.state.value,
                "capabilities": p.manifest.capabilities,
            }
            for name, p in self._plugins.items()
        ]
    
    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """Get a plugin by name."""
        return self._plugins.get(name)
    
    def has_capability(self, capability: str) -> bool:
        """Check if any plugin provides a capability."""
        return bool(self._capabilities.get(capability))
    
    def get_plugins_with_capability(self, capability: str) -> List[BasePlugin]:
        """Get all plugins that provide a capability."""
        plugin_names = self._capabilities.get(capability, [])
        return [self._plugins[name] for name in plugin_names if name in self._plugins]
    
    def execute_pre_tool_hooks(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute pre-tool hooks."""
        curr_args = args
        for plugin in self._plugins.values():
            if plugin.state == PluginState.RUNNING:
                curr_args = plugin.pre_tool_hook(tool_name, curr_args)
        return curr_args
    
    def execute_post_tool_hooks(self, tool_name: str, result: Any) -> Any:
        """Execute post-tool hooks."""
        curr_result = result
        for plugin in self._plugins.values():
            if plugin.state == PluginState.RUNNING:
                curr_result = plugin.post_tool_hook(tool_name, curr_result)
        return curr_result
    
    async def load_all(self):
        """Load all discovered plugins."""
        discovered = self.discover_plugins()
        for name, info in discovered.items():
            self.load_plugin(info["path"])
    
    async def start_all(self):
        """Start all loaded plugins."""
        for plugin in self._plugins.values():
            if plugin.state == PluginState.LOADED:
                await plugin.start()
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check all plugins."""
        results = {}
        for name, plugin in self._plugins.items():
            try:
                results[name] = await plugin.health()
            except Exception as e:
                results[name] = {"status": "error", "error": str(e)}
        return results
