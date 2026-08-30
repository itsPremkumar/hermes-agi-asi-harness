#!/usr/bin/env python3
"""Feedback learning plugin."""

from core.feedback import FeedbackLearner
from core.runtime.plugin_base import PluginBase, PluginManifest


class Plugin(PluginBase):
    def __init__(self):
        self.manifest = None
        self.engine = FeedbackLearner()
    
    async def load(self) -> bool:
        return True
    
    async def start(self) -> bool:
        return True
    
    async def stop(self) -> bool:
        return True
    
    def collect_explicit(self, rating: float, context: str = "") -> str:
        """Collect explicit feedback."""
        return self.engine.collect_explicit(rating, context)
    
    def collect_implicit(self, success: bool, context: str = "") -> str:
        """Collect implicit feedback."""
        return self.engine.collect_implicit(success, context)
    
    def start_ab_test(self, name: str, variant_a: str, variant_b: str) -> str:
        """Start an A/B test."""
        return self.engine.start_ab_test(name, variant_a, variant_b)
