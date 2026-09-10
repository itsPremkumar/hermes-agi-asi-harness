"""Observability & Evaluation Pipeline — Core module."""
from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class TraceStatus(Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Metric:
    name: str
    metric_type: MetricType
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    description: str = ""


@dataclass
class Trace:
    trace_id: str
    name: str
    status: TraceStatus = TraceStatus.STARTED
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    spans: list[dict[str, Any]] = field(default_factory=list)

    def complete(self, metadata: dict[str, Any] | None = None):
        self.status = TraceStatus.COMPLETED
        self.end_time = time.time()
        if metadata:
            self.metadata.update(metadata)

    def fail(self, error: str):
        self.status = TraceStatus.FAILED
        self.end_time = time.time()
        self.metadata["error"] = error

    @property
    def duration_ms(self) -> float:
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000


@dataclass
class EvaluationResult:
    run_id: str
    benchmark: str
    score: float
    target: float
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def gap(self) -> float:
        return self.target - self.score


class LangSmithClient:
    """Client for LangSmith observability integration."""

    def __init__(self, api_key: str | None = None, project: str = "aetheria"):
        self.api_key = api_key or ""
        self.project = project
        self._traces: list[Trace] = []
        self._metrics: list[Metric] = []

    def start_trace(self, name: str, metadata: dict[str, Any] | None = None) -> Trace:
        trace = Trace(
            trace_id=str(uuid.uuid4()),
            name=name,
            metadata=metadata or {},
        )
        self._traces.append(trace)
        return trace

    def record_metric(self, name: str, value: float, metric_type: MetricType = MetricType.GAUGE, labels: dict[str, str] | None = None):
        metric = Metric(
            name=name,
            metric_type=metric_type,
            value=value,
            labels=labels or {},
        )
        self._metrics.append(metric)

    def get_traces(self, status: TraceStatus | None = None) -> list[Trace]:
        if status is None:
            return list(self._traces)
        return [t for t in self._traces if t.status == status]

    def get_metrics(self, name: str | None = None) -> list[Metric]:
        if name is None:
            return list(self._metrics)
        return [m for m in self._metrics if m.name == name]

    def get_summary(self) -> dict[str, Any]:
        traces = self._traces
        completed = len([t for t in traces if t.status == TraceStatus.COMPLETED])
        failed = len([t for t in traces if t.status == TraceStatus.FAILED])
        total_duration = sum(t.duration_ms for t in traces)
        return {
            "project": self.project,
            "total_traces": len(traces),
            "completed": completed,
            "failed": failed,
            "success_rate": completed / len(traces) if traces else 0.0,
            "total_duration_ms": total_duration,
            "metrics_recorded": len(self._metrics),
        }


class ObservabilityPipeline:
    """Main observability pipeline for Aetheria."""

    def __init__(self, langsmith_api_key: str | None = None):
        self.langsmith = LangSmithClient(api_key=langsmith_api_key)
        self._metrics: list[Metric] = []
        self._evaluations: list[EvaluationResult] = []

    def record_latency(self, operation: str, duration_ms: float, labels: dict[str, str] | None = None):
        self.langsmith.record_metric(
            name=f"{operation}_latency_ms",
            value=duration_ms,
            metric_type=MetricType.HISTOGRAM,
            labels=labels or {},
        )

    def record_token_usage(self, model: str, tokens: int, cost_usd: float):
        self.langsmith.record_metric(
            name="llm_tokens_total",
            value=float(tokens),
            metric_type=MetricType.COUNTER,
            labels={"model": model},
        )
        self.langsmith.record_metric(
            name="llm_cost_usd",
            value=cost_usd,
            metric_type=MetricType.COUNTER,
            labels={"model": model},
        )

    def record_task_completion(self, task_id: str, assignee: str, duration_ms: float, success: bool):
        self.langsmith.record_metric(
            name="kanban_task_duration_ms",
            value=duration_ms,
            metric_type=MetricType.HISTOGRAM,
            labels={"assignee": assignee, "status": "success" if success else "failure"},
        )

    def evaluate_benchmark(self, benchmark: str, score: float, target: float, details: dict[str, Any] | None = None) -> EvaluationResult:
        result = EvaluationResult(
            run_id=str(uuid.uuid4())[:8],
            benchmark=benchmark,
            score=score,
            target=target,
            passed=score >= target,
            details=details or {},
        )
        self._evaluations.append(result)
        self.langsmith.record_metric(
            name="benchmark_score",
            value=score,
            metric_type=MetricType.GAUGE,
            labels={"benchmark": benchmark},
        )
        return result

    def get_evaluation_summary(self) -> dict[str, Any]:
        if not self._evaluations:
            return {"total": 0, "passed": 0, "failed": 0, "pass_rate": 0.0}
        passed = sum(1 for e in self._evaluations if e.passed)
        return {
            "total": len(self._evaluations),
            "passed": passed,
            "failed": len(self._evaluations) - passed,
            "pass_rate": passed / len(self._evaluations) * 100,
            "evaluations": [
                {
                    "benchmark": e.benchmark,
                    "score": e.score,
                    "target": e.target,
                    "passed": e.passed,
                }
                for e in self._evaluations
            ],
        }

    def generate_report(self) -> dict[str, Any]:
        return {
            "langsmith": self.langsmith.get_summary(),
            "evaluations": self.get_evaluation_summary(),
            "metrics_total": len(self.langsmith._metrics),
        }

    def save_report(self, path: str) -> None:
        report = self.generate_report()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(report, f, indent=2, default=str)
