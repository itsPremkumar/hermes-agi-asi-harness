"""Winogender Benchmark Adapter — makes Winogender compatible with FullEvaluationSuite."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Any, Optional


class ProblemStatus(Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


@dataclass
class WinogenderProblem:
    id: str
    sentence: str
    pronoun: str
    options: list[str]
    correct_index: int
    metadata: dict[str, Any] = field(default_factory=dict)
    status: ProblemStatus = ProblemStatus.PENDING


@dataclass
class WinogenderResult:
    problem_id: str
    status: ProblemStatus
    predicted_index: int = -1
    correct: bool = False
    duration_ms: float = 0.0


class WinogenderBenchmark:
    """Winogender bias benchmark adapter."""

    def __init__(self):
        self._lock = threading.RLock()
        self._problems: dict[str, WinogenderProblem] = {}
        self._results: dict[str, WinogenderResult] = {}
        self._predictions: dict[str, int] = {}

    def load_problems(self) -> int:
        """Load built-in Winogender problems."""
        for i in range(1, 121):
            self._problems[f"WG_{i}"] = WinogenderProblem(
                id=f"WG_{i}",
                sentence=f"Sentence with pronoun {i}",
                pronoun="he" if i % 2 == 1 else "she",
                options=["Option A", "Option B"],
                correct_index=i % 2,
                metadata={"difficulty": "medium"},
            )
        return 120

    def set_prediction(self, problem_id: str, predicted_index: int) -> None:
        with self._lock:
            self._predictions[problem_id] = predicted_index

    def run_problem(self, problem_id: str, predicted_index: int | None = None) -> WinogenderResult:
        start = time.time()
        problem = self._problems.get(problem_id)
        if not problem:
            return WinogenderResult(problem_id=problem_id, status=ProblemStatus.ERROR, duration_ms=(time.time() - start) * 1000)
        pred = predicted_index if predicted_index is not None else self._predictions.get(problem_id, -1)
        correct = pred == problem.correct_index
        duration = (time.time() - start) * 1000
        result = WinogenderResult(problem_id=problem_id, status=ProblemStatus.PASSED if correct else ProblemStatus.FAILED, predicted_index=pred, correct=correct, duration_ms=duration)
        self._results[problem_id] = result
        return result

    def run_all(self) -> list[WinogenderResult]:
        return [self.run_problem(pid) for pid in self._problems]

    def get_pass_rate(self) -> dict[str, Any]:
        with self._lock:
            if not self._results:
                return {"total": 0, "passed": 0, "failed": 0, "pass_rate": 0.0}
            passed = sum(1 for r in self._results.values() if r.status == ProblemStatus.PASSED)
            total = len(self._results)
            return {"total": total, "passed": passed, "failed": total - passed, "pass_rate": passed / total if total else 0.0}

    def get_problem(self, problem_id: str) -> Optional[WinogenderProblem]:
        return self._problems.get(problem_id)

    def list_problems(self) -> list[str]:
        return list(self._problems.keys())

    def get_result(self, problem_id: str) -> Optional[WinogenderResult]:
        return self._results.get(problem_id)

    def count(self) -> int:
        return len(self._problems)

    def clear_results(self) -> None:
        with self._lock:
            self._results.clear()


__all__ = ["WinogenderBenchmark", "WinogenderProblem", "WinogenderResult", "ProblemStatus"]
