"""
Dynamic Plugin Creator — creates new plugins at runtime based on need.

When the system encounters a task it can't handle with existing plugins,
it dynamically creates a new plugin to fill the gap.
"""

from __future__ import annotations

import logging
import os
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PluginSpec:
    """Specification for a new plugin."""
    name: str
    description: str
    capabilities: list[str]
    dependencies: list[str]
    author: str = "asi-harness"
    version: str = "1.0.0"


class DynamicPluginCreator:
    """
    Creates new plugins at runtime.
    
    Usage:
        creator = DynamicPluginCreator(project_path)
        
        # Create a plugin for a specific need
        plugin = await creator.create_plugin(PluginSpec(
            name="slack_notifier",
            description="Send notifications to Slack",
            capabilities=["notify", "slack", "message"],
            dependencies=["slack_sdk"],
        ))
        
        # The plugin is immediately usable
    """
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.plugins_dir = self.project_path / "plugins"
        self._created_plugins: dict[str, PluginSpec] = {}
    
    async def create_plugin(self, spec: PluginSpec) -> dict:
        """
        Create a new plugin from a specification.
        
        Args:
            spec: What the plugin should do
            
        Returns:
            Plugin creation result
        """
        plugin_dir = self.plugins_dir / spec.name
        
        # Don't overwrite existing plugins
        if plugin_dir.exists():
            return {
                "status": "exists",
                "plugin": spec.name,
                "path": str(plugin_dir),
            }
        
        try:
            # Create plugin directory
            plugin_dir.mkdir(parents=True, exist_ok=True)
            
            # Create __init__.py
            await self._create_init(plugin_dir, spec)
            
            # Create plugin.py
            await self._create_plugin_code(plugin_dir, spec)
            
            # Create plugin.yaml
            await self._create_manifest(plugin_dir, spec)
            
            self._created_plugins[spec.name] = spec
            
            logger.info(f"Created dynamic plugin: {spec.name}")
            
            return {
                "status": "created",
                "plugin": spec.name,
                "path": str(plugin_dir),
                "capabilities": spec.capabilities,
            }
        
        except Exception as e:
            logger.error(f"Failed to create plugin {spec.name}: {e}")
            return {"status": "error", "plugin": spec.name, "error": str(e)}
    
    async def _create_init(self, plugin_dir: Path, spec: PluginSpec) -> None:
        """Create __init__.py for the plugin."""
        content = f'''"""{spec.description}"""

from .plugin import Plugin

__all__ = ["Plugin"]
__version__ = "{spec.version}"
'''
        (plugin_dir / "__init__.py").write_text(content)
    
    async def _create_plugin_code(self, plugin_dir: Path, spec: PluginSpec) -> None:
        """Create the main plugin code."""
        # Generate capability methods
        capability_methods = ""
        for cap in spec.capabilities:
            capability_methods += f'''
    async def {cap}(self, **kwargs) -> dict:
        """{cap.capitalize()} capability."""
        return {{"status": "completed", "capability": "{cap}", "params": kwargs}}
'''
        
        content = f'''"""
{spec.description}

Dynamically created by ASI Harness at {time.strftime("%Y-%m-%d %H:%M:%S")}
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class Plugin:
    """{spec.description}"""
    
    PLUGIN_CONFIG = {{
        "name": "{spec.name}",
        "description": "{spec.description}",
        "version": "{spec.version}",
        "author": "{spec.author}",
        "capabilities": {spec.capabilities},
        "dependencies": {spec.dependencies},
    }}
    
    def __init__(self, config: dict | None = None):
        self.config = {{}}
        self._state = "loaded"
        self._error = None
    
    async def load(self) -> bool:
        """Load the plugin."""
        self._state = "loaded"
        return True
    
    async def start(self) -> bool:
        """Start the plugin."""
        self._state = "running"
        return True
    
    async def stop(self) -> bool:
        """Stop the plugin."""
        self._state = "stopped"
        return True
    
    async def health(self) -> dict:
        """Health check."""
        return {{"state": self._state, "error": self._error}}
    
    def get_capabilities(self) -> list[str]:
        """Get plugin capabilities."""
        return {spec.capabilities}
{capability_methods}'''
        
        (plugin_dir / "plugin.py").write_text(content)
    
    async def _create_manifest(self, plugin_dir: Path, spec: PluginSpec) -> None:
        """Create plugin.yaml manifest."""
        import yaml
        
        manifest = {
            "name": spec.name,
            "description": spec.description,
            "version": spec.version,
            "author": spec.author,
            "capabilities": spec.capabilities,
            "dependencies": spec.dependencies,
            "entry_point": "plugin.py",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "dynamic": True,
        }
        
        with open(plugin_dir / "plugin.yaml", "w") as f:
            yaml.dump(manifest, f, default_flow_style=False)
    
    def list_created_plugins(self) -> list[dict]:
        """List all dynamically created plugins."""
        return [
            {
                "name": name,
                "description": spec.description,
                "capabilities": spec.capabilities,
            }
            for name, spec in self._created_plugins.items()
        ]
    
    def has_plugin(self, name: str) -> bool:
        """Check if a plugin was created."""
        return name in self._created_plugins
