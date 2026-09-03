#!/usr/bin/env python3
"""Debate engine plugin."""

from core.debate import DebateEngine
from core.runtime.plugin_base import PluginBase, PluginManifest


class Plugin(PluginBase):
    def __init__(self):
        self.manifest = None
        self.engine = DebateEngine()
    
    async def load(self) -> bool:
        return True
    
    async def start(self) -> bool:
        return True
    
    async def stop(self) -> bool:
        return True
    
    async def conduct_debate(self, proposition: str, rounds: int = 3) -> dict:
        """Conduct a structured debate."""
        return await self.engine.conduct_debate(proposition, rounds)
    
    def detect_fallacies(self, argument: str) -> list:
        """Detect logical fallacies."""
        return self.engine.detect_fallacies(argument)
