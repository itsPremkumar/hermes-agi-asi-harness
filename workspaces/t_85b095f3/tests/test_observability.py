"""Tests for AgentOS observability module."""

from __future__ import annotations

import pytest

from agentos.observability import MetricsCollector, Observability, Span, Tracer


class TestSpan:
    def test_create_span(self) -> None:
        span = Span(
            trace_id="trace1",
            span_id="span1",
            parent_id=None,
            name="test",
            start_time=1000.0,
        )
        assert span.name == "test"
        assert span.duration_ms is None

    def test_end_span_sets_duration(self) -> None:
        span = Span(
            trace_id="trace1",
            span_id="span1",
            parent_id=None,
            name="test",
            start_time=1000.0,
        )
        span.end_time = 1001.5
        assert span.duration_ms == 1500.0

    def test_to_dict(self) -> None:
        span = Span(
            trace_id="trace1",
            span_id="span1",
            parent_id="parent1",
            name="test",
            start_time=1000.0,
            end_time=1001.0,
            status="ok",
        )
        d = span.to_dict()
        assert d["name"] == "test"
        assert d["status"] == "ok"


class TestTracer:
    def test_start_end_span(self) -> None:
        tracer = Tracer()
        span = tracer.start_span("test")
        tracer.end_span(span.span_id)
        assert len(tracer.get_spans()) == 1

    def test_span_context_manager(self) -> None:
        tracer = Tracer()
        with tracer.span("test") as span:
            assert span.status == "unset"
        assert span.status == "ok"

    def test_span_context_manager_error(self) -> None:
        tracer = Tracer()
        with pytest.raises(ValueError):
            with tracer.span("test") as span:
                raise ValueError("test error")
        assert span.status == "error"

    def test_get_spans_by_trace(self) -> None:
        tracer = Tracer()
        s1 = tracer.start_span("op1", trace_id="t1")
        s2 = tracer.start_span("op2", trace_id="t2")
        tracer.end_span(s1.span_id)
        tracer.end_span(s2.span_id)
        assert len(tracer.get_spans("t1")) == 1
        assert len(tracer.get_spans("t2")) == 1

    def test_clear_spans(self) -> None:
        tracer = Tracer()
        span = tracer.start_span("test")
        tracer.end_span(span.span_id)
        tracer.clear()
        assert len(tracer.get_spans()) == 0


class TestMetricsCollector:
    def test_counter(self) -> None:
        metrics = MetricsCollector()
        metrics.counter("requests")
        metrics.counter("requests")
        assert metrics.get_counter("requests") == 2.0

    def test_gauge(self) -> None:
        metrics = MetricsCollector()
        metrics.gauge("cpu_usage", 75.5)
        assert metrics.get_gauge("cpu_usage") == 75.5

    def test_histogram(self) -> None:
        metrics = MetricsCollector()
        metrics.histogram("latency", 100.0)
        metrics.histogram("latency", 200.0)
        h = metrics.get_metrics("latency", type="histogram")
        assert len(h) == 2

    def test_summary(self) -> None:
        metrics = MetricsCollector()
        metrics.counter("c1", 5.0)
        metrics.gauge("g1", 10.0)
        metrics.histogram("h1", 1.0)
        metrics.histogram("h1", 3.0)
        summary = metrics.summary()
        assert "counters" in summary
        assert "gauges" in summary
        assert "histograms" in summary
        assert summary["histograms"]["h1"]["avg"] == 2.0

    def test_metrics_with_labels(self) -> None:
        metrics = MetricsCollector()
        metrics.counter("requests", labels={"method": "GET", "status": "200"})
        key = 'requests{method="GET",status="200"}'
        assert metrics.get_counter("requests", labels={"method": "GET", "status": "200"}) == 1.0

    def test_clear(self) -> None:
        metrics = MetricsCollector()
        metrics.counter("test")
        metrics.clear()
        assert metrics.get_counter("test") == 0


class TestObservability:
    def test_trace_and_metrics(self) -> None:
        obs = Observability()
        with obs.trace("test_op"):
            pass
        assert len(obs.tracer.get_spans()) == 1
        assert len(obs.metrics.get_metrics("operation_duration_seconds")) == 1

    def test_health(self) -> None:
        obs = Observability()
        health = obs.health()
        assert health["status"] == "healthy"

    def test_record_error(self) -> None:
        obs = Observability()
        obs.record_error(ValueError("test"))
        assert obs.metrics.get_counter("errors_total", labels={"type": "ValueError"}) == 1.0
