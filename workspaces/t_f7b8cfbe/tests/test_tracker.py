"""
Tests for PerformanceTracker module.
"""

from __future__ import annotations

import pytest

from src.harness.improvement.tracker import (
    ABTest,
    MetricSnapshot,
    MetricType,
    PerformanceTracker,
    TrendAnalysis,
)


@pytest.fixture
def tracker() -> PerformanceTracker:
    return PerformanceTracker()


class TestMetricSnapshot:
    def test_snapshot_creation(self) -> None:
        s = MetricSnapshot(name="latency", value=100.0, metric_type=MetricType.LATENCY)
        assert s.name == "latency"
        assert s.value == 100.0
        assert s.metric_type == MetricType.LATENCY

    def test_snapshot_with_labels(self) -> None:
        s = MetricSnapshot(name="test", value=1.0, metric_type=MetricType.LATENCY, labels={"env": "prod"})
        assert s.labels["env"] == "prod"


class TestABTest:
    def test_ab_test_creation(self) -> None:
        t = ABTest(test_id="t1", name="Test", variant_a="A", variant_b="B", metric_name="latency")
        assert t.test_id == "t1"
        assert t.winner is None

    def test_add_samples(self) -> None:
        t = ABTest(test_id="t1", name="Test", variant_a="A", variant_b="B", metric_name="latency")
        t.add_sample_a(100.0)
        t.add_sample_a(110.0)
        t.add_sample_b(90.0)
        t.add_sample_b(95.0)
        assert len(t.samples_a) == 2
        assert len(t.samples_b) == 2

    def test_means(self) -> None:
        t = ABTest(test_id="t1", name="Test", variant_a="A", variant_b="B", metric_name="latency")
        t.add_sample_a(100.0)
        t.add_sample_a(200.0)
        t.add_sample_b(50.0)
        t.add_sample_b(150.0)
        assert t.mean_a == 150.0
        assert t.mean_b == 100.0

    def test_std_dev(self) -> None:
        t = ABTest(test_id="t1", name="Test", variant_a="A", variant_b="B", metric_name="latency")
        t.add_sample_a(100.0)
        t.add_sample_a(200.0)
        assert t.std_a > 0

    def test_improvement_pct(self) -> None:
        t = ABTest(test_id="t1", name="Test", variant_a="A", variant_b="B", metric_name="latency")
        t.add_sample_a(100.0)
        t.add_sample_b(80.0)
        assert t.improvement_pct == -20.0


class TestPerformanceTracker:
    def test_record_metric(self, tracker: PerformanceTracker) -> None:
        s = tracker.record_metric("latency", 100.0)
        assert s.name == "latency"
        assert s.value == 100.0

    def test_get_history(self, tracker: PerformanceTracker) -> None:
        tracker.record_metric("latency", 100.0)
        tracker.record_metric("latency", 200.0)
        history = tracker.get_history("latency")
        assert len(history) == 2

    def test_get_latest(self, tracker: PerformanceTracker) -> None:
        tracker.record_metric("latency", 100.0)
        tracker.record_metric("latency", 200.0)
        latest = tracker.get_latest("latency")
        assert latest is not None
        assert latest.value == 200.0

    def test_get_latest_empty(self, tracker: PerformanceTracker) -> None:
        assert tracker.get_latest("nonexistent") is None

    def test_get_statistics(self, tracker: PerformanceTracker) -> None:
        for v in [10.0, 20.0, 30.0, 40.0, 50.0]:
            tracker.record_metric("test", v)
        stats = tracker.get_statistics("test")
        assert stats["count"] == 5
        assert stats["mean"] == 30.0
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0

    def test_get_statistics_empty(self, tracker: PerformanceTracker) -> None:
        stats = tracker.get_statistics("nonexistent")
        assert stats["count"] == 0

    def test_set_baseline(self, tracker: PerformanceTracker) -> None:
        tracker.set_baseline("latency", 100.0)
        assert tracker.get_baseline("latency") == 100.0

    def test_compare_to_baseline(self, tracker: PerformanceTracker) -> None:
        tracker.set_baseline("latency", 100.0)
        tracker.record_metric("latency", 80.0)
        comparison = tracker.compare_to_baseline("latency")
        assert comparison["has_comparison"] is True
        assert comparison["delta"] == -20.0
        assert comparison["improved"] is True

    def test_compare_to_baseline_no_baseline(self, tracker: PerformanceTracker) -> None:
        tracker.record_metric("latency", 80.0)
        comparison = tracker.compare_to_baseline("latency")
        assert comparison["has_comparison"] is False

    def test_create_ab_test(self, tracker: PerformanceTracker) -> None:
        t = tracker.create_ab_test("test1", "My Test", "A", "B", "latency")
        assert t.test_id == "test1"
        assert "test1" in tracker.ab_test_ids

    def test_get_ab_test(self, tracker: PerformanceTracker) -> None:
        tracker.create_ab_test("test1", "My Test", "A", "B", "latency")
        t = tracker.get_ab_test("test1")
        assert t is not None
        assert t.name == "My Test"

    def test_conclude_ab_test(self, tracker: PerformanceTracker) -> None:
        t = tracker.create_ab_test("test1", "My Test", "A", "B", "latency")
        for _ in range(20):
            t.add_sample_a(100.0)
            t.add_sample_b(80.0)
        result = tracker.conclude_ab_test("test1")
        assert result is not None
        assert result.winner == "B"
        assert result.confidence >= 0.95

    def test_conclude_ab_test_inconclusive(self, tracker: PerformanceTracker) -> None:
        t = tracker.create_ab_test("test1", "My Test", "A", "B", "latency")
        t.add_sample_a(100.0)
        t.add_sample_b(101.0)
        result = tracker.conclude_ab_test("test1")
        assert result is not None
        assert result.winner == "inconclusive"

    def test_analyze_trend_improving(self, tracker: PerformanceTracker) -> None:
        for i in range(10):
            tracker.record_metric("accuracy", float(i) * 0.1)
        trend = tracker.analyze_trend("accuracy")
        assert trend is not None
        assert trend.direction == "improving"
        assert trend.slope > 0

    def test_analyze_trend_declining(self, tracker: PerformanceTracker) -> None:
        for i in range(10):
            tracker.record_metric("latency", float(i) * 10.0)
        trend = tracker.analyze_trend("latency")
        assert trend is not None
        assert trend.direction == "declining"

    def test_analyze_trend_stable(self, tracker: PerformanceTracker) -> None:
        for _ in range(10):
            tracker.record_metric("stable_metric", 100.0)
        trend = tracker.analyze_trend("stable_metric")
        assert trend is not None
        assert trend.direction == "stable"

    def test_analyze_trend_empty(self, tracker: PerformanceTracker) -> None:
        trend = tracker.analyze_trend("nonexistent")
        assert trend is None

    def test_detect_anomalies(self, tracker: PerformanceTracker) -> None:
        for _ in range(20):
            tracker.record_metric("metric", 100.0)
        tracker.record_metric("metric", 500.0)
        anomalies = tracker.detect_anomalies("metric")
        assert len(anomalies) == 1
        assert anomalies[0].value == 500.0

    def test_detect_anomalies_too_few(self, tracker: PerformanceTracker) -> None:
        tracker.record_metric("metric", 100.0)
        tracker.record_metric("metric", 500.0)
        anomalies = tracker.detect_anomalies("metric")
        assert len(anomalies) == 0

    def test_get_improvement_report(self, tracker: PerformanceTracker) -> None:
        tracker.record_metric("latency", 100.0)
        tracker.set_baseline("latency", 120.0)
        tracker.create_ab_test("t1", "Test", "A", "B", "latency")
        report = tracker.get_improvement_report()
        assert report["metrics_tracked"] == 1
        assert report["baselines_set"] == 1
        assert report["ab_tests"] == 1

    def test_metric_names(self, tracker: PerformanceTracker) -> None:
        tracker.record_metric("a", 1.0)
        tracker.record_metric("b", 2.0)
        assert "a" in tracker.metric_names
        assert "b" in tracker.metric_names

    def test_trend_with_window(self, tracker: PerformanceTracker) -> None:
        for i in range(20):
            tracker.record_metric("metric", float(i))
        trend = tracker.analyze_trend("metric", window=5)
        assert trend is not None
        assert trend.data_points == 5
