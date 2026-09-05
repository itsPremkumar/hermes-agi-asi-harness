"""
Calibration Tracking — Section 48 of v7 spec

Predicted confidence vs actual outcome, Brier score per capability.
"""

import asyncio
import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CalibrationTracker:
    """Track prediction quality."""

    def __init__(self):
        self._predictions: list[dict[str, Any]] = []
        self._by_capability: dict[str, list[dict]] = defaultdict(list)

    def record(self, capability: str, predicted_confidence: float, actual_success: bool):
        """Record a prediction and outcome."""
        record = {
            "predicted": predicted_confidence,
            "actual": 1.0 if actual_success else 0.0,
            "timestamp": time.time(),
        }
        self._predictions.append(record)
        self._by_capability[capability].append(record)

    def brier_score(self, capability: str | None = None) -> float:
        """Calculate Brier score (lower = better)."""
        records = self._by_capability.get(capability, self._predictions) if capability else self._predictions
        if not records:
            return 0.0
        return sum((r["predicted"] - r["actual"]) ** 2 for r in records) / len(records)

    def calibration_curve(self, capability: str | None = None, n_bins: int = 10) -> list[dict[str, Any]]:
        """Calculate calibration curve data."""
        records = self._by_capability.get(capability, self._predictions) if capability else self._predictions
        if not records:
            return []

        bins = [[] for _ in range(n_bins)]
        for r in records:
            idx = min(int(r["predicted"] * n_bins), n_bins - 1)
            bins[idx].append(r)

        curve = []
        for i, bin_records in enumerate(bins):
            if bin_records:
                avg_predicted = sum(r["predicted"] for r in bin_records) / len(bin_records)
                avg_actual = sum(r["actual"] for r in bin_records) / len(bin_records)
                curve.append({
                    "bin": i / n_bins,
                    "predicted": round(avg_predicted, 4),
                    "actual": round(avg_actual, 4),
                    "count": len(bin_records),
                })
        return curve

    def get_stats(self) -> dict[str, Any]:
        total = len(self._predictions)
        if total == 0:
            return {"total": 0}
        
        avg_predicted = sum(r["predicted"] for r in self._predictions) / total
        avg_actual = sum(r["actual"] for r in self._predictions) / total
        
        return {
            "total": total,
            "brier_score": round(self.brier_score(), 4),
            "avg_predicted": round(avg_predicted, 4),
            "avg_actual": round(avg_actual, 4),
            "calibration_error": round(abs(avg_predicted - avg_actual), 4),
            "capabilities": len(self._by_capability),
        }


class CalibrationPlugin:
    def __init__(self):
        self.tracker = CalibrationTracker()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {"status": "healthy", **self.tracker.get_stats()}

    async def record(self, capability: str, predicted_confidence: float, actual_success: bool):
        self.tracker.record(capability, predicted_confidence, actual_success)

    async def get_brier_score(self, capability: str | None = None):
        return self.tracker.brier_score(capability)

    async def get_curve(self, capability: str | None = None):
        return self.tracker.calibration_curve(capability)


async def create(kernel=None):
    plugin = CalibrationPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
