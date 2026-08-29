#!/usr/bin/env python3
"""Metacognitive monitoring plugin."""

from core.metacognition import MetacognitiveMonitor, CognitiveMode
from core.runtime.plugin_base import PluginBase, PluginManifest


class Plugin(PluginBase):
    def __init__(self):
        self.manifest = None
        self.monitor = MetacognitiveMonitor()
    
    async def load(self) -> bool:
        return True
    
    async def start(self) -> bool:
        return True
    
    async def stop(self) -> bool:
        return True
    
    async def assess(self, mode: str = "fast") -> dict:
        """Assess cognitive state."""
        try:
            cog_mode = CognitiveMode(mode)
        except ValueError:
            cog_mode = CognitiveMode.FAST
        
        result = await self.monitor.assess(cog_mode)
        return {
            "mode": result.mode.value,
            "confidence": result.confidence,
            "uncertainty": result.uncertainty,
            "issues": result.issues,
            "recommendations": result.recommendations,
            "should_escalate": result.should_escalate
        }
    
    def should_request_help(self) -> tuple:
        """Check if help should be requested."""
        return self.monitor.should_request_help()
    
    def update_confidence(self, predicted: float, actual: bool, context: str = ""):
        """Update confidence calibration."""
        self.monitor.update_confidence(predicted, actual, context)
