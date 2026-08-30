"""ARC-AGI-3 Benchmark Runner — run and evaluate benchmarks."""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from typing import Any, Optional

from arc_agi_3.engine import (
    Engine, Grid, Task, Solution, Status,
    RuleHypothesizer, StrategySelector, SolutionGenerator, SolutionVerifier,
)


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    task_id: str
    solved: bool
    iterations: int
    score: float
    duration_ms: float = 0.0
    solution_id: str = ""
    error: str = ""


@dataclass
class BenchmarkSuite:
    """A suite of benchmark tasks."""
    id: str
    name: str
    tasks: list[Task] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BenchmarkRunner:
    """Run ARC-AGI-3 benchmarks and evaluate results."""

    def __init__(self, engine: Engine | None = None):
        self._lock = threading.RLock()
        self._engine = engine or Engine()
        self._suites: dict[str, BenchmarkSuite] = {}
        self._results: list[BenchmarkResult] = []

    @property
    def engine(self) -> Engine:
        return self._engine

    def register_suite(self, suite: BenchmarkSuite) -> str:
        with self._lock:
            self._suites[suite.id] = suite
            return suite.id

    def get_suite(self, suite_id: str) -> Optional[BenchmarkSuite]:
        return self._suites.get(suite_id)

    def list_suites(self) -> list[str]:
        return list(self._suites.keys())

    def run_task(self, task: Task, max_iterations: int | None = None) -> BenchmarkResult:
        """Run a single task benchmark."""
        start = time.time()

        if max_iterations:
            self._engine._max_iterations = max_iterations

        result = self._engine.solve(task)
        duration = (time.time() - start) * 1000

        bench_result = BenchmarkResult(
            task_id=task.id,
            solved=result.get("solved", False),
            iterations=result.get("iterations", 0),
            score=result.get("score", 0.0),
            duration_ms=duration,
            solution_id=result.get("solution_id", ""),
        )
        self._results.append(bench_result)
        return bench_result

    def run_suite(self, suite_id: str) -> list[BenchmarkResult]:
        """Run all tasks in a benchmark suite."""
        suite = self._suites.get(suite_id)
        if not suite:
            return []

        results = []
        for task in suite.tasks:
            result = self.run_task(task)
            results.append(result)
        return results

    def run_all(self) -> list[BenchmarkResult]:
        """Run all registered suites."""
        all_results = []
        for suite_id in self._suites:
            results = self.run_suite(suite_id)
            all_results.extend(results)
        return all_results

    def get_results(self) -> list[BenchmarkResult]:
        return list(self._results)

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            if not self._results:
                return {"total": 0, "solved": 0, "failed": 0, "avg_score": 0.0}

            solved = sum(1 for r in self._results if r.solved)
            total = len(self._results)
            avg_score = sum(r.score for r in self._results) / total if total else 0.0
            avg_iterations = sum(r.iterations for r in self._results) / total if total else 0.0
            avg_duration = sum(r.duration_ms for r in self._results) / total if total else 0.0

            return {
                "total": total,
                "solved": solved,
                "failed": total - solved,
                "solve_rate": solved / total if total else 0.0,
                "avg_score": avg_score,
                "avg_iterations": avg_iterations,
                "avg_duration_ms": avg_duration,
            }

    def clear_results(self) -> None:
        with self._lock:
            self._results.clear()


def build_default_benchmark_suite() -> BenchmarkSuite:
    """Build a default benchmark suite with sample tasks."""
    tasks = [
        Task(
            id="bench_1",
            input_grid=Grid([[1, 2], [3, 4]]),
            target_grid=Grid([[1, 2], [3, 4]]),
            examples=[(Grid([[1, 2], [3, 4]]), Grid([[1, 2], [3, 4]]))],
        ),
        Task(
            id="bench_2",
            input_grid=Grid([[0, 0], [0, 0]]),
            target_grid=Grid([[1, 1], [1, 1]]),
            examples=[(Grid([[0, 0], [0, 0]]), Grid([[1, 1], [1, 1]]))],
        ),
        Task(
            id="bench_3",
            input_grid=Grid([[1, 0], [0, 1]]),
            target_grid=Grid([[0, 1], [1, 0]]),
            examples=[(Grid([[1, 0], [0, 1]]), Grid([[0, 1], [1, 0]]))],
        ),
    ]

    return BenchmarkSuite(
        id="default",
        name="Default ARC-AGI-3 Benchmark",
        tasks=tasks,
        metadata={"version": "1.0", "description": "Default benchmark suite"},
    )


__all__ = [
    "BenchmarkRunner",
    "BenchmarkResult",
    "BenchmarkSuite",
    "build_default_benchmark_suite",
]
