"""
Model Router Enhancement — Section 31 of v7 spec

Task classification, model portfolio with measured history,
automatic model selection based on task class.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ModelRecord:
    """Measured performance of a model on a task class."""
    model_id: str
    task_class: str
    success_rate: float = 0.0
    sample_count: int = 0
    avg_latency: float = 0.0
    avg_cost: float = 0.0
    calibration: float = 0.5
    last_used: float = 0.0

    def update(self, success: bool, latency: float = 0.0, cost: float = 0.0):
        """Update measured history."""
        self.sample_count += 1
        alpha = 0.1
        self.success_rate = self.success_rate * (1 - alpha) + (1.0 if success else 0.0) * alpha
        self.avg_latency = self.avg_latency * (1 - alpha) + latency * alpha
        self.avg_cost = self.avg_cost * (1 - alpha) + cost * alpha
        self.calibration = min(1.0, self.sample_count / 50.0)
        self.last_used = time.time()

    def score(self) -> float:
        """Calculate weighted score for ranking."""
        return (
            self.success_rate * 0.5
            + self.calibration * 0.2
            + (1.0 / max(1.0, self.avg_latency)) * 0.15
            + (1.0 / max(0.001, self.avg_cost)) * 0.15
        )


class ModelRouterEngine:
    """Measured model routing with history."""

    def __init__(self):
        self._records: Dict[str, ModelRecord] = {}  # key = f"{model_id}:{task_class}"
        self._default_model: str = "default"

    def register_model(self, model_id: str, task_classes: List[str]):
        """Register a model for specific task classes."""
        for tc in task_classes:
            key = f"{model_id}:{tc}"
            if key not in self._records:
                self._records[key] = ModelRecord(model_id=model_id, task_class=tc)

    def record_result(self, model_id: str, task_class: str, success: bool, latency: float = 0.0, cost: float = 0.0):
        """Record a model execution result."""
        key = f"{model_id}:{task_class}"
        if key not in self._records:
            self._records[key] = ModelRecord(model_id=model_id, task_class=task_class)
        self._records[key].update(success, latency, cost)

    def get_best_model(self, task_class: str) -> Optional[str]:
        """Get the best model for a task class based on measured history."""
        candidates = [r for r in self._records.values() if r.task_class == task_class and r.sample_count >= 1]
        if not candidates:
            return self._default_model
        candidates.sort(key=lambda r: r.score(), reverse=True)
        return candidates[0].model_id

    def get_records(self, task_class: str = None) -> List[ModelRecord]:
        """Get records filtered by task class."""
        if task_class:
            return [r for r in self._records.values() if r.task_class == task_class]
        return list(self._records.values())

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_records": len(self._records),
            "models": len(set(r.model_id for r in self._records.values())),
            "task_classes": len(set(r.task_class for r in self._records.values())),
        }


class ModelRouterPlugin:
    def __init__(self):
        self.engine = ModelRouterEngine()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {"status": "healthy", **self.engine.get_stats()}

    async def register_model(self, **kwargs):
        self.engine.register_model(**kwargs)

    async def record_result(self, model_id: str, task_class: str, success: bool, latency: float = 0.0, cost: float = 0.0):
        self.engine.record_result(model_id, task_class, success, latency, cost)

    async def get_best_model(self, task_class: str):
        return self.engine.get_best_model(task_class)


async def create(kernel=None):
    plugin = ModelRouterPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
