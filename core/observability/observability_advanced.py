"""Advanced observability — OpenTelemetry tracing, cost tracking, safety alerting, trace replay."""
from __future__ import annotations

import json
import os
import time
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from opentelemetry import trace, context, baggage
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SpanExporter,
    SpanExportResult,
)
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import SpanKind, StatusCode

# ---------------------------------------------------------------------------
# Structured export helper — exports spans as JSON for downstream consumers
# ---------------------------------------------------------------------------


class StructuredSpanExporter(SpanExporter):
    """Exports spans to a JSON-lines file with structured fields."""

    def __init__(self, output_path: str | Path | None = None) -> None:
        super().__init__()
        self._output = Path(output_path) if output_path else Path(
            os.environ.get("OTEL_EXPORTER_JSON_PATH", "traces.jsonl")
        )
        self._lock = threading.Lock()
        self._ensure_parent()

    def _ensure_parent(self) -> None:
        self._output.parent.mkdir(parents=True, exist_ok=True)

    def export(self, spans: List[ReadableSpan]) -> SpanExportResult:
        with self._lock:
            self._ensure_parent()
            with open(self._output, "a") as f:
                for span in spans:
                    record = self._span_to_dict(span)
                    f.write(json.dumps(record, default=str) + "\n")
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass

    @staticmethod
    def _span_to_dict(span: ReadableSpan) -> dict:
        return {
            "trace_id": format(span.context.trace_id, "032x"),
            "span_id": format(span.context.span_id, "016x"),
            "parent_span_id": format(span.parent.span_id, "016x") if span.parent else None,
            "name": span.name,
            "kind": span.kind.name,
            "start_time": span.start_time,
            "end_time": span.end_time,
            "duration_ms": (span.end_time - span.start_time) / 1_000_000 if span.end_time else None,
            "attributes": dict(span.attributes) if span.attributes else {},
            "events": [
                {"name": e.name, "timestamp": e.timestamp, "attributes": dict(e.attributes)}
                for e in span.events
            ],
            "status_code": span.status.status_code.name if span.status else None,
            "status_description": span.status.description if span.status else None,
            "resource_attributes": dict(span.resource.attributes) if span.resource else {},
            "scope": {
                "name": span.instrumentation_scope.name if span.instrumentation_scope else None,
                "version": span.instrumentation_scope.version if span.instrumentation_scope else None,
            },
            "dropped_attributes": span.dropped_attributes,
            "dropped_events": span.dropped_events,
        }


# ---------------------------------------------------------------------------
# TracerProviderManager — singleton OTel provider setup
# ---------------------------------------------------------------------------


class TracerProviderManager:
    """Manages the global OpenTelemetry TracerProvider with file + in-memory exporters."""

    _instance: Optional["TracerProviderManager"] = None
    _lock = threading.Lock()

    def __init__(self, service_name: str = "hermes-asi-harness") -> None:
        self._service_name = service_name
        self._in_memory = InMemorySpanExporter()
        self._structured: StructuredSpanExporter | None = None
        self._provider: TracerProvider | None = None
        self._tracer: trace.Tracer | None = None

    @classmethod
    def get(cls, service_name: str = "hermes-asi-harness") -> "TracerProviderManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(service_name)
        return cls._instance

    def configure(
        self,
        structured_export_path: str | Path | None = None,
        resource_attributes: dict | None = None,
    ) -> "TracerProviderManager":
        resource = Resource.create(
            {"service.name": self._service_name, **(resource_attributes or {})}
        )
        self._provider = TracerProvider(resource=resource)
        self._provider.add_span_processor(BatchSpanProcessor(self._in_memory))
        self._structured = StructuredSpanExporter(structured_export_path)
        self._provider.add_span_processor(BatchSpanProcessor(self._structured))
        trace.set_tracer_provider(self._provider)
        self._tracer = trace.get_tracer(__name__, "1.0.0")
        return self

    @property
    def tracer(self) -> trace.Tracer:
        if self._tracer is None:
            self.configure()
        return self._tracer

    @property
    def in_memory(self) -> InMemorySpanExporter:
        return self._in_memory

    @property
    def provider(self) -> TracerProvider | None:
        return self._provider

    def get_spans(self) -> List[ReadableSpan]:
        if self._provider is not None:
            try:
                self._provider.force_flush()
            except Exception:
                pass
        return self._in_memory.get_finished_spans()

    def clear_spans(self) -> None:
        self._in_memory.clear()

    def shutdown(self) -> None:
        if self._provider:
            self._provider.shutdown()
        TracerProviderManager._instance = None


# ---------------------------------------------------------------------------
# AgentCostTracker — cost / latency / token tracking per agent
# ---------------------------------------------------------------------------

@dataclass
class AgentCostRecord:
    agent_id: str
    run_id: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    input_cost_usd: float = 0.0
    output_cost_usd: float = 0.0
    latency_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict = field(default_factory=dict)


class AgentCostTracker:
    """Tracks per-agent cost, latency, and token usage."""

    def __init__(self) -> None:
        self._records: List[AgentCostRecord] = []
        self._lock = threading.Lock()
        self._pricing: Dict[str, Dict[str, float]] = {
            # defaults — overridden by configure()
            "default": {"input_per_1k": 0.005, "output_per_1k": 0.015},
        }

    def configure_pricing(self, model: str, input_per_1k: float, output_per_1k: float) -> None:
        self._pricing[model] = {"input_per_1k": input_per_1k, "output_per_1k": output_per_1k}

    def record(
        self,
        agent_id: str,
        run_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        metadata: dict | None = None,
    ) -> AgentCostRecord:
        pricing = self._pricing.get(model, self._pricing["default"])
        record = AgentCostRecord(
            agent_id=agent_id,
            run_id=run_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost_usd=round(input_tokens / 1000 * pricing["input_per_1k"], 6),
            output_cost_usd=round(output_tokens / 1000 * pricing["output_per_1k"], 6),
            latency_ms=latency_ms,
            metadata=metadata or {},
        )
        with self._lock:
            self._records.append(record)
        return record

    def get_agent_summary(self, agent_id: str) -> dict:
        with self._lock:
            records = [r for r in self._records if r.agent_id == agent_id]
        if not records:
            return {"agent_id": agent_id, "runs": 0}
        total_input = sum(r.input_tokens for r in records)
        total_output = sum(r.output_tokens for r in records)
        total_cost = sum(r.input_cost_usd + r.output_cost_usd for r in records)
        total_latency = sum(r.latency_ms for r in records)
        return {
            "agent_id": agent_id,
            "runs": len(records),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cost_usd": round(total_cost, 6),
            "avg_latency_ms": round(total_latency / len(records), 3),
            "total_latency_ms": round(total_latency, 3),
        }

    def get_all_summaries(self) -> List[dict]:
        agent_ids: set[str] = set()
        with self._lock:
            for r in self._records:
                agent_ids.add(r.agent_id)
        return [self.get_agent_summary(a) for a in sorted(agent_ids)]

    def get_total_cost(self) -> float:
        with self._lock:
            return round(sum(r.input_cost_usd + r.output_cost_usd for r in self._records), 6)

    def export_json(self, path: str | Path) -> dict:
        payload = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "records": [
                {
                    "agent_id": r.agent_id,
                    "run_id": r.run_id,
                    "model": r.model,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "input_cost_usd": r.input_cost_usd,
                    "output_cost_usd": r.output_cost_usd,
                    "latency_ms": r.latency_ms,
                    "timestamp": r.timestamp,
                    "metadata": r.metadata,
                }
                for r in self._records
            ],
            "summaries": self.get_all_summaries(),
            "total_cost_usd": self.get_total_cost(),
        }
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, indent=2))
        return payload


# ---------------------------------------------------------------------------
# SafetyAlertManager — real-time alerting on safety violations
# ---------------------------------------------------------------------------

@dataclass
class SafetyAlert:
    alert_id: str
    severity: str  # info | warning | critical | emergency
    category: str
    message: str
    agent_id: str | None
    trace_id: str | None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict = field(default_factory=dict)
    acknowledged: bool = False


class SafetyAlertManager:
    """Real-time safety alerting with severity thresholds and callbacks."""

    SEVERITIES = {"info", "warning", "critical", "emergency"}
    _DEFAULT_THRESHOLDS = {"critical": 1, "emergency": 1}  # fire immediately

    def __init__(self) -> None:
        self._alerts: List[SafetyAlert] = []
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[SafetyAlert], None]] = []
        self._thresholds: Dict[str, int] = dict(self._DEFAULT_THRESHOLDS)
        self._counts: Dict[str, int] = {sev: 0 for sev in self.SEVERITIES}

    def on_alert(self, callback: Callable[[SafetyAlert], None]) -> None:
        self._callbacks.append(callback)

    def set_threshold(self, severity: str, count: int) -> None:
        if severity not in self.SEVERITIES:
            raise ValueError(f"severity must be one of {self.SEVERITIES}")
        self._thresholds[severity] = count

    def alert(
        self,
        severity: str,
        category: str,
        message: str,
        agent_id: str | None = None,
        trace_id: str | None = None,
        metadata: dict | None = None,
    ) -> SafetyAlert:
        if severity not in self.SEVERITIES:
            raise ValueError(f"Invalid severity: {severity}")
        alert = SafetyAlert(
            alert_id=str(uuid.uuid4()),
            severity=severity,
            category=category,
            message=message,
            agent_id=agent_id,
            trace_id=trace_id,
            metadata=metadata or {},
        )
        with self._lock:
            self._alerts.append(alert)
            self._counts[severity] = self._counts.get(severity, 0) + 1
            count = self._counts[severity]
        # Fire callbacks when threshold is met
        if count >= self._thresholds.get(severity, 999):
            for cb in self._callbacks:
                try:
                    cb(alert)
                except Exception:
                    pass
        return alert

    # --- convenience helpers ---

    def safety_violation(
        self, violation_type: str, detail: str, agent_id: str | None = None, trace_id: str | None = None
    ) -> SafetyAlert:
        return self.alert(
            severity="critical",
            category=f"safety:{violation_type}",
            message=detail,
            agent_id=agent_id,
            trace_id=trace_id,
        )

    def injection_attempt(self, payload: str, agent_id: str | None = None, trace_id: str | None = None) -> SafetyAlert:
        return self.alert(
            severity="critical",
            category="safety:injection",
            message=f"Injection attempt detected: {payload[:200]}",
            agent_id=agent_id,
            trace_id=trace_id,
            metadata={"payload_sample": payload[:200]},
        )

    def self_replicate_guard(self, detail: str, agent_id: str | None = None, trace_id: str | None = None) -> SafetyAlert:
        return self.alert(
            severity="emergency",
            category="safety:self-replicate",
            message=detail,
            agent_id=agent_id,
            trace_id=trace_id,
        )

    # --- queries ---

    def get_alerts(self, severity: str | None = None, category: str | None = None) -> List[SafetyAlert]:
        with self._lock:
            alerts = list(self._alerts)
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if category:
            alerts = [a for a in alerts if a.category == category]
        return alerts

    def get_summary(self) -> dict:
        with self._lock:
            return {
                "total_alerts": len(self._alerts),
                "by_severity": {sev: self._counts.get(sev, 0) for sev in self.SEVERITIES},
                "unacknowledged": sum(1 for a in self._alerts if not a.acknowledged),
            }

    def acknowledge(self, alert_id: str) -> bool:
        with self._lock:
            for a in self._alerts:
                if a.alert_id == alert_id:
                    a.acknowledged = True
                    return True
        return False

    def export_json(self, path: str | Path) -> dict:
        payload = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "alerts": [
                {
                    "alert_id": a.alert_id,
                    "severity": a.severity,
                    "category": a.category,
                    "message": a.message,
                    "agent_id": a.agent_id,
                    "trace_id": a.trace_id,
                    "timestamp": a.timestamp,
                    "metadata": a.metadata,
                    "acknowledged": a.acknowledged,
                }
                for a in self._alerts
            ],
            "summary": self.get_summary(),
        }
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, indent=2))
        return payload


# ---------------------------------------------------------------------------
# TraceReplayEngine — replay traces from exported spans
# ---------------------------------------------------------------------------

@dataclass
class ReplayEvent:
    timestamp: float
    event_name: str
    attributes: dict
    span_name: str
    agent_id: str | None


class TraceReplayEngine:
    """Replays traces: filters, sequences events, and reconstructs agent runs."""

    def __init__(self, tracer_manager: TracerProviderManager | None = None) -> None:
        self._tracer_manager = tracer_manager or TracerProviderManager.get()
        self._replay_hooks: List[Callable[[ReplayEvent], None]] = []

    def on_event(self, callback: Callable[[ReplayEvent], None]) -> None:
        self._replay_hooks.append(callback)

    def load_spans(self, source: List[ReadableSpan] | None = None) -> List[ReadableSpan]:
        return list(source) if source is not None else list(self._tracer_manager.get_spans())

    def filter(
        self,
        spans: List[ReadableSpan] | None = None,
        agent_id: str | None = None,
        span_name: str | None = None,
        min_duration_ms: float | None = None,
    ) -> List[ReadableSpan]:
        spans = self.load_spans(spans)
        result = spans
        if agent_id is not None:
            result = [s for s in result if s.attributes.get("agent.id") == agent_id]
        if span_name is not None:
            result = [s for s in result if s.name == span_name]
        if min_duration_ms is not None:
            result = [s for s in result if (s.end_time - s.start_time) / 1000 >= min_duration_ms * 1000]
        return result

    def replay(
        self,
        spans: List[ReadableSpan] | None = None,
        agent_id: str | None = None,
        span_name: str | None = None,
    ) -> List[ReplayEvent]:
        filtered = self.filter(spans, agent_id=agent_id, span_name=span_name)
        events: List[ReplayEvent] = []
        for span in sorted(filtered, key=lambda s: s.start_time):
            attrs = dict(span.attributes) if span.attributes else {}
            agent = attrs.pop("agent.id", None)
            for evt in span.events:
                ev = ReplayEvent(
                    timestamp=evt.timestamp,
                    event_name=evt.name,
                    attributes=dict(evt.attributes),
                    span_name=span.name,
                    agent_id=agent,
                )
                events.append(ev)
                for cb in self._replay_hooks:
                    try:
                        cb(ev)
                    except Exception:
                        pass
        return events

    def reconstruct_runs(self, spans: List[ReadableSpan] | None = None) -> Dict[str, List[dict]]:
        """Group spans by trace_id to reconstruct full agent runs."""
        spans = self.load_spans(spans)
        runs: Dict[str, List[dict]] = {}
        for span in spans:
            tid = format(span.context.trace_id, "032x")
            runs.setdefault(tid, []).append(
                {
                    "span_id": format(span.context.span_id, "016x"),
                    "name": span.name,
                    "duration_ms": (span.end_time - span.start_time) / 1_000_000 if span.end_time else 0,
                    "attributes": dict(span.attributes) if span.attributes else {},
                    "events": [e.name for e in span.events],
                }
            )
        return runs

    def timeline(self, spans: List[ReadableSpan] | None = None) -> List[dict]:
        """Flat chronological timeline of all span start/end events."""
        spans = self.load_spans(spans)
        timeline: List[dict] = []
        for span in spans:
            timeline.append({"time": span.start_time, "event": "start", "span": span.name})
            if span.end_time:
                timeline.append({"time": span.end_time, "event": "end", "span": span.name})
        timeline.sort(key=lambda e: e["time"])
        return timeline


# ---------------------------------------------------------------------------
# High-level facade — single function to wire up everything
# ---------------------------------------------------------------------------


class advanced_observability:
    """Facade that wires up TracerProviderManager, AgentCostTracker,
    SafetyAlertManager, and TraceReplayEngine together."""

    def __init__(
        self,
        service_name: str = "hermes-asi-harness",
        traces_path: str | Path | None = None,
        cost_report_path: str | Path | None = None,
        alerts_path: str | Path | None = None,
    ) -> None:
        self.traces_path = Path(traces_path) if traces_path else None
        self.cost_report_path = Path(cost_report_path) if cost_report_path else None
        self.alerts_path = Path(alerts_path) if alerts_path else None

        # Core components
        self.tracer_mgr = TracerProviderManager.get(service_name)
        self.cost_tracker = AgentCostTracker()
        self.alert_mgr = SafetyAlertManager()
        self.replay = TraceReplayEngine(self.tracer_mgr)

        # Wire safety alerts to tracer spans
        self._alert_span_map: Dict[str, str] = {}

    def init(self, resource_attributes: dict | None = None) -> "advanced_observability":
        self.tracer_mgr.configure(
            structured_export_path=self.traces_path,
            resource_attributes=resource_attributes,
        )
        return self

    @property
    def tracer(self) -> trace.Tracer:
        return self.tracer_mgr.tracer

    # --- cost ---

    def track_cost(
        self,
        agent_id: str,
        run_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        metadata: dict | None = None,
    ) -> AgentCostRecord:
        return self.cost_tracker.record(agent_id, run_id, model, input_tokens, output_tokens, latency_ms, metadata)

    # --- safety ---

    def safety_violation(self, vtype: str, detail: str, agent_id: str | None = None, trace_id: str | None = None) -> SafetyAlert:
        return self.alert_mgr.safety_violation(vtype, detail, agent_id, trace_id)

    def injection_attempt(self, payload: str, agent_id: str | None = None, trace_id: str | None = None) -> SafetyAlert:
        return self.alert_mgr.injection_attempt(payload, agent_id, trace_id)

    def self_replicate_guard(self, detail: str, agent_id: str | None = None, trace_id: str | None = None) -> SafetyAlert:
        return self.alert_mgr.self_replicate_guard(detail, agent_id, trace_id)

    # --- replay ---

    def replay_events(
        self,
        spans: List[ReadableSpan] | None = None,
        agent_id: str | None = None,
        span_name: str | None = None,
    ) -> List[ReplayEvent]:
        return self.replay.replay(spans, agent_id=agent_id, span_name=span_name)

    def reconstruct_runs(self, spans: List[ReadableSpan] | None = None) -> Dict[str, List[dict]]:
        return self.replay.reconstruct_runs(spans)

    # --- export ---

    def export_cost_report(self, path: str | Path | None = None) -> dict:
        p = Path(path) if path else self.cost_report_path
        return self.cost_tracker.export_json(p)

    def export_alerts(self, path: str | Path | None = None) -> dict:
        p = Path(path) if path else self.alerts_path
        return self.alert_mgr.export_json(p)

    def export_traces_json(self, path: str | Path) -> List[dict]:
        """Export current in-memory spans as a JSON array."""
        spans = self.tracer_mgr.get_spans()
        records = [StructuredSpanExporter._span_to_dict(s) for s in spans]
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(records, indent=2, default=str))
        return records

    def shutdown(self) -> None:
        self.tracer_mgr.shutdown()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_advanced_observability: advanced_observability | None = None
_observability_lock = threading.Lock()


def get_advanced_observability(
    service_name: str = "hermes-asi-harness",
    traces_path: str | Path | None = None,
    cost_report_path: str | Path | None = None,
    alerts_path: str | Path | None = None,
) -> advanced_observability:
    """Get or create the global advanced observability instance."""
    global _advanced_observability
    if _advanced_observability is None or _advanced_observability._tracer_mgr.provider is None:
        with _observability_lock:
            if _advanced_observability is None or _advanced_observability._tracer_mgr.provider is None:
                _advanced_observability = advanced_observability(
                    service_name=service_name,
                    traces_path=traces_path,
                    cost_report_path=cost_report_path,
                    alerts_path=alerts_path,
                )
                _advanced_observability.init()
    return _advanced_observability
