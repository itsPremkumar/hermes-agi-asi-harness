#!/usr/bin/env python3
"""Advanced reasoning plugin."""

from core.reasoning import ReasoningEngine, ReasoningMode
from core.runtime.plugin_base import PluginBase, PluginManifest


class Plugin(PluginBase):
    def __init__(self):
        self.manifest = None
        self.engine = ReasoningEngine()
    
    async def load(self) -> bool:
        return True
    
    async def start(self) -> bool:
        return True
    
    async def stop(self) -> bool:
        return True
    
    async def reason(self, question: str, mode: str = "chain_of_thought") -> dict:
        """Execute reasoning."""
        try:
            reasoning_mode = ReasoningMode(mode)
        except ValueError:
            reasoning_mode = ReasoningMode.COT
        
        result = await self.engine.reason(question, reasoning_mode)
        return {
            "question": result.question,
            "answer": result.answer,
            "confidence": result.confidence,
            "steps": len(result.steps),
            "mode": result.mode.value
        }
    
    def list_modes(self) -> list:
        """List available reasoning modes."""
        return self.engine.list_modes()
