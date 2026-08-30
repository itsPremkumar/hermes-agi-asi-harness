"""
Self-Model Plugin — Empirical Capability Measurement

Implements section 50 of the v7 spec:
- Empirically measured ability per capability
- Tracks: success_rate, sample_count, calibration, failure_modes, best_strategy, best_model, resource_profile
- Feeds: planner, model router, curriculum engine, risk policy, evolution engine
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SelfModelCapability:
    """An empirically measured capability."""
    name: str
    success_rate: float = 0.0
    sample_count: int = 0
    calibration: float = 0.5
    failure_modes: list[str] = field(default_factory=list)
    best_strategy: str = ""
    best_model: str = ""
    resource_profile: dict[str, float] = field(default_factory=dict)
    evaluated_at: float = 0.0
    history: list[dict[str, Any]] = field(default_factory=list)

    def update(self, success: bool, strategy: str = "", model: str = "", resource_cost: float = 0.0):
        """Update capability measurement."""
        self.sample_count += 1
        
        # Exponential moving average
        alpha = 0.1
        self.success_rate = self.success_rate * (1 - alpha) + (1.0 if success else 0.0) * alpha
        
        # Calibration: more samples = more calibrated (asymptotes at 1.0)
        self.calibration = min(1.0, self.sample_count / 50.0)
        
        # Track best strategy
        if success and strategy and not self.best_strategy:
            self.best_strategy = strategy
        
        # Track resource profile
        if resource_cost > 0:
            self.resource_profile["avg_cost"] = (
                self.resource_profile.get("avg_cost", 0) * (1 - alpha) + resource_cost * alpha
            )
        
        self.evaluated_at = time.time()
        
        # Keep history bounded
        self.history.append({
            "success": success,
            "strategy": strategy,
            "model": model,
            "cost": resource_cost,
            "timestamp": time.time(),
        })
        if len(self.history) > 100:
            self.history = self.history[-100:]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "success_rate": round(self.success_rate, 4),
            "sample_count": self.sample_count,
            "calibration": round(self.calibration, 4),
            "failure_modes": self.failure_modes,
            "best_strategy": self.best_strategy,
            "best_model": self.best_model,
            "resource_profile": self.resource_profile,
            "evaluated_at": self.evaluated_at,
        }


class SelfModelEngine:
    """Engine for empirical self-measurement."""

    def __init__(self):
        self._capabilities: dict[str, SelfModelCapability] = {}
        self._bottlenecks: list[dict[str, Any]] = []

    def get_or_create(self, name: str) -> SelfModelCapability:
        if name not in self._capabilities:
            self._capabilities[name] = SelfModelCapability(name=name)
        return self._capabilities[name]

    def record_execution(
        self,
        capability: str,
        success: bool,
        strategy: str = "",
        model: str = "",
        resource_cost: float = 0.0,
        failure_mode: str = "",
    ):
        """Record a capability execution result."""
        cap = self.get_or_create(capability)
        cap.update(success, strategy, model, resource_cost)
        
        if failure_mode and failure_mode not in cap.failure_modes:
            cap.failure_modes.append(failure_mode)

    def get_capability(self, name: str) -> SelfModelCapability | None:
        return self._capabilities.get(name)

    def get_all(self) -> dict[str, SelfModelCapability]:
        return dict(self._capabilities)

    def get_weakest(self, n: int = 3) -> list[SelfModelCapability]:
        """Get weakest capabilities — primary improvement targets."""
        caps = [c for c in self._capabilities.values() if c.sample_count >= 3]
        caps.sort(key=lambda c: c.success_rate)
        return caps[:n]

    def get_strongest(self, n: int = 3) -> list[SelfModelCapability]:
        caps = [c for c in self._capabilities.values() if c.sample_count >= 3]
        caps.sort(key=lambda c: c.success_rate, reverse=True)
        return caps[:n]

    def detect_bottlenecks(self) -> list[dict[str, Any]]:
        """Detect performance bottlenecks for RSI targeting."""
        bottlenecks = []
        for cap in self._capabilities.values():
            if cap.sample_count >= 5 and cap.success_rate < 0.6:
                bottlenecks.append({
                    "capability": cap.name,
                    "success_rate": cap.success_rate,
                    "failure_modes": cap.failure_modes,
                    "priority": 1.0 - cap.success_rate,
                    "sample_count": cap.sample_count,
                })
        bottlenecks.sort(key=lambda b: b["priority"], reverse=True)
        self._bottlenecks = bottlenecks
        return bottlenecks

    def get_recommendation(self, task_class: str) -> dict[str, Any]:
        """Get model/strategy recommendation for a task class."""
        cap = self._capabilities.get(task_class)
        if not cap or cap.sample_count < 3:
            return {"recommendation": "insufficient_data", "confidence": 0.0}
        
        return {
            "recommendation": cap.best_strategy or "default",
            "model": cap.best_model,
            "expected_success_rate": cap.success_rate,
            "confidence": cap.calibration,
        }

    def get_profile(self) -> dict[str, Any]:
        """Get complete self-profile."""
        return {
            "capabilities": {name: cap.to_dict() for name, cap in self._capabilities.items()},
            "bottlenecks": self.detect_bottlenecks(),
            "overall_calibration": sum(c.calibration for c in self._capabilities.values()) / max(1, len(self._capabilities)),
            "total_samples": sum(c.sample_count for c in self._capabilities.values()),
        }

    def get_stats(self) -> dict[str, Any]:
        if not self._capabilities:
            return {"total": 0}
        rates = [c.success_rate for c in self._capabilities.values()]
        return {
            "total": len(self._capabilities),
            "avg_success_rate": round(sum(rates) / len(rates), 4),
            "bottlenecks": len(self._bottlenecks),
            "calibrated": sum(1 for c in self._capabilities.values() if c.calibration > 0.5),
        }


class SelfModelPlugin:
    def __init__(self):
        self.engine = SelfModelEngine()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {"status": "healthy", **self.engine.get_stats()}

    async def record(self, capability: str, success: bool, **kwargs):
        self.engine.record_execution(capability, success, **kwargs)

    async def get_profile(self):
        return self.engine.get_profile()

    async def get_bottlenecks(self):
        return self.engine.detect_bottlenecks()


async def create(kernel=None):
    plugin = SelfModelPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
