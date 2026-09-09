"""LangSmith integration for tracing and evaluation."""
from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from contextlib import contextmanager


@dataclass
class LangSmithRun:
    """Represents a LangSmith run."""
    run_id: str
    name: str
    run_type: str
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    start_time: str = ""
    end_time: str = ""
    status: str = "pending"
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    parent_run_id: str | None = None
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.run_id,
            "name": self.name,
            "run_type": self.run_type,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status,
            "error": self.error,
            "metadata": self.metadata,
            "parent_run_id": self.parent_run_id,
            "tags": self.tags,
        }


class LangSmithClient:
    """Client for LangSmith tracing and evaluation."""

    def __init__(
        self,
        api_key: str | None = None,
        project_name: str = "default",
        endpoint: str = "https://api.smith.langchain.com",
    ) -> None:
        self.api_key = api_key or os.environ.get("LANGSMITH_API_KEY", "")
        self.project_name = project_name
        self.endpoint = endpoint
        self._runs: dict[str, LangSmithRun] = {}
        self._active: bool = bool(self.api_key)

    @property
    def is_active(self) -> bool:
        """Whether the client is properly configured."""
        return self._active

    def create_run(
        self,
        name: str,
        run_type: str = "chain",
        inputs: dict[str, Any] | None = None,
        parent_run_id: str | None = None,
        tags: list[str] | None = None,
        **metadata: Any,
    ) -> LangSmithRun:
        """Create a new run."""
        run = LangSmithRun(
            run_id=str(uuid.uuid4()),
            name=name,
            run_type=run_type,
            inputs=inputs or {},
            start_time=datetime.now(timezone.utc).isoformat(),
            status="running",
            parent_run_id=parent_run_id,
            tags=tags or [],
            metadata=metadata,
        )
        self._runs[run.run_id] = run
        return run

    def end_run(
        self,
        run: LangSmithRun,
        outputs: dict[str, Any] | None = None,
        error: str | None = None,
        status: str = "success",
    ) -> None:
        """End a run with outputs."""
        run.end_time = datetime.now(timezone.utc).isoformat()
        run.outputs = outputs or {}
        run.error = error
        run.status = status if not error else "error"

    def get_run(self, run_id: str) -> LangSmithRun | None:
        """Get a run by ID."""
        return self._runs.get(run_id)

    def get_runs(self, run_type: str | None = None) -> list[LangSmithRun]:
        """Get all runs, optionally filtered by type."""
        runs = list(self._runs.values())
        if run_type:
            runs = [r for r in runs if r.run_type == run_type]
        return runs

    @contextmanager
    def trace(
        self,
        name: str,
        run_type: str = "chain",
        inputs: dict[str, Any] | None = None,
        parent_run_id: str | None = None,
        tags: list[str] | None = None,
        **metadata: Any,
    ):
        """Context manager for tracing a run."""
        run = self.create_run(
            name=name,
            run_type=run_type,
            inputs=inputs,
            parent_run_id=parent_run_id,
            tags=tags,
            **metadata,
        )
        try:
            yield run
            self.end_run(run, status="success")
        except Exception as e:
            self.end_run(run, error=str(e), status="error")
            raise

    def evaluate(
        self,
        run_id: str,
        evaluator_name: str,
        score: float,
        feedback: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record an evaluation for a run."""
        return {
            "run_id": run_id,
            "evaluator": evaluator_name,
            "score": score,
            "feedback": feedback,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_project_stats(self) -> dict[str, Any]:
        """Get statistics for the project."""
        runs = list(self._runs.values())
        total = len(runs)
        successful = sum(1 for r in runs if r.status == "success")
        failed = sum(1 for r in runs if r.status == "error")
        pending = sum(1 for r in runs if r.status == "pending")
        running = sum(1 for r in runs if r.status == "running")

        durations = []
        for r in runs:
            if r.start_time and r.end_time:
                try:
                    start = datetime.fromisoformat(r.start_time)
                    end = datetime.fromisoformat(r.end_time)
                    durations.append((end - start).total_seconds())
                except (ValueError, TypeError):
                    pass

        return {
            "project": self.project_name,
            "total_runs": total,
            "successful": successful,
            "failed": failed,
            "pending": pending,
            "running": running,
            "avg_duration": sum(durations) / len(durations) if durations else 0,
            "success_rate": successful / total if total else 0,
        }


class LangSmithTracer:
    """High-level tracer that integrates with LangSmith."""

    def __init__(self, client: LangSmithClient | None = None) -> None:
        self.client = client or LangSmithClient()
        self._spans: dict[str, LangSmithRun] = {}

    def start_span(
        self,
        name: str,
        inputs: dict[str, Any] | None = None,
        parent_span_id: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Start a new span and return its ID."""
        parent_run_id = self._spans[parent_span_id]["run_id"] if parent_span_id and parent_span_id in self._spans else None
        run = self.client.create_run(
            name=name,
            run_type="span",
            inputs=inputs,
            parent_run_id=parent_run_id,
            tags=tags,
        )
        self._spans[run.run_id] = {"run": run, "parent_id": parent_span_id}
        return run.run_id

    def end_span(
        self,
        span_id: str,
        outputs: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """End a span."""
        if span_id not in self._spans:
            return
        span_data = self._spans.pop(span_id)
        self.client.end_run(span_data["run"], outputs=outputs, error=error)

    @contextmanager
    def span(
        self,
        name: str,
        inputs: dict[str, Any] | None = None,
        parent_span_id: str | None = None,
        tags: list[str] | None = None,
    ):
        """Context manager for a span."""
        span_id = self.start_span(name, inputs, parent_span_id, tags)
        try:
            yield span_id
            self.end_span(span_id)
        except Exception as e:
            self.end_span(span_id, error=str(e))
            raise
