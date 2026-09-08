"""
PerformanceTracker — Track improvements over time, A/B comparisons.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MetricType(str, Enum):
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ACCURACY = "accuracy"
    RELIABILITY = "reliability"
    COST = "cost"


@dataclass
class MetricSnapshot:
    """A single metric measurement at a point in time."""

    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ABTest:
    """An A/B comparison between two configurations."""

    test_id: str
    name: str
    variant_a: str
    variant_b: str
    metric_name: str
    samples_a: list[float] = field(default_factory=list)
    samples_b: list[float] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime | None = None
    winner: str | None = None
    confidence: float = 0.0

    def add_sample_a(self, value: float) -> None:
        self.samples_a.append(value)

    def add_sample_b(self, value: float) -> None:
        self.samples_b.append(value)

    @property
    def mean_a(self) -> float:
        return statistics.mean(self.samples_a) if self.samples_a else 0.0

    @property
    def mean_b(self) -> float:
        return statistics.mean(self.samples_b) if self.samples_b else 0.0

    @property
    def std_a(self) -> float:
        return statistics.stdev(self.samples_a) if len(self.samples_a) > 1 else 0.0

    @property
    def std_b(self) -> float:
        return statistics.stdev(self.samples_b) if len(self.samples_b) > 1 else 0.0

    @property
    def improvement_pct(self) -> float:
        """Percentage improvement of B over A."""
        if self.mean_a == 0:
            return 0.0
        return ((self.mean_b - self.mean_a) / abs(self.mean_a)) * 100.0


@dataclass
class TrendAnalysis:
    """Trend analysis for a metric over time."""

    metric_name: str
    direction: str  # "improving", "declining", "stable"
    slope: float
    r_squared: float
    data_points: int
    prediction_next: float = 0.0


class PerformanceTracker:
    """Tracks performance metrics over time and supports A/B comparisons."""

    def __init__(self) -> None:
        self._metrics: dict[str, list[MetricSnapshot]] = {}
        self._ab_tests: dict[str, ABTest] = {}
        self._baselines: dict[str, float] = {}

    @property
    def metric_names(self) -> list[str]:
        return list(self._metrics.keys())

    @property
    def ab_test_ids(self) -> list[str]:
        return list(self._ab_tests.keys())

    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.LATENCY,
        labels: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MetricSnapshot:
        """Record a metric measurement."""
        snapshot = MetricSnapshot(
            name=name,
            value=value,
            metric_type=metric_type,
            labels=labels or {},
            metadata=metadata or {},
        )

        if name not in self._metrics:
            self._metrics[name] = []
        self._metrics[name].append(snapshot)

        return snapshot

    def get_history(self, name: str) -> list[MetricSnapshot]:
        """Get the full history for a metric."""
        return list(self._metrics.get(name, []))

    def get_latest(self, name: str) -> MetricSnapshot | None:
        """Get the most recent measurement for a metric."""
        history = self._metrics.get(name, [])
        return history[-1] if history else None

    def get_statistics(self, name: str) -> dict[str, float]:
        """Get descriptive statistics for a metric."""
        history = self._metrics.get(name, [])
        if not history:
            return {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0, "std": 0.0}

        values = [s.value for s in history]
        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "min": min(values),
            "max": max(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0.0,
        }

    def set_baseline(self, name: str, value: float) -> None:
        """Set a baseline value for a metric."""
        self._baselines[name] = value

    def get_baseline(self, name: str) -> float | None:
        """Get the baseline value for a metric."""
        return self._baselines.get(name)

    def compare_to_baseline(self, name: str) -> dict[str, Any]:
        """Compare the latest value to the baseline."""
        latest = self.get_latest(name)
        baseline = self._baselines.get(name)

        if latest is None or baseline is None:
            return {"has_comparison": False}

        delta = latest.value - baseline
        pct_change = (delta / abs(baseline)) * 100 if baseline != 0 else 0.0

        return {
            "has_comparison": True,
            "baseline": baseline,
            "latest": latest.value,
            "delta": delta,
            "pct_change": pct_change,
            "improved": abs(latest.value) < abs(baseline) if "latency" in name.lower() or "cost" in name.lower() else latest.value > baseline,
        }

    def create_ab_test(
        self,
        test_id: str,
        name: str,
        variant_a: str,
        variant_b: str,
        metric_name: str,
    ) -> ABTest:
        """Create a new A/B test."""
        test = ABTest(
            test_id=test_id,
            name=name,
            variant_a=variant_a,
            variant_b=variant_b,
            metric_name=metric_name,
        )
        self._ab_tests[test_id] = test
        return test

    def get_ab_test(self, test_id: str) -> ABTest | None:
        """Get an A/B test by ID."""
        return self._ab_tests.get(test_id)

    def conclude_ab_test(self, test_id: str) -> ABTest | None:
        """Conclude an A/B test and determine the winner."""
        test = self._ab_tests.get(test_id)
        if not test:
            return None

        if not test.samples_a or not test.samples_b:
            return test

        test.end_time = datetime.utcnow()

        # Require minimum sample size for statistical significance
        if len(test.samples_a) < 3 or len(test.samples_b) < 3:
            test.winner = "inconclusive"
            return test

        # Determine if lower is better based on metric name
        lower_is_better = any(
            kw in test.metric_name.lower()
            for kw in ("latency", "cost", "error", "failure")
        )

        # Simple t-test approximation (Welch's t-test)
        mean_diff = test.mean_b - test.mean_a
        se = ((test.std_a ** 2 / len(test.samples_a)) + (test.std_b ** 2 / len(test.samples_b))) ** 0.5

        if se > 0:
            t_stat = mean_diff / se
            # Approximate confidence from t-statistic
            test.confidence = min(0.99, max(0.0, 1.0 - 1.0 / (1.0 + abs(t_stat))))
        elif mean_diff == 0:
            test.confidence = 0.0
        else:
            test.confidence = 0.99

        # Determine winner
        if test.confidence >= 0.95:
            if mean_diff > 0:
                test.winner = test.variant_b if not lower_is_better else test.variant_a
            elif mean_diff < 0:
                test.winner = test.variant_a if not lower_is_better else test.variant_b
            else:
                test.winner = "tie"
        else:
            test.winner = "inconclusive"

        return test

    def analyze_trend(self, name: str, window: int | None = None) -> TrendAnalysis | None:
        """Analyze the trend of a metric over time using linear regression."""
        history = self._metrics.get(name, [])
        if not history:
            return None

        if window:
            history = history[-window:]

        if len(history) < 2:
            return TrendAnalysis(
                metric_name=name,
                direction="stable",
                slope=0.0,
                r_squared=0.0,
                data_points=len(history),
            )

        # Simple linear regression
        n = len(history)
        x_vals = list(range(n))
        y_vals = [s.value for s in history]

        x_mean = statistics.mean(x_vals)
        y_mean = statistics.mean(y_vals)

        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals))
        denominator = sum((x - x_mean) ** 2 for x in x_vals)

        if denominator == 0:
            slope = 0.0
        else:
            slope = numerator / denominator

        intercept = y_mean - slope * x_mean

        # R-squared
        ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(x_vals, y_vals))
        ss_tot = sum((y - y_mean) ** 2 for y in y_vals)
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # Determine direction
        if abs(slope) < 0.01 * abs(y_mean) if y_mean != 0 else abs(slope) < 0.001:
            direction = "stable"
        elif slope > 0:
            direction = "improving" if "accuracy" in name.lower() or "throughput" in name.lower() else "declining"
        else:
            direction = "improving" if "latency" in name.lower() or "cost" in name.lower() else "declining"

        prediction = slope * n + intercept

        return TrendAnalysis(
            metric_name=name,
            direction=direction,
            slope=slope,
            r_squared=r_squared,
            data_points=n,
            prediction_next=prediction,
        )

    def detect_anomalies(self, name: str, threshold_std: float = 2.0) -> list[MetricSnapshot]:
        """Detect anomalous metric values using standard deviation."""
        history = self._metrics.get(name, [])
        if len(history) < 3:
            return []

        values = [s.value for s in history]
        mean = statistics.mean(values)
        std = statistics.stdev(values)

        if std == 0:
            return []

        anomalies = [
            s for s in history
            if abs(s.value - mean) > threshold_std * std
        ]

        return anomalies

    def get_improvement_report(self) -> dict[str, Any]:
        """Generate a comprehensive improvement report."""
        report: dict[str, Any] = {
            "metrics_tracked": len(self._metrics),
            "baselines_set": len(self._baselines),
            "ab_tests": len(self._ab_tests),
            "metric_summaries": {},
            "trends": {},
            "baseline_comparisons": {},
            "ab_test_results": {},
        }

        for name in self._metrics:
            report["metric_summaries"][name] = self.get_statistics(name)
            trend = self.analyze_trend(name)
            if trend:
                report["trends"][name] = {
                    "direction": trend.direction,
                    "slope": trend.slope,
                    "r_squared": trend.r_squared,
                }

        for name in self._baselines:
            report["baseline_comparisons"][name] = self.compare_to_baseline(name)

        for test_id, test in self._ab_tests.items():
            report["ab_test_results"][test_id] = {
                "name": test.name,
                "winner": test.winner,
                "confidence": test.confidence,
                "improvement_pct": test.improvement_pct,
                "samples_a": len(test.samples_a),
                "samples_b": len(test.samples_b),
            }

        return report
