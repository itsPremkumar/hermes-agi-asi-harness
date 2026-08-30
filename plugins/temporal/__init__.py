#!/usr/bin/env python3
"""Temporal planner plugin."""

from core.temporal import TemporalPlanner
from core.runtime.plugin_base import PluginBase, PluginManifest


class Plugin(PluginBase):
    def __init__(self):
        self.manifest = None
        self.engine = TemporalPlanner()
    
    async def load(self) -> bool:
        return True
    
    async def start(self) -> bool:
        return True
    
    async def stop(self) -> bool:
        return True
    
    def add_task(self, name: str, duration: float, dependencies: list = None) -> str:
        """Add a task to the schedule."""
        return self.engine.add_task(name, duration, dependencies)
    
    def schedule(self) -> list:
        """Schedule tasks."""
        return self.engine.schedule()
