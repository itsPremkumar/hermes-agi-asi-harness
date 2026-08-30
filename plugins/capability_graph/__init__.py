"""
Capability Graph Plugin — Capability Measurement & Tracking

Implements section 50 of the v7 spec:
- Capabilities form a graph rather than one score
- Each capability measured separately with confidence, sample count
- Capability dependencies (requires/improves)
- Feeds planner, model router, curriculum engine, risk policy, evolution engine
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CapabilityNode:
    """A measured capability."""
    name: str
    success_rate: float = 0.0
    sample_count: int = 0
    calibration: float = 0.5
    failure_modes: list[str] = field(default_factory=list)
    best_strategy: str = ""
    best_model: str = ""
    resource_profile: dict[str, float] = field(default_factory=dict)
    evaluated_at: float = 0.0
    requires: list[str] = field(default_factory=list)
    improves: list[str] = field(default_factory=list)

    def update(self, success: bool):
        """Update capability measurement with new observation."""
        if self.sample_count == 0:
            self.success_rate = 1.0 if success else 0.0
        else:
            # Bayesian update with moving average
            alpha = 0.1  # learning rate
            self.success_rate = self.success_rate * (1 - alpha) + (1.0 if success else 0.0) * alpha
        
        self.sample_count += 1
        self.evaluated_at = time.time()
        self.calibration = min(1.0, self.sample_count / 50.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "success_rate": round(self.success_rate, 4),
            "sample_count": self.sample_count,
            "calibration": round(self.calibration, 4),
            "failure_modes": self.failure_modes,
            "best_strategy": self.best_strategy,
            "best_model": self.best_model,
            "requires": self.requires,
            "improves": self.improves,
            "evaluated_at": self.evaluated_at,
        }


class CapabilityGraph:
    """Graph of measured capabilities with dependencies."""

    def __init__(self):
        self._capabilities: dict[str, CapabilityNode] = {}
        self._edges: list[tuple] = []  # (cap_a, cap_b, relation_type)

    def get_or_create(self, name: str) -> CapabilityNode:
        """Get or create a capability node."""
        if name not in self._capabilities:
            self._capabilities[name] = CapabilityNode(name=name)
        return self._capabilities[name]

    def record_success(self, capability: str):
        """Record a successful capability execution."""
        cap = self.get_or_create(capability)
        cap.update(True)

    def record_failure(self, capability: str, failure_mode: str = ""):
        """Record a failed capability execution."""
        cap = self.get_or_create(capability)
        cap.update(False)
        if failure_mode and failure_mode not in cap.failure_modes:
            cap.failure_modes.append(failure_mode)

    def set_dependency(self, capability: str, requires: str | None = None, improves: str | None = None):
        """Set capability dependencies."""
        cap = self.get_or_create(capability)
        if requires:
            cap.requires.append(requires)
            self._edges.append((requires, capability, "requires"))
        if improves:
            cap.improves.append(improves)
            self._edges.append((capability, improves, "improves"))

    def get_capability(self, name: str) -> CapabilityNode | None:
        """Get a capability node."""
        return self._capabilities.get(name)

    def get_all(self) -> dict[str, CapabilityNode]:
        """Get all capability nodes."""
        return dict(self._capabilities)

    def get_weakest(self, n: int = 3) -> list[CapabilityNode]:
        """Get the n weakest capabilities (by success rate)."""
        caps = list(self._capabilities.values())
        caps.sort(key=lambda c: (c.success_rate, c.sample_count))
        return caps[:n]

    def get_strongest(self, n: int = 3) -> list[CapabilityNode]:
        """Get the n strongest capabilities."""
        caps = list(self._capabilities.values())
        caps.sort(key=lambda c: c.success_rate, reverse=True)
        return caps[:n]

    def get_gap_analysis(self) -> dict[str, Any]:
        """Identify capability gaps for curriculum targeting."""
        gaps = []
        for cap in self._capabilities.values():
            if cap.success_rate < 0.5:
                gaps.append({
                    "capability": cap.name,
                    "success_rate": cap.success_rate,
                    "prerequisites": cap.requires,
                    "priority": 1.0 - cap.success_rate,
                })
        gaps.sort(key=lambda g: g["priority"], reverse=True)
        return {"gaps": gaps, "total": len(self._capabilities)}

    def get_stats(self) -> dict[str, Any]:
        """Get overall statistics."""
        if not self._capabilities:
            return {"total": 0}
        
        rates = [c.success_rate for c in self._capabilities.values()]
        return {
            "total": len(self._capabilities),
            "avg_success_rate": round(sum(rates) / len(rates), 4),
            "min": round(min(rates), 4),
            "max": round(max(rates), 4),
            "edges": len(self._edges),
            "calibrated": sum(1 for c in self._capabilities.values() if c.calibration > 0.5),
        }


class CapabilityGraphPlugin:
    """Plugin wrapper for capability graph."""

    def __init__(self):
        self.graph = CapabilityGraph()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {"status": "healthy", **self.graph.get_stats()}

    async def record(self, capability: str, success: bool, failure_mode: str = ""):
        """Record a capability execution result."""
        if success:
            self.graph.record_success(capability)
        else:
            self.graph.record_failure(capability, failure_mode)

    async def get_profile(self) -> dict[str, Any]:
        """Get the full capability profile."""
        return {
            name: cap.to_dict()
            for name, cap in self.graph.get_all().items()
        }


async def create(kernel=None):
    plugin = CapabilityGraphPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
