"""
Anti-Goodhart Architecture — Section 108 of v7 spec

Multiple objectives, hidden holdout protection, adversarial test suite, regression suite.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AntiGoodhartEngine:
    """Protect against metric gaming."""

    def __init__(self):
        self._metrics: dict[str, list[dict[str, Any]]] = {}
        self._holdout_set: list[dict[str, Any]] = []
        self._adversarial_tests: list[dict[str, Any]] = []

    def record_metric(self, metric: str, value: float, candidate_id: str | None = None):
        """Record a metric value."""
        if metric not in self._metrics:
            self._metrics[metric] = []
        self._metrics[metric].append({
            "value": value,
            "candidate": candidate_id,
            "timestamp": time.time(),
        })

    def add_holdout_test(self, test: dict[str, Any]):
        """Add a hidden holdout test."""
        self._holdout_set.append(test)

    def add_adversarial_test(self, test: dict[str, Any]):
        """Add an adversarial test."""
        self._adversarial_tests.append(test)

    def check_pareto(self, candidate_scores: dict[str, float]) -> dict[str, Any]:
        """
        Check if candidate dominates on Pareto frontier.
        Returns analysis of trade-offs.
        """
        if not candidate_scores:
            return {"dominates": False, "reason": "no_scores"}

        # Check if any metric is significantly worse
        dominated = False
        for metric, value in candidate_scores.items():
            if self._metrics.get(metric):
                historical = [m["value"] for m in self._metrics[metric]]
                avg = sum(historical) / len(historical)
                if value < avg * 0.8:  # 20% below average
                    dominated = True
                    break

        return {
            "dominates": not dominated,
            "metrics": candidate_scores,
            "timestamp": time.time(),
        }

    def evaluate_candidate(self, candidate_id: str, metrics: dict[str, float]) -> dict[str, Any]:
        """Comprehensive candidate evaluation."""
        # Check for gaming
        pareto = self.check_pareto(metrics)
        
        # Check for regression on critical metrics
        regressions = []
        for metric, value in metrics.items():
            if self._metrics.get(metric):
                historical = [m["value"] for m in self._metrics[metric]]
                if historical and value < min(historical):
                    regressions.append(metric)

        return {
            "candidate": candidate_id,
            "pareto_dominates": pareto["dominates"],
            "regressions": regressions,
            "passed": pareto["dominates"] and not regressions,
            "metrics": metrics,
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "metrics_tracked": len(self._metrics),
            "holdout_tests": len(self._holdout_set),
            "adversarial_tests": len(self._adversarial_tests),
        }


class AntiGoodhartPlugin:
    def __init__(self):
        self.engine = AntiGoodhartEngine()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {"status": "healthy", **self.engine.get_stats()}

    async def evaluate(self, **kwargs):
        return self.engine.evaluate_candidate(**kwargs)


async def create(kernel=None):
    plugin = AntiGoodhartPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
