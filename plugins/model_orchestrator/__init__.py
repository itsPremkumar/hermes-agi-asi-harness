#!/usr/bin/env python3
"""Multi-model orchestrator plugin."""

from core.models import ModelOrchestrator, ModelCapability
from core.runtime.plugin_base import PluginBase, PluginManifest


class Plugin(PluginBase):
    def __init__(self):
        self.manifest = None
        self.engine = ModelOrchestrator()
    
    async def load(self) -> bool:
        return True
    
    async def start(self) -> bool:
        return True
    
    async def stop(self) -> bool:
        return True
    
    def route(self, task: str, prefer_local: bool = True) -> dict:
        """Route a task to the optimal model."""
        decision = self.engine.route(task, prefer_local=prefer_local)
        return {"model": decision.selected_model, "confidence": decision.confidence, "reason": decision.reason}
    
    async def ensemble(self, task: str, num_models: int = 3) -> dict:
        """Query multiple models for consensus."""
        return await self.engine.ensemble(task, num_models)
