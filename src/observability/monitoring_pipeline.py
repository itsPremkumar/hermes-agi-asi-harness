"""Real-time monitoring dashboard data pipeline."""
from __future__ import annotations

import time
import json
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable, Iterator
from contextlib import contextmanager


@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    value: float
    timestamp: str
    labels: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp,
            "labels": self.labels,
        }


@dataclass
class AlertRule:
    """An alert rule for monitoring."""
    name: str
    metric: str
    threshold: float
    comparison: str = "gt"  # gt, lt, gte, lte, eq
    duration: int = 60  # seconds
    severity: str = "warning"
    labels: dict[str, str] = field(default_factory=dict)
    _triggered_at: float | None = field(default=None, repr=False)

    def check(self, value: float) -> bool:
        """Check if the value triggers the alert."""
        if self.comparison == "gt":
            return value > self.threshold
        elif self.comparison == "lt":
            return value < self.threshold
        elif self.comparison == "gte":
            return value >= self.threshold
        elif self.comparison == "lte":
            return value <= self.threshold
        elif self.comparison == "eq":
            return value == self.threshold
        return False


@dataclass
class Alert:
    """An active alert."""
    rule_name: str
    metric: str
    value: float
    threshold: float
    severity: str
    timestamp: str
    labels: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "severity": self.severity,
            "timestamp": self.timestamp,
            "labels": self.labels,
        }


class TimeSeriesStore:
    """In-memory time-series storage with SQLite persistence."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self._db_path = str(db_path)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._lock = threading.Lock()
        self._create_tables()

    def _create_tables(self) -> None:
        """Create the metrics table."""
        with self._lock:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    labels TEXT DEFAULT '{}'
                )
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_name_time
                ON metrics (name, timestamp)
            """)
            self._conn.commit()

    def write(self, point: MetricPoint) -> None:
        """Write a metric point."""
        with self._lock:
            self._conn.execute(
                "INSERT INTO metrics (name, value, timestamp, labels) VALUES (?, ?, ?, ?)",
                (point.name, point.value, point.timestamp, json.dumps(point.labels)),
            )
            self._conn.commit()

    def query(
        self,
        name: str,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int = 1000,
    ) -> list[MetricPoint]:
        """Query metric points."""
        query = "SELECT name, value, timestamp, labels FROM metrics WHERE name = ?"
        params: list[Any] = [name]

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            rows = self._conn.execute(query, params).fetchall()

        return [
            MetricPoint(
                name=row[0],
                value=row[1],
                timestamp=row[2],
                labels=json.loads(row[3]),
            )
            for row in rows
        ]

    def aggregate(
        self,
        name: str,
        window_seconds: int = 60,
        agg_func: str = "avg",
    ) -> list[dict[str, Any]]:
        """Aggregate metrics over time windows."""
        now = datetime.now(timezone.utc)
        window_start = (now - timedelta(seconds=window_seconds)).isoformat()

        points = self.query(name, start_time=window_start, limit=10000)
        if not points:
            return []

        values = [p.value for p in points]
        if agg_func == "avg":
            result = sum(values) / len(values)
        elif agg_func == "sum":
            result = sum(values)
        elif agg_func == "min":
            result = min(values)
        elif agg_func == "max":
            result = max(values)
        elif agg_func == "count":
            result = len(values)
        else:
            result = sum(values) / len(values)

        return [
            {
                "name": name,
                "window_start": window_start,
                "window_end": now.isoformat(),
                "aggregation": agg_func,
                "value": result,
                "count": len(values),
            }
        ]

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()


class MonitoringPipeline:
    """Real-time monitoring pipeline for metrics collection and alerting."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.store = TimeSeriesStore(db_path)
        self._alert_rules: dict[str, AlertRule] = {}
        self._active_alerts: list[Alert] = []
        self._collectors: list[Callable[[], list[MetricPoint]]] = []
        self._running = False
        self._thread: threading.Thread | None = None

    def add_alert_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        self._alert_rules[rule.name] = rule

    def remove_alert_rule(self, name: str) -> None:
        """Remove an alert rule."""
        self._alert_rules.pop(name, None)

    def add_collector(self, collector: Callable[[], list[MetricPoint]]) -> None:
        """Add a metric collector function."""
        self._collectors.append(collector)

    def record(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Record a metric point."""
        point = MetricPoint(
            name=name,
            value=value,
            timestamp=datetime.now(timezone.utc).isoformat(),
            labels=labels or {},
        )
        self.store.write(point)
        self._check_alerts(point)

    def _check_alerts(self, point: MetricPoint) -> None:
        """Check if any alert rules are triggered."""
        for rule in self._alert_rules.values():
            if rule.metric != point.name:
                continue
            if rule.check(point.value):
                now = time.time()
                if rule._triggered_at is None:
                    rule._triggered_at = now
                    if rule.duration <= 0:
                        alert = Alert(
                            rule_name=rule.name,
                            metric=point.name,
                            value=point.value,
                            threshold=rule.threshold,
                            severity=rule.severity,
                            timestamp=point.timestamp,
                            labels=rule.labels,
                        )
                        self._active_alerts.append(alert)
                elif now - rule._triggered_at >= rule.duration:
                    alert = Alert(
                        rule_name=rule.name,
                        metric=point.name,
                        value=point.value,
                        threshold=rule.threshold,
                        severity=rule.severity,
                        timestamp=point.timestamp,
                        labels=rule.labels,
                    )
                    self._active_alerts.append(alert)
            else:
                rule._triggered_at = None

    def get_active_alerts(self) -> list[Alert]:
        """Get all active alerts."""
        return list(self._active_alerts)

    def clear_alerts(self) -> None:
        """Clear all active alerts."""
        self._active_alerts.clear()

    def get_metrics(
        self,
        name: str,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int = 1000,
    ) -> list[MetricPoint]:
        """Get metric points."""
        return self.store.query(name, start_time, end_time, limit)

    def get_dashboard_data(self) -> dict[str, Any]:
        """Get data for the monitoring dashboard."""
        now = datetime.now(timezone.utc)
        one_hour_ago = (now - timedelta(hours=1)).isoformat()

        # Get all unique metric names
        all_points = self.store.query("", start_time=one_hour_ago, limit=10000)
        metric_names = set(p.name for p in all_points)

        metrics_summary = {}
        for name in metric_names:
            points = self.store.query(name, start_time=one_hour_ago, limit=1000)
            if points:
                values = [p.value for p in points]
                metrics_summary[name] = {
                    "latest": values[0] if values else 0,
                    "avg": sum(values) / len(values) if values else 0,
                    "min": min(values) if values else 0,
                    "max": max(values) if values else 0,
                    "count": len(values),
                }

        return {
            "timestamp": now.isoformat(),
            "metrics": metrics_summary,
            "active_alerts": [a.to_dict() for a in self._active_alerts],
            "alert_count": len(self._active_alerts),
        }

    def start(self, interval: float = 10.0) -> None:
        """Start the monitoring pipeline in a background thread."""
        self._running = True

        def _run():
            while self._running:
                for collector in self._collectors:
                    try:
                        points = collector()
                        for point in points:
                            self.record(point.name, point.value, point.labels)
                    except Exception:
                        pass
                time.sleep(interval)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the monitoring pipeline."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def close(self) -> None:
        """Close the pipeline and release resources."""
        self.stop()
        self.store.close()
