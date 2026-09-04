
"""
Plugin Base — every plugin inherits this.

All capabilities in Hermes are plugins. The kernel only provides
the runtime; plugins provide all actual functionality.

Extracted & enhanced from:
- hermes-free-harness: base.py (PluginBase, PluginManifest, PluginPermissions)
- agi-hermes-advanced-master: plugin_manager.py (BasePlugin with hooks)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class PluginState(str, Enum):
    REGISTERED = "registered"
    LOADED = "loaded"
    RUNNING = "running"
    PAUSED = "PAUSED"
    ERROR = "error"
    UNLOADED = "unLOADED"


@dataclass
class PluginPermissions:
    """What this plugin is allowed to do."""
    filesystem_read: str = "project"   # project | workspace | none | all
    filesystem_write: str = "project"
    network_domains: list[str] = field(default_factory=list)  # empty = none
    shell_commands: list[str] = field(default_factory=list)  # empty = none
    secrets_access: str = "none"  # none | scoped | all
    max_memory_mb: int = 512
    max_cpu_percent: int = 50


@dataclass
class PluginManifest:
    """Plugin metadata — loaded from plugin.yaml."""
    name: str
    version: str
    description: str
    license: str
    source: str
    capabilities: list[str]
    cost: str  # free | optional-paid
    permissions: PluginPermissions = field(default_factory=PluginPermissions)
    dependencies: list[str] = field(default_factory=list)
    path: Path | None = None

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> PluginManifest:
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
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
                max_memory_mb=perms.get("max_memory_mb", 512),
                max_cpu_percent=perms.get("max_cpu_percent", 50),
            ),
            dependencies=data.get("dependencies", []),
            path=yaml_path.parent,
        )


class PluginBase:
    """
    Base class for all plugins.
    
    Lifecycle:
        register → load → start → run → pause → resume → stop → unload
    
    Hook system (from agi-hermes-advanced-master):
        pre_step_hook — called before each agent step
        post_step_hook — called after each agent step
        pre_tool_hook — called before each tool execution
        post_tool_hook — called after each tool execution
        on_error_hook — called when an error occurs
    """
    
    manifest: PluginManifest
    
    def __init__(self, manifest: PluginManifest, kernel: Any = None):
        self.manifest = manifest
        self.kernel = kernel
        self.state = PluginState.REGISTERED
        self._health_check_interval = 30
    
    async def load(self) -> bool:
        """Load the plugin. Called once before start()."""
        self.state = PluginState.LOADED
        return True
    
    async def start(self) -> bool:
        """Start the plugin. Called after load()."""
        self.state = PluginState.RUNNING
        return True
    
    async def pause(self) -> bool:
        """Pause the plugin temporarily."""
        self.state = PluginState.PAUSED
        return True
    
    async def resume(self) -> bool:
        """Resume a paused plugin."""
        self.state = PluginState.RUNNING
        return True
    
    async def stop(self) -> bool:
        """Stop the plugin."""
        self.state = PluginState.UNLOADED
        return True
    
    async def unload(self) -> bool:
        """Unload the plugin. Called once before removal."""
        self.state = PluginState.UNLOADED
        return True
    
    async def health(self) -> dict[str, Any]:
        """Return health status."""
        return {
            "plugin": self.manifest.name,
            "version": self.manifest.version,
            "state": self.state.value,
            "healthy": self.state in (PluginState.LOADED, PluginState.RUNNING),
        }
    
    def capabilities(self) -> list[str]:
        """Return list of capabilities this plugin provides."""
        return self.manifest.capabilities
    
    async def verify(self) -> bool:
        """Run plugin self-test. Override in subclasses."""
        return True
    
    # Hook system (from agi-hermes-advanced-master)
    def pre_step_hook(self, step_number: int, task: str) -> str | None:
        """Called before each agent step. Return a string to inject context."""
        return None
    
    def post_step_hook(self, step_number: int, observation: str):
        """Called after each agent step."""
    
    def pre_tool_hook(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Called before each tool execution. Can modify args."""
        return args
    
    def post_tool_hook(self, tool_name: str, result: Any) -> Any:
        """Called after each tool execution. Can modify result."""
        return result
    
    def on_error_hook(self, error: Exception) -> str | None:
        """Called when an error occurs. Return a recovery suggestion."""
        return None
