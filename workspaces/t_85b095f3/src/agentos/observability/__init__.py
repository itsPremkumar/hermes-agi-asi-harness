"""Observability module with OpenTelemetry traces and metrics."""

from __future__ import annotations

import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class Span:
    """A trace span."""
    trace_id: str
    span_id: str
    parent_id: str | None
    name: str
    start_time: float
    end_time: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    status: str = "unset"  # unset, ok, error

    @property
    def duration_ms(self) -> float | None:
        if self.end_time is not None:
            return (self.end_time - self.start_time) * 1000
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "events": self.events,
            "status": self.status,
        }


@dataclass
class Metric:
    """A single metric data point."""
    name: str
    value: float
    timestamp: float
    labels: dict[str, str] = field(default_factory=dict)
    type: str = "gauge"  # gauge, counter, histogram


class Tracer:
    """Simple in-memory tracer compatible with OpenTelemetry concepts."""

    def __init__(self, service_name: str = "agentos") -> None:
        self.service_name = service_name
        self._spans: list[Span] = []
        self._active: dict[str, Span] = {}

    def start_span(self, name: str, trace_id: str | None = None,
                   parent_id: str | None = None,
                   attributes: dict[str, Any] | None = None) -> Span:
        """Start a new span."""
        import uuid

        span = Span(
            trace_id=trace_id or str(uuid.uuid4()),
            span_id=str(uuid.uuid4())[:16],
            parent_id=parent_id,
            name=name,
            start_time=time.time(),
            attributes=attributes or {},
        )
        self._active[span.span_id] = span
        return span

    def end_span(self, span_id: str, status: str = "ok") -> Span | None:
        """End a span."""
        span = self._active.pop(span_id, None)
        if span is None:
            return None

        span.end_time = time.time()
        span.status = status
        self._spans.append(span)
        return span

    @contextmanager
    def span(self, name: str, **attributes: Any) -> Iterator[Span]:
        """Context manager for span lifecycle."""
        span = self.start_span(name, attributes=attributes)
        try:
            yield span
        except Exception as e:
            span.status = "error"
            span.events.append({
                "name": "exception",
                "attributes": {"error": str(e)},
            })
            raise
        finally:
            if span.status != "error":
                span.status = "ok"
            self.end_span(span.span_id, span.status)

    def get_spans(self, trace_id: str | None = None) -> list[Span]:
        """Get all spans, optionally filtered by trace ID."""
        if trace_id:
            return [s for s in self._spans if s.trace_id == trace_id]
        return list(self._spans)

    def clear(self) -> None:
        """Clear all spans."""
        self._spans.clear()
        self._active.clear()


class MetricsCollector:
    """Collects and aggregates metrics."""

    def __init__(self) -> None:
        self._metrics: list[Metric] = []
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = defaultdict(float)

    def counter(self, name: str, value: float = 1.0,
                labels: dict[str, str] | None = None) -> None:
        """Increment a counter metric."""
        key = self._format_key(name, labels)
        self._counters[key] += value
        self._metrics.append(Metric(
            name=name,
            value=self._counters[key],
            timestamp=time.time(),
            labels=labels or {},
            type="counter",
        ))

    def gauge(self, name: str, value: float,
              labels: dict[str, str] | None = None) -> None:
        """Set a gauge metric."""
        key = self._format_key(name, labels)
        self._gauges[key] = value
        self._metrics.append(Metric(
            name=name,
            value=value,
            timestamp=time.time(),
            labels=labels or {},
            type="gauge",
        ))

    def histogram(self, name: str, value: float,
                  labels: dict[str, str] | None = None) -> None:
        """Record a histogram observation."""
        self._metrics.append(Metric(
            name=name,
            value=value,
            timestamp=time.time(),
            labels=labels or {},
            type="histogram",
        ))

    def get_counter(self, name: str, labels: dict[str, str] | None = None) -> float:
        """Get current counter value."""
        key = self._format_key(name, labels)
        return self._counters[key]

    def get_gauge(self, name: str, labels: dict[str, str] | None = None) -> float:
        """Get current gauge value."""
        key = self._format_key(name, labels)
        return self._gauges[key]

    def get_metrics(self, name: str | None = None,
                    type: str | None = None) -> list[Metric]:
        """Get metrics filtered by name and/or type."""
        result = self._metrics
        if name:
            result = [m for m in result if m.name == name]
        if type:
            result = [m for m in result if m.type == type]
        return result

    def summary(self) -> dict[str, Any]:
        """Get a summary of all metrics."""
        counters: dict[str, float] = {}
        gauges: dict[str, float] = {}
        histograms: dict[str, list[float]] = defaultdict(list)

        for m in self._metrics:
            key = self._format_key(m.name, m.labels)
            if m.type == "counter":
                counters[key] = m.value
            elif m.type == "gauge":
                gauges[key] = m.value
            elif m.type == "histogram":
                histograms[key].append(m.value)

        return {
            "counters": counters,
            "gauges": gauges,
            "histograms": {
                k: {
                    "count": len(v),
                    "min": min(v),
                    "max": max(v),
                    "avg": sum(v) / len(v) if v else 0,
                    "sum": sum(v),
                }
                for k, v in histograms.items()
            },
        }

    @staticmethod
    def _format_key(name: str, labels: dict[str, str] | None) -> str:
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def clear(self) -> None:
        """Clear all metrics."""
        self._metrics.clear()
        self._counters.clear()
        self._gauges.clear()


class Observability:
    """Combined observability with tracing and metrics."""

    def __init__(self, service_name: str = "agentos") -> None:
        self.tracer = Tracer(service_name)
        self.metrics = MetricsCollector()

    @contextmanager
    def trace(self, name: str, **attributes: Any) -> Iterator[Span]:
        """Context manager for tracing an operation."""
        with self.tracer.span(name, **attributes) as span:
            yield span
            self.metrics.histogram(
                "operation_duration_seconds",
                span.duration_ms / 1000 if span.duration_ms else 0,
                labels={"operation": name},
            )

    def record_error(self, error: Exception, **context: Any) -> None:
        """Record an error in both traces and metrics."""
        self.metrics.counter("errors_total", labels={"type": type(error).__name__})
        self.tracer.start_span(
            "error",
            attributes={"error": str(error), **context},
        )

    def health(self) -> dict[str, Any]:
        """Get health status."""
        return {
            "status": "healthy",
            "spans_recorded": len(self.tracer.get_spans()),
            "metrics_recorded": len(self.metrics.get_metrics()),
        }
