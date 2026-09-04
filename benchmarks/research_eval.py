"""Research module for continuous improvement — benchmark analysis, trend detection, improvement recommendations."""

from __future__ import annotations

import statistics
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class TrendDirection(Enum):
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    VOLATILE = "volatile"


@dataclass
class BenchmarkRun:
    """A single benchmark run."""
    id: str
    task_id: str
    score: float
    duration_ms: float
    iterations: int
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TrendAnalysis:
    """Analysis of performance trends."""
    task_id: str
    direction: TrendDirection
    slope: float
    confidence: float
    data_points: int
    recommendation: str


@dataclass
class ImprovementRecommendation:
    """A recommendation for improvement."""
    id: str
    category: str  # strategy | parameters | architecture | data
    description: str
    expected_impact: float  # 0-1
    effort: float  # 0-1
    priority: float = 0.0

    def __post_init__(self):
        self.priority = self.expected_impact / max(self.effort, 0.01)


class BenchmarkResearch:
    """Research module for continuous improvement through benchmark analysis."""

    def __init__(self):
        self._lock = threading.RLock()
        self._runs: list[BenchmarkRun] = []
        self._trends: dict[str, TrendAnalysis] = {}
        self._recommendations: list[ImprovementRecommendation] = []

    def record_run(self, run: BenchmarkRun) -> None:
        with self._lock:
            self._runs.append(run)

    def get_runs(self, task_id: str | None = None) -> list[BenchmarkRun]:
        with self._lock:
            if task_id:
                return [r for r in self._runs if r.task_id == task_id]
            return list(self._runs)

    def analyze_trend(self, task_id: str) -> TrendAnalysis:
        """Analyze performance trend for a task."""
        with self._lock:
            runs = [r for r in self._runs if r.task_id == task_id]
            if len(runs) < 2:
                return TrendAnalysis(
                    task_id=task_id,
                    direction=TrendDirection.STABLE,
                    slope=0.0,
                    confidence=0.0,
                    data_points=len(runs),
                    recommendation="Need more data points",
                )

            # Sort by timestamp
            runs.sort(key=lambda r: r.timestamp)
            scores = [r.score for r in runs]

            # Simple linear regression
            n = len(scores)
            x_mean = (n - 1) / 2
            y_mean = sum(scores) / n

            numerator = sum((i - x_mean) * (s - y_mean) for i, s in enumerate(scores))
            denominator = sum((i - x_mean) ** 2 for i in range(n))

            slope = numerator / denominator if denominator != 0 else 0.0

            # Determine direction
            if abs(slope) < 0.01:
                direction = TrendDirection.STABLE
            elif slope > 0:
                direction = TrendDirection.IMPROVING
            else:
                direction = TrendDirection.DECLINING

            # Check volatility
            if len(scores) > 2:
                std_dev = statistics.stdev(scores)
                if std_dev > 0.2:
                    direction = TrendDirection.VOLATILE

            # Confidence based on data points
            confidence = min(1.0, n / 10.0)

            # Generate recommendation
            recommendation = self._generate_recommendation(direction, slope, scores)

            analysis = TrendAnalysis(
                task_id=task_id,
                direction=direction,
                slope=slope,
                confidence=confidence,
                data_points=n,
                recommendation=recommendation,
            )
            self._trends[task_id] = analysis
            return analysis

    def _generate_recommendation(self, direction: TrendDirection, slope: float, scores: list[float]) -> str:
        if direction == TrendDirection.IMPROVING:
            return "Continue current approach"
        elif direction == TrendDirection.DECLINING:
            return "Investigate performance regression"
        elif direction == TrendDirection.VOLATILE:
            return "Stabilize performance before optimizing"
        else:
            return "Try new strategies to improve"

    def generate_recommendations(self) -> list[ImprovementRecommendation]:
        """Generate improvement recommendations based on analysis."""
        with self._lock:
            recommendations = []

            # Analyze each task
            task_ids = set(r.task_id for r in self._runs)
            for task_id in task_ids:
                analysis = self.analyze_trend(task_id)

                if analysis.direction == TrendDirection.DECLINING:
                    recommendations.append(ImprovementRecommendation(
                        id=f"rec_{task_id}_strategy",
                        category="strategy",
                        description=f"Try alternative strategies for {task_id}",
                        expected_impact=0.6,
                        effort=0.5,
                    ))
                    recommendations.append(ImprovementRecommendation(
                        id=f"rec_{task_id}_params",
                        category="parameters",
                        description=f"Tune parameters for {task_id}",
                        expected_impact=0.4,
                        effort=0.3,
                    ))
                elif analysis.direction == TrendDirection.STABLE:
                    recommendations.append(ImprovementRecommendation(
                        id=f"rec_{task_id}_architecture",
                        category="architecture",
                        description=f"Explore architectural changes for {task_id}",
                        expected_impact=0.7,
                        effort=0.8,
                    ))

            # Sort by priority
            recommendations.sort(key=lambda r: r.priority, reverse=True)
            self._recommendations = recommendations
            return recommendations

    def get_trend(self, task_id: str) -> Optional[TrendAnalysis]:
        return self._trends.get(task_id)

    def get_all_trends(self) -> list[TrendAnalysis]:
        return list(self._trends.values())

    def get_recommendations(self) -> list[ImprovementRecommendation]:
        return list(self._recommendations)

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            if not self._runs:
                return {"total_runs": 0, "avg_score": 0.0, "tasks": 0}

            scores = [r.score for r in self._runs]
            return {
                "total_runs": len(self._runs),
                "avg_score": sum(scores) / len(scores),
                "min_score": min(scores),
                "max_score": max(scores),
                "tasks": len(set(r.task_id for r in self._runs)),
                "trends_analyzed": len(self._trends),
                "recommendations": len(self._recommendations),
            }

    def clear(self) -> None:
        with self._lock:
            self._runs.clear()
            self._trends.clear()
            self._recommendations.clear()


__all__ = [
    "BenchmarkResearch",
    "BenchmarkRun",
    "TrendAnalysis",
    "TrendDirection",
    "ImprovementRecommendation",
]
