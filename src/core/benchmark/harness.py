"""Lightweight benchmark harness — run named callables, score, summarize.

Used by :meth:`core.continuous.EvolutionEngine.run_once` to honestly
benchmark each evolution round. Stdlib only: a task is any mapping (or
object) with a ``name`` and a zero-argument ``fn`` callable. Exceptions
raised by ``fn`` are recorded as failures, never propagated.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable


class ScoringFunction:
    """Default pass/fail scorer: truthy return values score ``1.0``."""

    def __call__(self, value: Any) -> float:
        return 1.0 if value else 0.0


@dataclass
class TaskScore:
    """Per-task outcome across ``n_runs`` repetitions."""

    name: str
    passed: bool
    score: float
    runs: int = 1
    duration_ms: float = 0.0
    error: str = ""


class BenchmarkRunner:
    """Run ``tasks`` with ``scoring_fn`` and summarize honestly."""

    def __init__(self, scoring_fn: Callable[[Any], float] | None = None) -> None:
        self._scoring_fn = scoring_fn or ScoringFunction()
        self._scores: list[TaskScore] = []

    @property
    def scores(self) -> list[TaskScore]:
        return list(self._scores)

    def run(
        self, tasks: list[dict[str, Any]], n_runs: int = 1
    ) -> list[TaskScore]:
        """Execute each task ``n_runs`` times; exceptions become failures."""
        n_runs = max(1, int(n_runs))
        self._scores = []
        for task in tasks:
            if isinstance(task, dict):
                name = str(task.get("name", "task"))
                fn = task.get("fn")
            else:  # tolerate objects exposing .name / .fn
                name = str(getattr(task, "name", "task"))
                fn = getattr(task, "fn", None)
            run_scores: list[float] = []
            all_passed = True
            error = ""
            duration_ms = 0.0
            for _ in range(n_runs):
                start = time.perf_counter()
                try:
                    value = fn() if callable(fn) else None
                    if not callable(fn):
                        raise TypeError(f"task {name!r} has no callable 'fn'")
                    run_scores.append(float(self._scoring_fn(value)))
                except Exception as exc:  # noqa: BLE001 - recorded, not raised
                    all_passed = False
                    run_scores.append(0.0)
                    error = f"{type(exc).__name__}: {exc}"
                finally:
                    duration_ms += (time.perf_counter() - start) * 1000.0
            mean_score = sum(run_scores) / len(run_scores)
            self._scores.append(
                TaskScore(
                    name=name,
                    passed=all_passed and mean_score >= 1.0,
                    score=mean_score,
                    runs=n_runs,
                    duration_ms=duration_ms,
                    error=error,
                )
            )
        return self.scores

    def summary(self) -> dict[str, Any]:
        """Aggregate the last :meth:`run` (keys consumed by core.continuous)."""
        total = len(self._scores)
        passed = sum(1 for s in self._scores if s.passed)
        mean_score = sum(s.score for s in self._scores) / total if total else 0.0
        return {
            "total_tasks": total,
            "passed_tasks": passed,
            "failed_tasks": total - passed,
            "pass_rate": (passed / total) if total else 0.0,
            "mean_score": mean_score,
            "measured": total > 0,
            "total_duration_ms": sum(s.duration_ms for s in self._scores),
        }
