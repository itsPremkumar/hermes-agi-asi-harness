"""Tests for Observability & Evaluation Layer."""
from __future__ import annotations

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from observability import (
    MetricSample,
    MetricsCollector,
    LogEntry,
    StructuredLogger,
    Span,
    Tracer,
    EvaluationResult,
    EvaluationRunner,
    HealthChecker,
    Observability,
)


# ─── MetricsCollector Tests ────────────────────────────────────────────────────

class TestMetricsCollector:
    def test_record(self):
        m = MetricsCollector()
        m.record("cpu_usage", 75.5)
        assert len(m.get("cpu_usage")) == 1

    def test_get_all(self):
        m = MetricsCollector()
        m.record("cpu", 50)
        m.record("memory", 80)
        assert len(m.get_all()) == 2

    def test_summary(self):
        m = MetricsCollector()
        m.record("cpu", 50)
        m.record("cpu", 100)
        s = m.summary()
        assert s["cpu"]["count"] == 2
        assert s["cpu"]["avg"] == 75

    def test_reset(self):
        m = MetricsCollector()
        m.record("cpu", 50)
        m.reset()
        assert len(m.get_all()) == 0


# ─── StructuredLogger Tests ────────────────────────────────────────────────────

class TestStructuredLogger:
    def test_info(self):
        logger = StructuredLogger()
        entry = logger.info("Test message")
        assert entry.level == "INFO"
        assert entry.message == "Test message"

    def test_warn(self):
        logger = StructuredLogger()
        entry = logger.warn("Warning message")
        assert entry.level == "WARN"

    def test_error(self):
        logger = StructuredLogger()
        entry = logger.error("Error message")
        assert entry.level == "ERROR"

    def test_debug(self):
        logger = StructuredLogger()
        entry = logger.debug("Debug message")
        assert entry.level == "DEBUG"

    def test_get_logs_by_level(self):
        logger = StructuredLogger()
        logger.info("Info 1")
        logger.error("Error 1")
        logger.info("Info 2")
        assert len(logger.get_logs("INFO")) == 2
        assert len(logger.get_logs("ERROR")) == 1


# ─── Tracer Tests ──────────────────────────────────────────────────────────────

class TestTracer:
    def test_start_span(self):
        tracer = Tracer()
        span = tracer.start_span("test_op")
        assert span.name == "test_op"
        assert span.trace_id is not None

    def test_end_span(self):
        tracer = Tracer()
        span = tracer.start_span("test")
        tracer.end_span(span)
        assert span.end_time is not None
        assert span.status == "ok"

    def test_span_context_manager(self):
        tracer = Tracer()
        with tracer.span("test") as span:
            assert span.name == "test"
        assert span.end_time is not None

    def test_span_context_manager_error(self):
        tracer = Tracer()
        with pytest.raises(ValueError):
            with tracer.span("test") as span:
                raise ValueError("test error")

    def test_get_spans(self):
        tracer = Tracer()
        tracer.start_span("span1")
        tracer.start_span("span2")
        assert len(tracer.get_spans()) == 2


# ─── EvaluationRunner Tests ────────────────────────────────────────────────────

class TestEvaluationRunner:
    def test_register_and_run(self):
        runner = EvaluationRunner()
        runner.register("test", lambda: {"score": 0.9, "total": 10, "passed": 9, "failed": 1})
        result = runner.run("test")
        assert result.score == 0.9
        assert result.passed == 9

    def test_run_missing(self):
        runner = EvaluationRunner()
        with pytest.raises(KeyError):
            runner.run("nonexistent")

    def test_run_all(self):
        runner = EvaluationRunner()
        runner.register("a", lambda: {"score": 0.8, "total": 10, "passed": 8, "failed": 2})
        runner.register("b", lambda: {"score": 0.9, "total": 10, "passed": 9, "failed": 1})
        results = runner.run_all()
        assert len(results) == 2


# ─── HealthChecker Tests ───────────────────────────────────────────────────────

class TestHealthChecker:
    def test_register_and_check(self):
        hc = HealthChecker()
        hc.register("db", lambda: True)
        assert hc.check("db") is True

    def test_check_all(self):
        hc = HealthChecker()
        hc.register("db", lambda: True)
        hc.register("cache", lambda: False)
        results = hc.check_all()
        assert results["db"] is True
        assert results["cache"] is False

    def test_is_healthy(self):
        hc = HealthChecker()
        hc.register("db", lambda: True)
        assert hc.is_healthy() is True

    def test_is_healthy_false(self):
        hc = HealthChecker()
        hc.register("db", lambda: False)
        assert hc.is_healthy() is False


# ─── Observability Tests ───────────────────────────────────────────────────────

class TestObservability:
    def test_report(self):
        obs = Observability()
        obs.metrics.record("cpu", 50)
        obs.logger.info("Test")
        report = obs.report()
        assert "metrics" in report
        assert "log_count" in report
        assert "span_count" in report
        assert "health" in report
