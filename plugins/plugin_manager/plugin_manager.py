
"""
Plugin Manager - dynamic plugin loader & capability registry.

Extracted from: agi-hermes-advanced-master/hermes_agi_harness/src/plugins/plugin_manager.py
"""

import os
import sys
import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BasePlugin:
    def __init__(self, manifest: Any):
        self.manifest = manifest
        self.is_enabled = False
    
    def initialize(self) -> bool:
        self.is_enabled = True
        return True
    
    def shutdown(self):
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
    def __init__(self, plugins_root: Optional[Path] = None, kernel: Any = None):
        self.kernel = kernel
        self.plugins_root = plugins_root or Path("plugins")
        self._plugins: Dict[str, BasePlugin] = {}
        self._tool_registry: Dict[str, tuple] = {}
        self._capabilities: Dict[str, List[str]] = {}
    
    def discover_plugins(self) -> Dict[str, Any]:
        discovered = {}
        if not self.plugins_root.exists():
            return discovered
        
        for child in self.plugins_root.iterdir():
            if child.is_dir() and not child.name.startswith("_"):
                plugin_yaml = child / "plugin.yaml"
                if plugin_yaml.exists():
                    try:
                        import yaml
                        data = yaml.safe_load(plugin_yaml.read_text(encoding="utf-8"))
                        discovered[data.get("name", child.name)] = {
                            "path": child,
                            "manifest": data,
                        }
                    except Exception as e:
                        logger.warning("Failed to parse plugin.yaml in %s: %s", child.name, e)
        return discovered
    
    def load_plugin(self, plugin_path: Path) -> bool:
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
        name = plugin.manifest.name if hasattr(plugin.manifest, 'name') else plugin.__class__.__name__
        
        if name in self._plugins:
            return False
        
        if not plugin.initialize():
            return False
        
        self._plugins[name] = plugin
        
        capabilities = plugin.manifest.capabilities if hasattr(plugin.manifest, 'capabilities') else []
        for cap in capabilities:
            if cap not in self._capabilities:
                self._capabilities[cap] = []
            self._capabilities[cap].append(name)
        
        logger.info("Plugin registered: %s", name)
        return True
    
    def unregister_plugin(self, name: str) -> bool:
        if name not in self._plugins:
            return False
        plugin = self._plugins.pop(name)
        plugin.shutdown()
        for cap in list(self._capabilities.keys()):
            if name in self._capabilities[cap]:
                self._capabilities[cap].remove(name)
        return True
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": name,
                "enabled": p.is_enabled,
                "capabilities": p.manifest.capabilities if hasattr(p.manifest, 'capabilities') else [],
            }
            for name, p in self._plugins.items()
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
    
    async def health(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "type": "plugin_manager",
            "plugins": len(self._plugins),
            "capabilities": {k: len(v) for k, v in self._capabilities.items()},
        }


async def create(kernel: Any) -> PluginManager:
    plugins_root = Path("plugins")
    if kernel and hasattr(kernel, 'config'):
        plugins_root = kernel.config.plugins_root
    return PluginManager(plugins_root=plugins_root, kernel=kernel)
