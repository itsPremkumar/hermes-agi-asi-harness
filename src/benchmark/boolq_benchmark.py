"""BoolQ Benchmark — boolean question answering."""

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
class BoolQProblem:
    """A BoolQ problem."""
    id: str
    question: str
    passage: str
    answer: bool
    metadata: dict[str, Any] = field(default_factory=dict)
    status: ProblemStatus = ProblemStatus.PENDING


@dataclass
class BoolQResult:
    """Result of running a BoolQ problem."""
    problem_id: str
    status: ProblemStatus
    predicted: bool = False
    correct: bool = False
    duration_ms: float = 0.0


class BoolQBenchmark:
    """BoolQ benchmark runner."""

    def __init__(self):
        self._lock = threading.RLock()
        self._problems: dict[str, BoolQProblem] = {}
        self._results: dict[str, BoolQResult] = {}
        self._predictions: dict[str, bool] = {}

    def load_problems(self, problems: list[dict[str, Any]] | None = None) -> int:
        """Load problems from list or use built-in."""
        if problems:
            for p in problems:
                problem = BoolQProblem(
                    id=p["id"],
                    question=p["question"],
                    passage=p["passage"],
                    answer=p["answer"],
                    metadata=p.get("metadata", {}),
                )
                self._problems[problem.id] = problem
            return len(problems)
        return self._load_default_problems()

    def _load_default_problems(self) -> int:
        """Load the built-in problems."""
        for i in range(1, 1001):
            problem = BoolQProblem(
                id=f"BoolQ_{i}",
                question=self._get_question(i),
                passage=self._get_passage(i),
                answer=self._get_answer(i),
                metadata={"difficulty": self._get_difficulty(i)},
            )
            self._problems[problem.id] = problem
        return 1000

    def _get_question(self, i: int) -> str:
        questions = {
            1: "Is the sky blue?",
            2: "Is water wet?",
            3: "Is the Earth flat?",
            4: "Is Python a programming language?",
            5: "Is the sun a star?",
        }
        if i in questions:
            return questions[i]
        return f"Is statement {i} true?"

    def _get_passage(self, i: int) -> str:
        passages = {
            1: "The sky appears blue due to Rayleigh scattering.",
            2: "Water is a liquid that feels wet to the touch.",
            3: "The Earth is an oblate spheroid.",
            4: "Python is a high-level programming language.",
            5: "The sun is a G-type main-sequence star.",
        }
        if i in passages:
            return passages[i]
        return f"Passage {i} provides context for the question."

    def _get_answer(self, i: int) -> bool:
        return i % 2 == 1

    def _get_difficulty(self, i: int) -> str:
        if i <= 300:
            return "easy"
        elif i <= 700:
            return "medium"
        else:
            return "hard"

    def set_prediction(self, problem_id: str, predicted: bool) -> None:
        with self._lock:
            self._predictions[problem_id] = predicted

    def run_problem(self, problem_id: str, predicted: bool | None = None) -> BoolQResult:
        """Run a single problem."""
        start = time.time()
        problem = self._problems.get(problem_id)
        if not problem:
            return BoolQResult(
                problem_id=problem_id,
                status=ProblemStatus.ERROR,
                duration_ms=(time.time() - start) * 1000,
            )

        pred = predicted if predicted is not None else self._predictions.get(problem_id, False)
        correct = pred == problem.answer

        duration = (time.time() - start) * 1000
        result = BoolQResult(
            problem_id=problem_id,
            status=ProblemStatus.PASSED if correct else ProblemStatus.FAILED,
            predicted=pred,
            correct=correct,
            duration_ms=duration,
        )
        self._results[problem_id] = result
        return result

    def run_all(self) -> list[BoolQResult]:
        """Run all loaded problems."""
        results = []
        for problem_id in self._problems:
            result = self.run_problem(problem_id)
            results.append(result)
        return results

    def get_pass_rate(self) -> dict[str, Any]:
        """Get pass rate statistics."""
        with self._lock:
            if not self._results:
                return {"total": 0, "passed": 0, "failed": 0, "pass_rate": 0.0}

            passed = sum(1 for r in self._results.values() if r.status == ProblemStatus.PASSED)
            total = len(self._results)
            return {
                "total": total,
                "passed": passed,
                "failed": total - passed,
                "pass_rate": passed / total if total else 0.0,
            }

    def get_problem(self, problem_id: str) -> Optional[BoolQProblem]:
        return self._problems.get(problem_id)

    def list_problems(self) -> list[str]:
        return list(self._problems.keys())

    def get_result(self, problem_id: str) -> Optional[BoolQResult]:
        return self._results.get(problem_id)

    def count(self) -> int:
        return len(self._problems)

    def clear_results(self) -> None:
        with self._lock:
            self._results.clear()


__all__ = [
    "BoolQBenchmark",
    "BoolQProblem",
    "BoolQResult",
    "ProblemStatus",
]
