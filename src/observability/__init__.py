"""Observability & Evaluation Layer — Metrics, Logging, Tracing, Evaluation."""
from __future__ import annotations

import time
import json
import uuid
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Protocol
from contextlib import contextmanager


# ─── Metrics ──────────────────────────────────────────────────────────────────

@dataclass
class MetricSample:
    """A single metric sample."""
    name: str
    value: float
    timestamp: str
    labels: dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """Collect and aggregate metrics."""

    def __init__(self) -> None:
        self._metrics: list[MetricSample] = []

    def record(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        self._metrics.append(MetricSample(
            name=name,
            value=value,
            timestamp=datetime.now(timezone.utc).isoformat(),
            labels=labels or {},
        ))

    def get(self, name: str) -> list[MetricSample]:
        return [m for m in self._metrics if m.name == name]

    def get_all(self) -> list[MetricSample]:
        return list(self._metrics)

    def summary(self) -> dict[str, dict[str, float]]:
        result: dict[str, list[float]] = {}
        for m in self._metrics:
            result.setdefault(m.name, []).append(m.value)
        return {
            name: {
                "count": len(values),
                "sum": sum(values),
                "avg": sum(values) / len(values) if values else 0,
                "min": min(values) if values else 0,
                "max": max(values) if values else 0,
            }
            for name, values in result.items()
        }

    def reset(self) -> None:
        self._metrics.clear()


# ─── Logging ──────────────────────────────────────────────────────────────────

@dataclass
class LogEntry:
    """A structured log entry."""
    timestamp: str
    level: str
    message: str
    source: str
    trace_id: str | None = None
    span_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class StructuredLogger:
    """Structured logger with trace support."""

    def __init__(self, source: str = "app") -> None:
        self.source = source
        self._logs: list[LogEntry] = []

    def _log(self, level: str, message: str, **kwargs: Any) -> LogEntry:
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level,
            message=message,
            source=self.source,
            trace_id=kwargs.get("trace_id"),
            span_id=kwargs.get("span_id"),
            metadata=kwargs,
        )
        self._logs.append(entry)
        return entry

    def info(self, message: str, **kwargs: Any) -> LogEntry:
        return self._log("INFO", message, **kwargs)

    def warn(self, message: str, **kwargs: Any) -> LogEntry:
        return self._log("WARN", message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> LogEntry:
        return self._log("ERROR", message, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> LogEntry:
        return self._log("DEBUG", message, **kwargs)

    def get_logs(self, level: str | None = None) -> list[LogEntry]:
        if level:
            return [l for l in self._logs if l.level == level]
        return list(self._logs)


# ─── Tracing ──────────────────────────────────────────────────────────────────

@dataclass
class Span:
    """A trace span."""
    trace_id: str
    span_id: str
    parent_span_id: str | None
    name: str
    start_time: str
    end_time: str | None = None
    status: str = "ok"
    metadata: dict[str, Any] = field(default_factory=dict)


class Tracer:
    """Distributed tracing."""

    def __init__(self) -> None:
        self._spans: list[Span] = []

    def start_span(self, name: str, parent: Span | None = None, **kwargs: Any) -> Span:
        span = Span(
            trace_id=parent.trace_id if parent else str(uuid.uuid4()),
            span_id=str(uuid.uuid4()),
            parent_span_id=parent.span_id if parent else None,
            name=name,
            start_time=datetime.now(timezone.utc).isoformat(),
            metadata=kwargs,
        )
        self._spans.append(span)
        return span

    def end_span(self, span: Span, status: str = "ok") -> None:
        span.end_time = datetime.now(timezone.utc).isoformat()
        span.status = status

    def get_spans(self, trace_id: str | None = None) -> list[Span]:
        if trace_id:
            return [s for s in self._spans if s.trace_id == trace_id]
        return list(self._spans)

    @contextmanager
    def span(self, name: str, **kwargs: Any):
        span = self.start_span(name, **kwargs)
        try:
            yield span
            self.end_span(span, "ok")
        except Exception:
            self.end_span(span, "error")
            raise


# ─── Evaluation ────────────────────────────────────────────────────────────────

@dataclass
class EvaluationResult:
    """Result of an evaluation run."""
    benchmark: str
    score: float
    total: int
    passed: int
    failed: int
    duration: float
    details: dict[str, Any] = field(default_factory=dict)


class EvaluationRunner:
    """Run evaluations against benchmarks."""

    def __init__(self) -> None:
        self._benchmarks: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, func: Callable[..., Any]) -> None:
        self._benchmarks[name] = func

    def run(self, name: str, *args: Any, **kwargs: Any) -> EvaluationResult:
        if name not in self._benchmarks:
            raise KeyError(f"Benchmark not found: {name}")
        start = time.perf_counter()
        try:
            result = self._benchmarks[name](*args, **kwargs)
            duration = time.perf_counter() - start
            return EvaluationResult(
                benchmark=name,
                score=result.get("score", 0),
                total=result.get("total", 0),
                passed=result.get("passed", 0),
                failed=result.get("failed", 0),
                duration=duration,
                details=result,
            )
        except Exception as e:
            duration = time.perf_counter() - start
            return EvaluationResult(
                benchmark=name,
                score=0,
                total=0,
                passed=0,
                failed=1,
                duration=duration,
                details={"error": str(e)},
            )

    def run_all(self) -> list[EvaluationResult]:
        return [self.run(name) for name in self._benchmarks]


# ─── Health Check ──────────────────────────────────────────────────────────────

class HealthChecker:
    """Health check system."""

    def __init__(self) -> None:
        self._checks: dict[str, Callable[[], bool]] = {}

    def register(self, name: str, check: Callable[[], bool]) -> None:
        self._checks[name] = check

    def check(self, name: str) -> bool:
        check = self._checks.get(name)
        return check() if check else False

    def check_all(self) -> dict[str, bool]:
        return {name: check() for name, check in self._checks.items()}

    def is_healthy(self) -> bool:
        return all(self.check_all().values())


# ─── Observability Facade ──────────────────────────────────────────────────────

class Observability:
    """Main observability facade."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.metrics = MetricsCollector()
        self.logger = StructuredLogger()
        self.tracer = Tracer()
        self.evaluations = EvaluationRunner()
        self.health = HealthChecker()
        self._db_path = str(db_path)

    def report(self) -> dict[str, Any]:
        return {
            "metrics": self.metrics.summary(),
            "log_count": len(self.logger.get_logs()),
            "span_count": len(self.tracer.get_spans()),
            "health": self.health.check_all(),
        }
