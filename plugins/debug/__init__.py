#!/usr/bin/env python3
"""Debug engine plugin."""

from core.debug import DebugEngine
from core.runtime.plugin_base import PluginBase, PluginManifest


class Plugin(PluginBase):
    def __init__(self):
        self.manifest = None
        self.engine = DebugEngine()
    
    async def load(self) -> bool:
        return True
    
    async def start(self) -> bool:
        return True
    
    async def stop(self) -> bool:
        return True
    
    async def reproduce(self, error_trace: str, file_path: str) -> dict:
        """Reproduce a bug."""
        return await self.engine.reproduce(error_trace, file_path)
    
    async def analyze(self, bug_id: str) -> dict:
        """Analyze root cause."""
        return await self.engine.analyze_root_cause(bug_id)
