"""Monitoring Pipeline — Real-time metrics collection and dashboard feed."""
from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MetricSample:
    """A single metric data point."""
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "labels": self.labels,
            "timestamp": self.timestamp,
        }


@dataclass
class DashboardWidget:
    """Configuration for a dashboard widget."""
    widget_id: str
    title: str
    metric_name: str
    widget_type: str = "line"  # line, gauge, bar, table
    refresh_interval_s: float = 5.0
    labels_filter: Dict[str, str] = field(default_factory=dict)


class MetricsAggregator:
    """Aggregates metric samples over time windows."""

    def __init__(self, window_size_s: float = 60.0):
        self.window_size_s = window_size_s
        self._samples: List[MetricSample] = []
        self._lock = threading.Lock()

    def add_sample(self, sample: MetricSample):
        with self._lock:
            self._samples.append(sample)
            cutoff = time.time() - self.window_size_s
            self._samples = [s for s in self._samples if s.timestamp >= cutoff]

    def get_stats(self, metric_name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        with self._lock:
            samples = [s for s in self._samples if s.name == metric_name]
            if labels:
                samples = [s for s in samples if all(s.labels.get(k) == v for k, v in labels.items())]

        if not samples:
            return {"count": 0, "sum": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0}

        values = [s.value for s in samples]
        return {
            "count": len(values),
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }

    def get_rate(self, metric_name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Calculate rate per second for a counter metric."""
        stats = self.get_stats(metric_name, labels)
        if stats["count"] < 2 or self.window_size_s <= 0:
            return 0.0
        return stats["sum"] / self.window_size_s


class AlertRule:
    """Threshold-based alert rule."""

    def __init__(
        self,
        rule_id: str,
        metric_name: str,
        threshold: float,
        comparison: str = "gt",  # gt, lt, gte, lte
        severity: str = "warning",
        labels: Optional[Dict[str, str]] = None,
    ):
        self.rule_id = rule_id
        self.metric_name = metric_name
        self.threshold = threshold
        self.comparison = comparison
        self.severity = severity
        self.labels = labels or {}
        self._triggered = False
        self._last_triggered: Optional[float] = None

    def evaluate(self, value: float) -> bool:
        triggered = False
        if self.comparison == "gt":
            triggered = value > self.threshold
        elif self.comparison == "lt":
            triggered = value < self.threshold
        elif self.comparison == "gte":
            triggered = value >= self.threshold
        elif self.comparison == "lte":
            triggered = value <= self.threshold

        if triggered and not self._triggered:
            self._triggered = True
            self._last_triggered = time.time()
            return True
        elif not triggered:
            self._triggered = False
        return False


class MonitoringPipeline:
    """
    Real-time monitoring pipeline for Hermes ASI.
    Collects metrics, aggregates data, evaluates alerts, and feeds dashboards.
    """

    def __init__(self, window_size_s: float = 60.0):
        self.aggregator = MetricsAggregator(window_size_s=window_size_s)
        self._alert_rules: Dict[str, AlertRule] = {}
        self._widgets: Dict[str, DashboardWidget] = {}
        self._callbacks: List[Callable[[str, MetricSample], None]] = []
        self._active_alerts: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def record_metric(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> MetricSample:
        """Record a metric sample."""
        sample = MetricSample(name=name, value=value, labels=labels or {})
        self.aggregator.add_sample(sample)

        # Evaluate alert rules
        self._evaluate_alerts(sample)

        # Notify callbacks
        for cb in self._callbacks:
            try:
                cb(name, sample)
            except Exception:
                pass

        return sample

    def record_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Record a counter metric (monotonically increasing)."""
        return self.record_metric(name, value, labels)

    def record_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a gauge metric (can go up or down)."""
        return self.record_metric(name, value, labels)

    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a histogram sample (distribution)."""
        return self.record_metric(name, value, labels)

    def add_alert_rule(self, rule: AlertRule):
        """Register an alert rule."""
        self._alert_rules[rule.rule_id] = rule

    def remove_alert_rule(self, rule_id: str) -> bool:
        """Remove an alert rule."""
        if rule_id in self._alert_rules:
            del self._alert_rules[rule_id]
            return True
        return False

    def add_widget(self, widget: DashboardWidget):
        """Register a dashboard widget."""
        self._widgets[widget.widget_id] = widget

    def on_metric(self, callback: Callable[[str, MetricSample], None]):
        """Register a callback for metric events."""
        self._callbacks.append(callback)

    def _evaluate_alerts(self, sample: MetricSample):
        """Evaluate all alert rules against a new sample."""
        for rule in self._alert_rules.values():
            if rule.metric_name != sample.name:
                continue
            if rule.labels and not all(sample.labels.get(k) == v for k, v in rule.labels.items()):
                continue
            if rule.evaluate(sample.value):
                alert = {
                    "rule_id": rule.rule_id,
                    "metric": sample.name,
                    "value": sample.value,
                    "threshold": rule.threshold,
                    "severity": rule.severity,
                    "timestamp": time.time(),
                }
                with self._lock:
                    self._active_alerts.append(alert)
                logger.warning(f"[Monitor] Alert triggered: {rule.rule_id} — {sample.name}={sample.value}")

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts."""
        with self._lock:
            return list(self._active_alerts)

    def clear_alerts(self):
        """Clear all active alerts."""
        with self._lock:
            self._active_alerts.clear()

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for all dashboard widgets."""
        dashboard = {}
        for widget_id, widget in self._widgets.items():
            stats = self.aggregator.get_stats(widget.metric_name, widget.labels_filter)
            dashboard[widget_id] = {
                "widget": {
                    "id": widget.widget_id,
                    "title": widget.title,
                    "type": widget.widget_type,
                    "metric": widget.metric_name,
                },
                "stats": stats,
                "rate": self.aggregator.get_rate(widget.metric_name, widget.labels_filter),
            }
        return dashboard

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health snapshot."""
        return {
            "timestamp": time.time(),
            "active_alerts": len(self._active_alerts),
            "alert_rules": len(self._alert_rules),
            "widgets": len(self._widgets),
            "dashboard": self.get_dashboard_data(),
        }
