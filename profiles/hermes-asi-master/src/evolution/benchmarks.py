"""benchmarks.py — Capability benchmarks with baseline tracking.

A benchmark is a collection of tasks that an agent runs. Each task produces
a result (success/failure, score, latency, cost). The benchmark aggregates
these into a report and tracks baselines over time.

Module API:
- TaskResult: outcome of a single task
- BenchmarkResult: aggregated report
- Benchmark: runs a suite of tasks against a runner
- TaskSuite: a reusable collection of tasks
- BaselineTracker: tracks benchmark results over time with regression detection
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
# Baseline Tracker
# ---------------------------------------------------------------------------


@dataclass
class BaselineEntry:
    """A single baseline measurement."""

    suite_id: str
    avg_score: float
    avg_latency: float
    total_cost: float
    success_rate: float
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BaselineEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class BaselineTracker:
    """Track benchmark baselines over time with regression detection.

    Usage:
        tracker = BaselineTracker()
        tracker.record(result)
        report = tracker.check_regression(result, score_threshold=0.05)
    """

    def __init__(self) -> None:
        self.baselines: dict[str, BaselineEntry] = {}
        self.history: dict[str, list[BaselineEntry]] = {}

    def record(self, result: BenchmarkResult) -> None:
        """Record a benchmark result as the new baseline."""
        entry = BaselineEntry(
            suite_id=result.suite_id,
            avg_score=result.avg_score,
            avg_latency=result.avg_latency,
            total_cost=result.total_cost,
            success_rate=result.success_rate,
        )
        self.baselines[result.suite_id] = entry
        if result.suite_id not in self.history:
            self.history[result.suite_id] = []
        self.history[result.suite_id].append(entry)

    def get_baseline(self, suite_id: str) -> BaselineEntry | None:
        """Get the current baseline for a suite."""
        return self.baselines.get(suite_id)

    def check_regression(
        self,
        result: BenchmarkResult,
        score_threshold: float = 0.05,
        latency_threshold: float = 0.2,
        cost_threshold: float = 0.3,
    ) -> dict[str, Any]:
        """Check if a result regresses from baseline.

        Returns a report with regression flags and deltas.
        """
        baseline = self.baselines.get(result.suite_id)
        if baseline is None:
            return {"suite_id": result.suite_id, "has_baseline": False, "regressed": False}

        score_delta = result.avg_score - baseline.avg_score
        latency_delta = result.avg_latency - baseline.avg_latency
        cost_delta = result.total_cost - baseline.total_cost

        score_regressed = score_delta < -score_threshold
        latency_regressed = latency_delta > latency_threshold * baseline.avg_latency if baseline.avg_latency > 0 else False
        cost_regressed = cost_delta > cost_threshold * baseline.total_cost if baseline.total_cost > 0 else False

        return {
            "suite_id": result.suite_id,
            "has_baseline": True,
            "regressed": score_regressed or latency_regressed or cost_regressed,
            "score_regressed": score_regressed,
            "latency_regressed": latency_regressed,
            "cost_regressed": cost_regressed,
            "score_delta": score_delta,
            "latency_delta": latency_delta,
            "cost_delta": cost_delta,
            "baseline_score": baseline.avg_score,
            "current_score": result.avg_score,
        }

    def trend(self, suite_id: str, window: int = 5) -> dict[str, Any]:
        """Compute trend over recent history."""
        entries = self.history.get(suite_id, [])
        if not entries:
            return {"suite_id": suite_id, "samples": 0}

        recent = entries[-window:]
        scores = [e.avg_score for e in recent]
        latencies = [e.avg_latency for e in recent]

        return {
            "suite_id": suite_id,
            "samples": len(recent),
            "score_trend": scores[-1] - scores[0] if len(scores) >= 1 else 0.0,
            "latency_trend": latencies[-1] - latencies[0] if len(latencies) >= 1 else 0.0,
            "best_score": max(scores),
            "worst_score": min(scores),
            "avg_score": statistics.mean(scores),
        }

    def summary(self) -> dict[str, Any]:
        """Summary of all tracked baselines."""
        return {
            "suites": list(self.baselines.keys()),
            "count": len(self.baselines),
            "baselines": {sid: b.to_dict() for sid, b in self.baselines.items()},
        }

    def __len__(self) -> int:
        return len(self.baselines)

    def __contains__(self, suite_id: str) -> bool:
        return suite_id in self.baselines


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
