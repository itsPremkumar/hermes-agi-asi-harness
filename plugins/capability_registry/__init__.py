"""
Capability Registry Plugin — Empirical Capability Tracking & Self-Model

Tracks what the system can do (success_rate, evidence_count, required_tools,
best_model, average_time, confidence) as an empirical self-model.
Uses data from benchmark results, task outcomes, and evolution experiments.
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class CapabilityRecord:
    name: str
    success_rate: float = 0.0
    evidence_count: int = 0
    required_tools: List[str] = field(default_factory=list)
    best_model: str = "unknown"
    average_time_seconds: float = 0.0
    confidence: float = 0.5
    last_evaluated: Optional[float] = None
    category: str = "general"
    benchmarks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "success_rate": self.success_rate,
            "evidence_count": self.evidence_count,
            "required_tools": self.required_tools,
            "best_model": self.best_model,
            "average_time_seconds": self.average_time_seconds,
            "confidence": self.confidence,
            "last_evaluated": self.last_evaluated,
            "category": self.category,
            "benchmarks": self.benchmarks,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CapabilityRecord":
        d = dict(d)
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class CapabilityRegistry:
    def __init__(self):
        self._capabilities: Dict[str, CapabilityRecord] = {}
        self._performance_history: List[Dict[str, Any]] = []

    def register_capability(self, name: str, category: str = "general",
                           required_tools: List[str] = None) -> CapabilityRecord:
        """Register a new capability."""
        if name not in self._capabilities:
            self._capabilities[name] = CapabilityRecord(
                name=name,
                category=category,
                required_tools=required_tools or [],
            )
        return self._capabilities[name]

    def get_capability(self, name: str) -> Optional[CapabilityRecord]:
        return self._capabilities.get(name)

    def record_result(self, capability_name: str, success: bool,
                     time_seconds: float = 0.0,
                     model: str = "unknown",
                     evidence: str = None) -> CapabilityRecord:
        """Record a task execution result for a capability."""
        cap = self._capabilities.get(capability_name)
        if cap is None:
            cap = self.register_capability(capability_name)

        old_count = cap.evidence_count
        new_count = old_count + 1
        cap.success_rate = (cap.success_rate * old_count + (1.0 if success else 0.0)) / new_count
        cap.average_time_seconds = (cap.average_time_seconds * old_count + time_seconds) / new_count

        # Track best model based on success rate per model
        if success and model != "unknown":
            cap.best_model = model
        cap.evidence_count = new_count
        cap.confidence = min(1.0, 0.3 + new_count * 0.05)
        cap.last_evaluated = time.time()

        if evidence:
            cap.benchmarks.append(evidence)

        self._performance_history.append({
            "capability": capability_name,
            "success": success,
            "time_seconds": time_seconds,
            "model": model,
            "timestamp": time.time(),
        })
        return cap

    def get_best_model_for_capability(self, capability_name: str) -> str:
        """Recommend the best model for a given capability."""
        cap = self._capabilities.get(capability_name)
        return cap.best_model if cap else "unknown"

    def get_confidence(self, capability_name: str) -> float:
        """Get confidence level for a capability."""
        cap = self._capabilities.get(capability_name)
        return cap.confidence if cap else 0.0

    def get_all_capabilities(self) -> Dict[str, Dict[str, Any]]:
        return {name: cap.to_dict() for name, cap in self._capabilities.items()}

    def get_summary(self) -> Dict[str, Any]:
        caps = list(self._capabilities.values())
        avg_success = sum(c.success_rate for c in caps) / len(caps) if caps else 0
        avg_conf = sum(c.confidence for c in caps) / len(caps) if caps else 0
        return {
            "total_capabilities": len(caps),
            "avg_success_rate": round(avg_success, 3),
            "avg_confidence": round(avg_conf, 3),
            "by_category": self._by_category(),
        }

    def _by_category(self) -> Dict[str, int]:
        counts = {}
        for cap in self._capabilities.values():
            counts[cap.category] = counts.get(cap.category, 0) + 1
        return counts


class CapabilityRegistryPlugin:
    def __init__(self):
        self.registry = CapabilityRegistry()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {"status": "healthy", "capabilities": len(self.registry._capabilities)}


async def create(kernel=None):
    plugin = CapabilityRegistryPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
