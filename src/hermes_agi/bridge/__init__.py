"""Bridge package — Hermes Agent integration."""

from __future__ import annotations

from .hermes_bridge import HermesBridge, BotSwarm, BenchmarkRunner, SelfImprovementLoop

__all__ = [
    "HermesBridge",
    "BotSwarm",
    "BenchmarkRunner",
    "SelfImprovementLoop",
]
