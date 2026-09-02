"""Tests for Performance Telemetry."""

import os
import sys
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src"))

from harness.telemetry import (
    PerformanceTelemetry,
    MetricType,
    AlertSeverity,
    AlertRule,
    Alert,
    TimerContext,
)


class TestPerformanceTelemetry:
    def test_create(self):
        tel = PerformanceTelemetry()
        assert tel is not None

    def test_record(self):
        tel = PerformanceTelemetry()
        tel.record("cpu_usage", 50.0)
        metrics = tel.get_metrics("cpu_usage")
        assert len(metrics) == 1
        assert metrics[0].value == 50.0

    def test_increment(self):
        tel = PerformanceTelemetry()
        tel.increment("requests")
        tel.increment("requests")
        metrics = tel.get_metrics("requests")
        assert len(metrics) == 2

    def test_histogram(self):
        tel = PerformanceTelemetry()
        tel.histogram("response_time", 150.0)
        metrics = tel.get_metrics("response_time")
        assert len(metrics) == 1

    def test_timer(self):
        tel = PerformanceTelemetry()
        with tel.timer("operation"):
            time.sleep(0.01)
        metrics = tel.get_metrics("operation")
        assert len(metrics) == 1
        assert metrics[0].value > 0

    def test_add_alert_rule(self):
        tel = PerformanceTelemetry()
        rule = AlertRule("r1", "High CPU", "cpu", 90.0)
        tel.add_alert_rule(rule)
        assert len(tel._alert_rules) == 1

    def test_remove_alert_rule(self):
        tel = PerformanceTelemetry()
        rule = AlertRule("r1", "High CPU", "cpu", 90.0)
        tel.add_alert_rule(rule)
        tel.remove_alert_rule("r1")
        assert len(tel._alert_rules) == 0

    def test_get_alerts(self):
        tel = PerformanceTelemetry()
        rule = AlertRule("r1", "High CPU", "cpu", 90.0, comparison="gt")
        tel.add_alert_rule(rule)
        tel.record("cpu", 95.0)
        alerts = tel.get_alerts()
        assert len(alerts) == 1

    def test_resolve_alert(self):
        tel = PerformanceTelemetry()
        rule = AlertRule("r1", "High CPU", "cpu", 90.0)
        tel.add_alert_rule(rule)
        tel.record("cpu", 95.0)
        alert_id = tel.get_alerts()[0].alert_id
        assert tel.resolve_alert(alert_id) is True
        assert tel.get_alerts()[0].resolved is True

    def test_get_stats(self):
        tel = PerformanceTelemetry()
        tel.record("cpu", 50.0)
        tel.record("cpu", 60.0)
        tel.record("cpu", 70.0)
        stats = tel.get_stats("cpu")
        assert stats["count"] == 3
        assert stats["min"] == 50.0
        assert stats["max"] == 70.0

    def test_summary(self):
        tel = PerformanceTelemetry()
        tel.record("cpu", 50.0)
        tel.record("mem", 70.0)
        summary = tel.summary()
        assert summary["total_metrics"] == 2
        assert summary["unique_metrics"] == 2

    def test_get_metrics_with_labels(self):
        tel = PerformanceTelemetry()
        tel.record("cpu", 50.0, labels={"host": "server1"})
        tel.record("cpu", 60.0, labels={"host": "server2"})
        metrics = tel.get_metrics("cpu", labels={"host": "server1"})
        assert len(metrics) == 1
        assert metrics[0].value == 50.0


class TestAlertRule:
    def test_create(self):
        rule = AlertRule("r1", "High CPU", "cpu", 90.0)
        assert rule.rule_id == "r1"
        assert rule.enabled is True

    def test_create_custom_comparison(self):
        rule = AlertRule("r1", "Low CPU", "cpu", 10.0, comparison="lt")
        assert rule.comparison == "lt"
