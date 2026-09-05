"""Advanced Performance Telemetry.

Real-time metrics collection, aggregation, and alerting.
"""

from __future__ import annotations

import statistics
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Metric:
    name: str
    metric_type: MetricType
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class Alert:
    alert_id: str
    name: str
    severity: AlertSeverity
    message: str
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False
    resolved_at: float | None = None


@dataclass
class AlertRule:
    rule_id: str
    name: str
    metric_name: str
    threshold: float
    comparison: str = "gt"  # gt, lt, eq, gte, lte
    severity: AlertSeverity = AlertSeverity.WARNING
    enabled: bool = True


class PerformanceTelemetry:
    """Advanced performance telemetry."""

    def __init__(self):
        self._metrics: list[Metric] = []
        self._alerts: list[Alert] = []
        self._alert_rules: dict[str, AlertRule] = {}
        self._lock = threading.RLock()
        self._max_history = 10000

    def record(self, name: str, value: float, metric_type: MetricType = MetricType.GAUGE, labels: dict[str, str] | None = None) -> None:
        """Record a metric."""
        with self._lock:
            metric = Metric(
                name=name,
                metric_type=metric_type,
                value=value,
                labels=labels or {},
            )
            self._metrics.append(metric)
            if len(self._metrics) > self._max_history:
                self._metrics = self._metrics[-self._max_history:]

            # Check alert rules
            self._check_alerts(metric)

    def increment(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Increment a counter metric."""
        self.record(name, value, MetricType.COUNTER, labels)

    def timer(self, name: str, labels: dict[str, str] | None = None):
        """Context manager for timing operations."""
        return TimerContext(self, name, labels)

    def histogram(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Record a histogram value."""
        self.record(name, value, MetricType.HISTOGRAM, labels)

    def add_alert_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        with self._lock:
            self._alert_rules[rule.rule_id] = rule

    def remove_alert_rule(self, rule_id: str) -> None:
        """Remove an alert rule."""
        with self._lock:
            self._alert_rules.pop(rule_id, None)

    def get_alerts(self, severity: AlertSeverity | None = None, resolved: bool | None = None) -> list[Alert]:
        """Get alerts."""
        with self._lock:
            alerts = list(self._alerts)
            if severity:
                alerts = [a for a in alerts if a.severity == severity]
            if resolved is not None:
                alerts = [a for a in alerts if a.resolved == resolved]
            return alerts

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        with self._lock:
            for alert in self._alerts:
                if alert.alert_id == alert_id:
                    alert.resolved = True
                    alert.resolved_at = time.time()
                    return True
            return False

    def get_metrics(self, name: str | None = None, labels: dict[str, str] | None = None) -> list[Metric]:
        """Get metrics."""
        with self._lock:
            metrics = list(self._metrics)
            if name:
                metrics = [m for m in metrics if m.name == name]
            if labels:
                metrics = [
                    m for m in metrics
                    if all(m.labels.get(k) == v for k, v in labels.items())
                ]
            return metrics

    def get_stats(self, name: str) -> dict[str, float]:
        """Get stats for a metric."""
        with self._lock:
            values = [m.value for m in self._metrics if m.name == name]
            if not values:
                return {}
            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
            }

    def summary(self) -> dict[str, Any]:
        """Get telemetry summary."""
        with self._lock:
            metric_names = set(m.name for m in self._metrics)
            return {
                "total_metrics": len(self._metrics),
                "unique_metrics": len(metric_names),
                "total_alerts": len(self._alerts),
                "unresolved_alerts": sum(1 for a in self._alerts if not a.resolved),
                "alert_rules": len(self._alert_rules),
            }

    def _check_alerts(self, metric: Metric) -> None:
        """Check alert rules against a metric."""
        for rule in self._alert_rules.values():
            if not rule.enabled:
                continue
            if rule.metric_name != metric.name:
                continue

            triggered = False
            if rule.comparison == "gt":
                triggered = metric.value > rule.threshold
            elif rule.comparison == "lt":
                triggered = metric.value < rule.threshold
            elif rule.comparison == "eq":
                triggered = metric.value == rule.threshold
            elif rule.comparison == "gte":
                triggered = metric.value >= rule.threshold
            elif rule.comparison == "lte":
                triggered = metric.value <= rule.threshold

            if triggered:
                alert = Alert(
                    alert_id=f"alert_{int(time.time() * 1000)}",
                    name=rule.name,
                    severity=rule.severity,
                    message=f"{rule.metric_name} = {metric.value} (threshold: {rule.comparison} {rule.threshold})",
                )
                self._alerts.append(alert)


class TimerContext:
    """Context manager for timing."""

    def __init__(self, telemetry: PerformanceTelemetry, name: str, labels: dict[str, str] | None = None):
        self._telemetry = telemetry
        self._name = name
        self._labels = labels
        self._start = 0.0

    def __enter__(self):
        self._start = time.time()
        return self

    def __exit__(self, *args):
        duration = (time.time() - self._start) * 1000
        self._telemetry.histogram(self._name, duration, self._labels)
