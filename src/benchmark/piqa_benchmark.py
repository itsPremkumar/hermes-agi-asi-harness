"""PIQA Benchmark — Physical Interaction Question Answering."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ProblemStatus(Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


@dataclass
class PIQAProblem:
    """A PIQA problem."""
    id: str
    question: str
    options: list[str]
    correct_index: int
    metadata: dict[str, Any] = field(default_factory=dict)
    status: ProblemStatus = ProblemStatus.PENDING


@dataclass
class PIQAResult:
    """Result of running a PIQA problem."""
    problem_id: str
    status: ProblemStatus
    predicted_index: int = -1
    correct: bool = False
    duration_ms: float = 0.0


class PIQABenchmark:
    """PIQA benchmark runner."""

    def __init__(self):
        self._lock = threading.RLock()
        self._problems: dict[str, PIQAProblem] = {}
        self._results: dict[str, PIQAResult] = {}
        self._predictions: dict[str, int] = {}

    def load_problems(self) -> int:
        """Load built-in PIQA problems."""
        for i in range(1, 1001):
            problem = PIQAProblem(
                id=f"PIQA_{i}",
                question=self._get_question(i),
                options=self._get_options(i),
                correct_index=i % 2,
                metadata={"difficulty": self._get_difficulty(i)},
            )
            self._problems[problem.id] = problem
        return 1000

    def _get_question(self, i: int) -> str:
        questions = {
            1: "What is the best way to open a jar?",
            2: "How do you tie a shoelace?",
            3: "What happens when you mix oil and water?",
        }
        if i in questions:
            return questions[i]
        return f"Physical interaction question {i}"

    def _get_options(self, i: int) -> list[str]:
        return ["Option A: Use a grip", "Option B: Use a tool"]

    def _get_difficulty(self, i: int) -> str:
        if i <= 300:
            return "easy"
        elif i <= 700:
            return "medium"
        return "hard"

    def set_prediction(self, problem_id: str, predicted_index: int) -> None:
        with self._lock:
            self._predictions[problem_id] = predicted_index

    def run_problem(self, problem_id: str, predicted_index: int | None = None) -> PIQAResult:
        start = time.time()
        problem = self._problems.get(problem_id)
        if not problem:
            return PIQAResult(problem_id=problem_id, status=ProblemStatus.ERROR, duration_ms=(time.time() - start) * 1000)
        pred = predicted_index if predicted_index is not None else self._predictions.get(problem_id, -1)
        correct = pred == problem.correct_index
        duration = (time.time() - start) * 1000
        result = PIQAResult(problem_id=problem_id, status=ProblemStatus.PASSED if correct else ProblemStatus.FAILED, predicted_index=pred, correct=correct, duration_ms=duration)
        self._results[problem_id] = result
        return result

    def run_all(self) -> list[PIQAResult]:
        return [self.run_problem(pid) for pid in self._problems]

    def get_pass_rate(self) -> dict[str, Any]:
        with self._lock:
            if not self._results:
                return {"total": 0, "passed": 0, "failed": 0, "pass_rate": 0.0}
            passed = sum(1 for r in self._results.values() if r.status == ProblemStatus.PASSED)
            total = len(self._results)
            return {"total": total, "passed": passed, "failed": total - passed, "pass_rate": passed / total if total else 0.0}

    def get_problem(self, problem_id: str) -> Optional[PIQAProblem]:
        return self._problems.get(problem_id)

    def list_problems(self) -> list[str]:
        return list(self._problems.keys())

    def get_result(self, problem_id: str) -> Optional[PIQAResult]:
        return self._results.get(problem_id)

    def count(self) -> int:
        return len(self._problems)

    def clear_results(self) -> None:
        with self._lock:
            self._results.clear()


__all__ = ["PIQABenchmark", "PIQAProblem", "PIQAResult", "ProblemStatus"]
