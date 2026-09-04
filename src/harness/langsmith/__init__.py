"""LangSmith Integration — tracing, eval runner, datasets, experiments."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..errors import LangSmithError

import os

logger = logging.getLogger(__name__)


@dataclass
class TraceSpan:
    """A trace span for LangSmith."""

    name: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    parent_id: str | None = None
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    children: list[TraceSpan] = field(default_factory=list)

    def end(self, outputs: dict[str, Any] | None = None, error: str | None = None) -> None:
        if outputs:
            self.outputs = outputs
        if error:
            self.error = error


class TracingClient:
    """LangSmith tracing client supporting both local in-memory traces and cloud client."""

    def __init__(self, project_name: str = "harness", enabled: bool = True, api_key: str | None = None) -> None:
        self.project_name = project_name
        self.enabled = enabled
        self.api_key = api_key or os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
        self._traces: list[TraceSpan] = []
        self._active_spans: dict[str, TraceSpan] = {}
        self._cloud_client: Any = None

        if self.enabled and self.api_key:
            try:
                import langsmith
                self._cloud_client = langsmith.Client(api_key=self.api_key)
            except Exception as e:
                logger.debug(f"LangSmith cloud client fallback to local: {e}")
                self._cloud_client = None

    @property
    def is_cloud_connected(self) -> bool:
        return self._cloud_client is not None

    def start_span(self, name: str, inputs: dict[str, Any] | None = None, parent_id: str | None = None) -> TraceSpan:
        span = TraceSpan(name=name, inputs=inputs or {}, parent_id=parent_id)
        self._active_spans[span.run_id] = span
        if parent_id and parent_id in self._active_spans:
            self._active_spans[parent_id].children.append(span)
        if not parent_id:
            self._traces.append(span)
        return span

    def end_span(self, run_id: str, outputs: dict[str, Any] | None = None, error: str | None = None) -> TraceSpan | None:
        span = self._active_spans.pop(run_id, None)
        if span:
            span.end(outputs, error)
            return span
        return None

    def get_traces(self) -> list[TraceSpan]:
        return list(self._traces)

    def clear(self) -> None:
        self._traces.clear()
        self._active_spans.clear()


@dataclass
class DatasetEntry:
    """A dataset entry for evaluation."""

    inputs: dict[str, Any]
    expected_output: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])


class Dataset:
    """LangSmith-style dataset."""

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self.entries: list[DatasetEntry] = []

    def add_entry(self, inputs: dict[str, Any], expected_output: str | None = None, **metadata: Any) -> DatasetEntry:
        entry = DatasetEntry(inputs=inputs, expected_output=expected_output, metadata=metadata)
        self.entries.append(entry)
        return entry

    @property
    def size(self) -> int:
        return len(self.entries)

    def to_langsmith(self, client: Any = None) -> Any:
        """Export dataset to LangSmith if client is available."""
        if client is not None:
            try:
                ds = client.create_dataset(dataset_name=self.name, description=self.description)
                for e in self.entries:
                    client.create_example(
                        inputs=e.inputs,
                        outputs={"expected": e.expected_output} if e.expected_output else None,
                        dataset_id=ds.id,
                        metadata=e.metadata,
                    )
                return ds
            except Exception as ex:
                logger.debug(f"LangSmith dataset export error: {ex}")
        return None


@dataclass
class EvalResult:
    """Result of a single evaluation."""

    entry_id: str
    predicted: str
    expected: str | None
    score: float
    feedback: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class EvalRunner:
    """LangSmith-style evaluation runner."""

    def __init__(self, tracing: TracingClient | None = None) -> None:
        self.tracing = tracing or TracingClient()

    def run_eval(
        self,
        dataset: Dataset,
        predict_fn: callable,
        scoring_fn: callable | None = None,
    ) -> list[EvalResult]:
        results = []
        for entry in dataset.entries:
            span = self.tracing.start_span("eval", inputs=entry.inputs)
            try:
                predicted = predict_fn(entry.inputs)
                score = scoring_fn(predicted, entry.expected_output, entry.inputs) if scoring_fn else 0.0
                result = EvalResult(
                    entry_id=entry.entry_id,
                    predicted=str(predicted),
                    expected=entry.expected_output,
                    score=score,
                )
                results.append(result)
                self.tracing.end_span(span.run_id, outputs={"score": score})
            except Exception as e:
                self.tracing.end_span(span.run_id, error=str(e))
                results.append(EvalResult(
                    entry_id=entry.entry_id,
                    predicted="",
                    expected=entry.expected_output,
                    score=0.0,
                    feedback=str(e),
                ))
        return results


@dataclass
class Experiment:
    """LangSmith-style experiment."""

    name: str
    description: str = ""
    experiment_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    results: list[EvalResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def avg_score(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.score for r in self.results) / len(self.results)


class ExperimentManager:
    """Manage experiments."""

    def __init__(self) -> None:
        self.experiments: dict[str, Experiment] = {}

    def create(self, name: str, description: str = "", **metadata: Any) -> Experiment:
        exp = Experiment(name=name, description=description, metadata=metadata)
        self.experiments[exp.experiment_id] = exp
        return exp

    def get(self, experiment_id: str) -> Experiment | None:
        return self.experiments.get(experiment_id)

    def list_experiments(self) -> list[Experiment]:
        return list(self.experiments.values())

    def compare(self, *experiment_ids: str) -> dict[str, float]:
        return {
            eid: self.experiments[eid].avg_score
            for eid in experiment_ids
            if eid in self.experiments
        }
