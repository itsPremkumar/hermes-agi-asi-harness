"""
HERMES INTELLIGENCE OS — LANGSMITH TELEMETRY & OBSERVABILITY EXPORTER
=====================================================================
Pluggable, non-blocking telemetry bridge connecting Hermes Intelligence OS
and the Dual-Substrate Execution Engine (LangGraph + Deep Agents) to LangSmith:
- Root-level Mission traces with nested execution wave and subagent worker spans.
- Native LangGraph dynamic StateGraph tracing & checkpoint tracking.
- Automatic SecretScrubber privacy redaction to prevent data & credential leakage.
- 100% offline air-gap fallback when unconfigured or disconnected.
"""

from __future__ import annotations

import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes.os.langsmith")

# Optional import of official langsmith library
try:
    import langsmith
    from langsmith import Client as LangSmithClient
    from langsmith.run_trees import RunTree
    _LANGSMITH_AVAILABLE = True
except ImportError:
    _LANGSMITH_AVAILABLE = False
    LangSmithClient = None  # type: ignore
    RunTree = None          # type: ignore


@dataclass
class LangSmithConfig:
    """Runtime configuration for LangSmith telemetry export."""
    enabled: bool = False
    api_key: Optional[str] = None
    project_name: str = "hermes-asi-master"
    endpoint: str = "https://api.smith.langchain.com"
    scrub_secrets: bool = True
    local_fallback: bool = True

    @classmethod
    def from_env(cls) -> LangSmithConfig:
        api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
        tracing_v2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() in ("true", "1", "yes")
        enabled = bool(api_key or tracing_v2)
        project = os.getenv("LANGCHAIN_PROJECT") or "hermes-asi-master"
        endpoint = os.getenv("LANGSMITH_ENDPOINT") or "https://api.smith.langchain.com"
        return cls(
            enabled=enabled,
            api_key=api_key,
            project_name=project,
            endpoint=endpoint,
            scrub_secrets=True,
            local_fallback=True,
        )


@dataclass
class LocalTraceSpan:
    """Zero-dependency local trace span for offline air-gap execution."""
    name: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    run_type: str = "chain"
    parent_id: Optional[str] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    status: str = "running"
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    children: List[LocalTraceSpan] = field(default_factory=list)

    def end(self, outputs: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
        self.end_time = time.time()
        self.status = "failed" if error else "completed"
        if outputs:
            self.outputs = outputs
        if error:
            self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "run_id": self.run_id,
            "run_type": self.run_type,
            "status": self.status,
            "parent_id": self.parent_id,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "error": self.error,
            "metadata": self.metadata,
            "duration": round(self.end_time - self.start_time, 3) if self.end_time else None,
            "children": [c.to_dict() for c in self.children],
        }


class LangSmithTelemetryExporter:
    """
    Non-blocking telemetry exporter for LangSmith.
    Supports official LangSmith RunTree/Client when connected,
    with automatic secret redaction and 100% offline fallback.
    """

    SECRET_PATTERNS = [
        (re.compile(r"(sk-[a-zA-Z0-9]{20,})", re.IGNORECASE), "[REDACTED_OPENAI_KEY]"),
        (re.compile(r"(ghp_[a-zA-Z0-9]{20,})", re.IGNORECASE), "[REDACTED_GITHUB_TOKEN]"),
        (re.compile(r"(ls__[a-zA-Z0-9]{20,})", re.IGNORECASE), "[REDACTED_LANGSMITH_KEY]"),
        (re.compile(r"(Bearer\s+[a-zA-Z0-9_\-\.]{20,})", re.IGNORECASE), "Bearer [REDACTED_BEARER_TOKEN]"),
        (re.compile(r"(password\s*[:=]\s*['\"][^'\"]+['\"])", re.IGNORECASE), "password='[REDACTED_PASSWORD]'"),
    ]

    def __init__(
        self,
        config: Optional[LangSmithConfig] = None,
        event_bus: Optional[Any] = None,
    ) -> None:
        self.config = config or LangSmithConfig.from_env()
        self.event_bus = event_bus

        # Live trace registries
        self._active_mission_runs: Dict[str, Any] = {}
        self._active_wave_spans: Dict[str, Any] = {}
        self._active_worker_spans: Dict[str, Any] = {}
        self._completed_traces: List[Dict[str, Any]] = []

        # Client initialization
        self._client: Optional[Any] = None
        if self.config.enabled and _LANGSMITH_AVAILABLE and self.config.api_key:
            try:
                self._client = LangSmithClient(
                    api_key=self.config.api_key,
                    api_url=self.config.endpoint,
                )
                logger.info(f"[LangSmith] Connected client to project '{self.config.project_name}'")
            except Exception as e:
                logger.warning(f"[LangSmith] Client initialization failed: {e}. Using local fallback.")

        # Auto-subscribe to EventBus if provided
        if self.event_bus is not None:
            self._attach_event_subscribers()

    @property
    def is_cloud_connected(self) -> bool:
        return self._client is not None

    def _scrub_payload(self, data: Any) -> Any:
        """Deep scrubbing of credentials and sensitive tokens from telemetry payloads."""
        if not self.config.scrub_secrets:
            return data

        if isinstance(data, str):
            res = data
            for pat, repl in self.SECRET_PATTERNS:
                res = pat.sub(repl, res)
            return res
        elif isinstance(data, dict):
            return {k: self._scrub_payload(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._scrub_payload(x) for x in data]
        return data

    def start_mission_trace(
        self,
        mission_id: str,
        request: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Initialize the root trace for an end-to-end Hermes mission."""
        scrubbed_input = self._scrub_payload({"request": request})
        meta = self._scrub_payload(metadata or {})
        meta["hermes_version"] = "v9"
        meta["architecture"] = "dual_substrate"

        if self.config.enabled and _LANGSMITH_AVAILABLE and RunTree is not None:
            try:
                run = RunTree(
                    name=f"Hermes Mission: {request[:50]}",
                    run_type="chain",
                    inputs=scrubbed_input,
                    project_name=self.config.project_name,
                    extra=meta,
                )
                self._active_mission_runs[mission_id] = run
                logger.debug(f"[LangSmith] Started cloud mission run {run.id} for {mission_id}")
                return run
            except Exception as e:
                logger.warning(f"[LangSmith] Failed creating RunTree: {e}. Falling back to local span.")

        # Local fallback span
        span = LocalTraceSpan(
            name=f"Hermes Mission: {request[:50]}",
            run_type="chain",
            inputs=scrubbed_input,
            metadata=meta,
        )
        self._active_mission_runs[mission_id] = span
        return span

    def end_mission_trace(
        self,
        mission_id: str,
        status: str,
        proof: Optional[Dict[str, Any]] = None,
        artifacts: Optional[List[str]] = None,
        error: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Finalize the root mission trace with proof and output artifacts."""
        run = self._active_mission_runs.pop(mission_id, None)
        if not run:
            return None

        scrubbed_outputs = self._scrub_payload({
            "status": status,
            "proof": proof or {},
            "artifacts": artifacts or [],
        })

        if isinstance(run, LocalTraceSpan):
            run.end(outputs=scrubbed_outputs, error=error)
            run.status = status
            run_dict = run.to_dict()
            run_dict["status"] = status
            self._completed_traces.append(run_dict)
            return run_dict

        # Official RunTree
        try:
            run.end(outputs=scrubbed_outputs, error=error)
            if self.config.api_key:
                run.post()
            run_summary = {
                "run_id": str(run.id),
                "name": run.name,
                "status": status,
                "outputs": scrubbed_outputs,
            }
            self._completed_traces.append(run_summary)
            return run_summary
        except Exception as e:
            logger.warning(f"[LangSmith] Failed posting RunTree to cloud: {e}")
            return {"run_id": str(getattr(run, "id", "")), "status": status, "error": str(e)}

    def start_wave_span(
        self,
        mission_id: str,
        wave_number: int,
        task_ids: List[str],
    ) -> Any:
        """Create a child span representing a LangGraph execution wave."""
        parent = self._active_mission_runs.get(mission_id)
        span_name = f"Wave {wave_number}: [{', '.join(task_ids)}]"
        inputs = self._scrub_payload({"wave": wave_number, "tasks": task_ids})
        key = f"{mission_id}:wave:{wave_number}"

        if parent and hasattr(parent, "create_child"):
            try:
                child = parent.create_child(
                    name=span_name,
                    run_type="chain",
                    inputs=inputs,
                )
                self._active_wave_spans[key] = child
                return child
            except Exception as e:
                logger.warning(f"[LangSmith] Error creating wave child span: {e}")

        # Local span child
        child_span = LocalTraceSpan(
            name=span_name,
            run_type="chain",
            parent_id=getattr(parent, "run_id", None) if parent else None,
            inputs=inputs,
        )
        if isinstance(parent, LocalTraceSpan):
            parent.children.append(child_span)
        self._active_wave_spans[key] = child_span
        return child_span

    def end_wave_span(
        self,
        mission_id: str,
        wave_number: int,
        completed_tasks: List[str],
        checkpoint_id: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """End an execution wave span."""
        key = f"{mission_id}:wave:{wave_number}"
        span = self._active_wave_spans.pop(key, None)
        if not span:
            return

        outputs = self._scrub_payload({
            "completed_tasks": completed_tasks,
            "checkpoint": checkpoint_id,
        })

        if isinstance(span, LocalTraceSpan):
            span.end(outputs=outputs, error=error)
        elif hasattr(span, "end"):
            try:
                span.end(outputs=outputs, error=error)
                if self.config.api_key:
                    span.post()
            except Exception as e:
                logger.debug(f"[LangSmith] Non-critical error ending wave span: {e}")

    def start_worker_span(
        self,
        mission_id: str,
        worker_id: str,
        task_id: str,
        role: str = "worker",
        sandbox_dir: str = "",
    ) -> Any:
        """Create a child span representing an isolated Deep Agent worker task."""
        parent = self._active_mission_runs.get(mission_id)
        span_name = f"Subagent [{role}]: {task_id}"
        inputs = self._scrub_payload({"worker_id": worker_id, "task_id": task_id, "sandbox": sandbox_dir})
        key = f"{mission_id}:worker:{worker_id}"

        if parent and hasattr(parent, "create_child"):
            try:
                child = parent.create_child(
                    name=span_name,
                    run_type="tool",
                    inputs=inputs,
                )
                self._active_worker_spans[key] = child
                return child
            except Exception as e:
                logger.warning(f"[LangSmith] Error creating worker child span: {e}")

        child_span = LocalTraceSpan(
            name=span_name,
            run_type="tool",
            parent_id=getattr(parent, "run_id", None) if parent else None,
            inputs=inputs,
        )
        if isinstance(parent, LocalTraceSpan):
            parent.children.append(child_span)
        self._active_worker_spans[key] = child_span
        return child_span

    def end_worker_span(
        self,
        mission_id: str,
        worker_id: str,
        artifacts: Optional[List[str]] = None,
        error: Optional[str] = None,
    ) -> None:
        """End a subagent worker span."""
        key = f"{mission_id}:worker:{worker_id}"
        span = self._active_worker_spans.pop(key, None)
        if not span:
            return

        outputs = self._scrub_payload({"artifacts": artifacts or []})

        if isinstance(span, LocalTraceSpan):
            span.end(outputs=outputs, error=error)
        elif hasattr(span, "end"):
            try:
                span.end(outputs=outputs, error=error)
                if self.config.api_key:
                    span.post()
            except Exception as e:
                logger.debug(f"[LangSmith] Non-critical error ending worker span: {e}")

    def record_feedback(
        self,
        run_id: str,
        key: str,
        score: float,
        comment: str = "",
    ) -> bool:
        """Log verification or human-in-the-loop evaluation score for a run."""
        if self._client is not None:
            try:
                self._client.create_feedback(
                    run_id=run_id,
                    key=key,
                    score=score,
                    comment=self._scrub_payload(comment),
                )
                return True
            except Exception as e:
                logger.warning(f"[LangSmith] Failed creating cloud feedback: {e}")

        logger.debug(f"[LangSmith Local] Feedback recorded: run={run_id} key={key} score={score}")
        return True

    def _attach_event_subscribers(self) -> None:
        """Wire telemetry exporter into Hermes Universal Event Bus."""
        def _on_mission_started(event: Any) -> None:
            payload = getattr(event, "payload", {})
            mid = payload.get("mission_id") or getattr(event, "correlation_id", "") or "mission"
            req = payload.get("request") or "Autonomous Mission"
            self.start_mission_trace(mid, req, metadata={"source": str(getattr(event, "source", ""))})

        def _on_mission_completed(event: Any) -> None:
            payload = getattr(event, "payload", {})
            mid = payload.get("mission_id") or "mission"
            status = payload.get("status", "completed")
            self.end_mission_trace(mid, status=status)

        self.event_bus.subscribe("mission.started", _on_mission_started)
        self.event_bus.subscribe("mission.completed", _on_mission_completed)

    def get_completed_traces(self) -> List[Dict[str, Any]]:
        return list(self._completed_traces)

    def clear(self) -> None:
        self._active_mission_runs.clear()
        self._active_wave_spans.clear()
        self._active_worker_spans.clear()
        self._completed_traces.clear()
