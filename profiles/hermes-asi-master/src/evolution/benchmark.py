"""benchmark.py — Run task suites, measure score/latency/cost/failure rate.

A benchmark is a collection of tasks that an agent runs. Each task produces
a result (success/failure, score, latency, cost). The benchmark aggregates
these into a report.

Module API:
- TaskResult: outcome of a single task
- BenchmarkResult: aggregated report
- Benchmark: runs a suite of tasks against a runner
- TaskSuite: a reusable collection of tasks
"""

from __future__ import annotations

import dataclasses
import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclass
class TaskResult:
    """Outcome of a single benchmark task."""

    task_id: str
    success: bool
    score: float = 0.0  # 0.0 .. 1.0
    latency: float = 0.0  # seconds
    cost: float = 0.0  # arbitrary cost units
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskResult":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class BenchmarkResult:
    """Aggregated benchmark report."""

    suite_id: str
    task_results: list[TaskResult] = field(default_factory=list)
    total_duration: float = 0.0
    timestamp: float = field(default_factory=time.time)

    @property
    def count(self) -> int:
        return len(self.task_results)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.task_results if r.success)

    @property
    def failure_count(self) -> int:
        return sum(1 for r in self.task_results if not r.success)

    @property
    def success_rate(self) -> float:
        if not self.task_results:
            return 0.0
        return self.success_count / self.count

    @property
    def failure_rate(self) -> float:
        if not self.task_results:
            return 0.0
        return self.failure_count / self.count

    @property
    def avg_score(self) -> float:
        if not self.task_results:
            return 0.0
        return statistics.mean(r.score for r in self.task_results)

    @property
    def avg_latency(self) -> float:
        if not self.task_results:
            return 0.0
        return statistics.mean(r.latency for r in self.task_results)

    @property
    def total_cost(self) -> float:
        return sum(r.cost for r in self.task_results)

    @property
    def avg_cost(self) -> float:
        if not self.task_results:
            return 0.0
        return self.total_cost / self.count

    @property
    def score_std(self) -> float:
        if len(self.task_results) < 2:
            return 0.0
        return statistics.stdev(r.score for r in self.task_results)

    @property
    def latency_p50(self) -> float:
        if not self.task_results:
            return 0.0
        return statistics.median(r.latency for r in self.task_results)

    @property
    def latency_p95(self) -> float:
        if not self.task_results:
            return 0.0
        sorted_latencies = sorted(r.latency for r in self.task_results)
        idx = int(len(sorted_latencies) * 0.95)
        idx = min(idx, len(sorted_latencies) - 1)
        return sorted_latencies[idx]

    def summary(self) -> dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "count": self.count,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "avg_score": self.avg_score,
            "avg_latency": self.avg_latency,
            "latency_p95": self.latency_p95,
            "total_cost": self.total_cost,
            "avg_cost": self.avg_cost,
            "score_std": self.score_std,
            "total_duration": self.total_duration,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "task_results": [r.to_dict() for r in self.task_results],
            "total_duration": self.total_duration,
            "timestamp": self.timestamp,
            "summary": self.summary(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BenchmarkResult":
        results = [TaskResult.from_dict(r) for r in data.pop("task_results", [])]
        summary = data.pop("summary", None)
        return cls(task_results=results, **{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Task Suite
# ---------------------------------------------------------------------------


@dataclass
class Task:
    """A single benchmark task."""

    id: str
    input: Any
    expected: Any = None
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


class TaskSuite:
    """A reusable collection of tasks.

    Usage:
        suite = TaskSuite("my_suite")
        suite.add(Task("t1", input="hello", expected="HELLO"))
        suite.add(Task("t2", input="world", expected="WORLD"))
    """

    def __init__(self, suite_id: str, tasks: Sequence[Task] | None = None) -> None:
        self.suite_id = suite_id
        self.tasks: list[Task] = list(tasks) if tasks else []

    def add(self, task: Task) -> None:
        self.tasks.append(task)

    def remove(self, task_id: str) -> bool:
        n = len(self.tasks)
        self.tasks = [t for t in self.tasks if t.id != task_id]
        return len(self.tasks) < n

    def get(self, task_id: str) -> Task | None:
        return next((t for t in self.tasks if t.id == task_id), None)

    def filter_by(self, predicate: Callable[[Task], bool]) -> list[Task]:
        return [t for t in self.tasks if predicate(t)]

    def __len__(self) -> int:
        return len(self.tasks)

    def __iter__(self):
        return iter(self.tasks)


# ---------------------------------------------------------------------------
# Benchmark Runner
# ---------------------------------------------------------------------------


class Benchmark:
    """Run a task suite against a runner and produce a report.

    The runner is a callable that takes (task_input) -> output.
    The scorer is a callable that takes (output, expected) -> (success, score).

    Usage:
        bench = Benchmark(suite)
        result = bench.run(runner=my_func, scorer=my_scorer)
    """

    def __init__(
        self,
        suite: TaskSuite,
        scorer: Callable[[Any, Any], tuple[bool, float]] | None = None,
    ) -> None:
        self.suite = suite
        self.scorer = scorer or self._default_scorer
        self.history: list[BenchmarkResult] = []

    def run(
        self,
        runner: Callable[[Any], Any],
        scorer: Callable[[Any, Any], tuple[bool, float]] | None = None,
        cost_fn: Callable[[Any, float], float] | None = None,
        max_tasks: int | None = None,
    ) -> BenchmarkResult:
        """Run the suite. Returns a BenchmarkResult."""
        scorer = scorer or self.scorer
        task_results: list[TaskResult] = []
        start = time.time()

        tasks = self.suite.tasks
        if max_tasks is not None:
            tasks = tasks[:max_tasks]

        for task in tasks:
            t0 = time.time()
            try:
                output = runner(task.input)
                success, score = scorer(output, task.expected)
                error = ""
            except Exception as exc:  # noqa: BLE001
                output = None
                success, score = False, 0.0
                error = str(exc)

            latency = time.time() - t0
            cost = cost_fn(output, latency) if cost_fn else 0.0

            task_results.append(
                TaskResult(
                    task_id=task.id,
                    success=success,
                    score=score,
                    latency=latency,
                    cost=cost,
                    error=error,
                    metadata=task.metadata,
                )
            )

        total_duration = time.time() - start
        result = BenchmarkResult(
            suite_id=self.suite.suite_id,
            task_results=task_results,
            total_duration=total_duration,
        )
        self.history.append(result)
        return result

    def compare(self, other: BenchmarkResult) -> dict[str, Any]:
        """Compare this benchmark's latest result with another."""
        if not self.history:
            return {"error": "no history"}
        mine = self.history[-1]
        return {
            "suite_id": mine.suite_id,
            "baseline_score": mine.avg_score,
            "candidate_score": other.avg_score,
            "score_delta": other.avg_score - mine.avg_score,
            "baseline_latency": mine.avg_latency,
            "candidate_latency": other.avg_latency,
            "latency_delta": other.avg_latency - mine.avg_latency,
            "baseline_cost": mine.total_cost,
            "candidate_cost": other.total_cost,
            "cost_delta": other.total_cost - mine.total_cost,
        }

    @staticmethod
    def _default_scorer(output: Any, expected: Any) -> tuple[bool, float]:
        """Default scorer: exact match = success, score 1.0."""
        if expected is None:
            return True, 1.0
        success = output == expected
        score = 1.0 if success else 0.0
        return success, score


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_suite_id(name: str) -> str:
    """Generate a stable suite id."""
    import hashlib

    h = hashlib.sha256(name.encode()).hexdigest()[:8]
    return f"suite-{h}"


def quick_suite(
    name: str,
    cases: list[tuple[Any, Any]],
    weights: list[float] | None = None,
) -> TaskSuite:
    """Build a TaskSuite from (input, expected) pairs."""
    suite = TaskSuite(name)
    for i, (inp, exp) in enumerate(cases):
        w = weights[i] if weights and i < len(weights) else 1.0
        suite.add(Task(id=f"t{i}", input=inp, expected=exp, weight=w))
    return suite
