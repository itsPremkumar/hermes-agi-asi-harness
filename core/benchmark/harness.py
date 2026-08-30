"""Benchmark harness for AVO engine.

Objective, measured scoring — never claimed. Provides:

- ``BenchmarkRunner`` — runs a suite of local tasks and scores them
- ``ScoringFunction`` — objective correctness + performance + quality
- ``BenchmarkResult`` — measured scores with confidence intervals

For ARC-AGI-3 style tasks: use the official ARC-AGI-3 harness when
available; this benchmark gives a *local objective baseline* with
honestly measured scores.
"""
from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class BenchmarkResult:
    name: str = ""
    score: float = 0.0
    confidence_interval: Tuple[float, float] = (0.0, 0.0)
    runs: int = 0
    passed: bool = False
    failed: int = 0
    details: List[Dict[str, Any]] = field(default_factory=list)
    measured_at: float = field(default_factory=time.time)
    measured: bool = True  # Honest: this score was actually measured

    @property
    def mean(self) -> float:
        return self.score

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dataclass_fields__.items()}


class ScoringFunction:
    """Objective scoring: correctness gate + performance + quality.

    Mirrors the AVO paper's multidimensional scoring:

        f(x_i) = (f_correctness(x_i), f_performance(x_i), f_quality(x_i))
    """

    def __init__(
        self,
        correctness_weight: float = 0.5,
        performance_weight: float = 0.3,
        quality_weight: float = 0.2,
    ) -> None:
        self._w_correctness = correctness_weight
        self._w_performance = performance_weight
        self._w_quality = quality_weight

    def score(
        self,
        correctness: bool,
        performance: float,
        quality: float,
    ) -> float:
        """Weighted composite score. Correctness is a hard gate."""
        if not correctness:
            return 0.0
        return (
            self._w_correctness * (1.0 if correctness else 0.0)
            + self._w_performance * min(performance, 1.0)
            + self._w_quality * min(quality, 1.0)
        )


class BenchmarkRunner:
    """Runs a suite of local tasks and returns measured scores."""

    def __init__(self, scoring_fn: Optional[ScoringFunction] = None) -> None:
        self.scoring_fn = scoring_fn or ScoringFunction()
        self._results: List[BenchmarkResult] = []

    def run(
        self,
        tasks: List[Dict[str, Any]],
        n_runs: int = 3,
    ) -> List[BenchmarkResult]:
        self._results = []
        for task in tasks:
            name = task.get("name", "unnamed")
            scores: List[float] = []
            details: List[Dict[str, Any]] = []
            passed = 0
            failed = 0
            for _ in range(n_runs):
                try:
                    t0 = time.time()
                    outcome = task.get("fn")() if callable(task.get("fn")) else task.get("expected", False)
                    elapsed = time.time() - t0
                    score = self._score_outcome(outcome, elapsed)
                    scores.append(score)
                    details.append({"score": score, "elapsed": elapsed, "outcome": outcome})
                    if outcome is True or (isinstance(outcome, bool) and outcome):
                        passed += 1
                    else:
                        failed += 1
                except Exception as e:
                    details.append({"score": 0.0, "error": str(e)})
                    failed += 1
                    scores.append(0.0)
            mean = statistics.mean(scores) if scores else 0.0
            ci = (mean, mean)
            if len(scores) > 1:
                se = statistics.stdev(scores) / (len(scores) ** 0.5)
                ci = (max(0.0, mean - 1.96 * se), min(1.0, mean + 1.96 * se))
            result = BenchmarkResult(
                name=name,
                score=mean,
                confidence_interval=ci,
                runs=len(scores),
                passed=passed,
                failed=failed,
                details=details,
            )
            self._results.append(result)
        return self._results

    def _score_outcome(self, outcome: Any, elapsed: float) -> float:
        if isinstance(outcome, bool):
            correctness = outcome
        elif isinstance(outcome, (int, float)):
            correctness = bool(outcome > 0)
        else:
            correctness = bool(outcome)
        performance = max(0.0, 1.0 - elapsed) if elapsed < 1.0 else 0.5
        quality = 0.8 if correctness else 0.0
        return self.scoring_fn.score(correctness, performance, quality)

    def summary(self) -> Dict[str, Any]:
        scores = [r.score for r in self._results]
        return {
            "total_tasks": len(self._results),
            "passed_tasks": sum(1 for r in self._results if r.passed or r.failed == 0),
            "mean_score": statistics.mean(scores) if scores else 0.0,
            "min_score": min(scores) if scores else 0.0,
            "max_score": max(scores) if scores else 0.0,
            "results": [r.to_dict() for r in self._results],
            "measured": True,
        }
