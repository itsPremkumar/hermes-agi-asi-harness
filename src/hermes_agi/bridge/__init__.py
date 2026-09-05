"""Bridge package — Hermes Agent integration."""

from __future__ import annotations

from .hermes_bridge import BenchmarkRunner, BotSwarm, HermesBridge, SelfImprovementLoop

__all__ = [
    "HermesBridge",
    "BotSwarm",
    "BenchmarkRunner",
    "SelfImprovementLoop",
]
