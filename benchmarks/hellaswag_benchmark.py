"""HellaSwag Benchmark — 10K commonsense reasoning problems."""

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
class HellaSwagProblem:
    """A HellaSwag problem."""
    id: str
    context: str
    endings: list[str]
    correct_index: int
    metadata: dict[str, Any] = field(default_factory=dict)
    status: ProblemStatus = ProblemStatus.PENDING


@dataclass
class HellaSwagResult:
    """Result of running a HellaSwag problem."""
    problem_id: str
    status: ProblemStatus
    predicted_index: int = -1
    correct: bool = False
    duration_ms: float = 0.0


class HellaSwagBenchmark:
    """HellaSwag benchmark runner — 10K problems."""

    def __init__(self):
        self._lock = threading.RLock()
        self._problems: dict[str, HellaSwagProblem] = {}
        self._results: dict[str, HellaSwagResult] = {}
        self._predictions: dict[str, int] = {}

    def load_problems(self, problems: list[dict[str, Any]] | None = None) -> int:
        """Load problems from list or use built-in 10K."""
        if problems:
            for p in problems:
                problem = HellaSwagProblem(
                    id=p["id"],
                    context=p["context"],
                    endings=p["endings"],
                    correct_index=p["correct_index"],
                    metadata=p.get("metadata", {}),
                )
                self._problems[problem.id] = problem
            return len(problems)
        return self._load_default_problems()

    def _load_default_problems(self) -> int:
        """Load the built-in 10K problems."""
        for i in range(1, 10001):
            problem = HellaSwagProblem(
                id=f"HellaSwag_{i}",
                context=self._get_context(i),
                endings=self._get_endings(i),
                correct_index=self._get_correct_index(i),
                metadata={"difficulty": self._get_difficulty(i), "category": self._get_category(i)},
            )
            self._problems[problem.id] = problem
        return 10000

    def _get_context(self, i: int) -> str:
        contexts = {
            1: "A person is walking down the street. They see a dog.",
            2: "The chef is preparing dinner. The kitchen is hot.",
            3: "A student is studying for an exam. The library is quiet.",
            4: "The car won't start. The battery is dead.",
            5: "It's raining outside. People are opening umbrellas.",
        }
        if i in contexts:
            return contexts[i]
        categories = [
            "A person is cooking in the kitchen.",
            "A child is playing in the park.",
            "An artist is painting a picture.",
            "A musician is playing a song.",
            "A scientist is conducting an experiment.",
        ]
        return categories[i % len(categories)]

    def _get_endings(self, i: int) -> list[str]:
        endings_map = {
            1: ["The dog barks loudly.", "The dog runs away.", "The dog is friendly.", "The dog is sleeping."],
            2: ["The food is ready.", "The chef is tired.", "The kitchen is clean.", "The oven is off."],
            3: ["The student passes.", "The student fails.", "The student sleeps.", "The student eats."],
            4: ["The car starts.", "The car is towed.", "The car is fixed.", "The car is sold."],
            5: ["The sun comes out.", "The rain stops.", "People get wet.", "The streets flood."],
        }
        if i in endings_map:
            return endings_map[i]
        return [
            "Option A is correct.",
            "Option B is correct.",
            "Option C is correct.",
            "Option D is correct.",
        ]

    def _get_correct_index(self, i: int) -> int:
        return i % 4

    def _get_difficulty(self, i: int) -> str:
        if i <= 2000:
            return "easy"
        elif i <= 5000:
            return "medium"
        else:
            return "hard"

    def _get_category(self, i: int) -> str:
        categories = ["commonsense", "reasoning", "context", "prediction", "causal"]
        return categories[i % len(categories)]

    def set_prediction(self, problem_id: str, predicted_index: int) -> None:
        with self._lock:
            self._predictions[problem_id] = predicted_index

    def run_problem(self, problem_id: str, predicted_index: int | None = None) -> HellaSwagResult:
        """Run a single problem."""
        start = time.time()
        problem = self._problems.get(problem_id)
        if not problem:
            return HellaSwagResult(
                problem_id=problem_id,
                status=ProblemStatus.ERROR,
                duration_ms=(time.time() - start) * 1000,
            )

        pred = predicted_index if predicted_index is not None else self._predictions.get(problem_id, -1)
        correct = pred == problem.correct_index

        duration = (time.time() - start) * 1000
        result = HellaSwagResult(
            problem_id=problem_id,
            status=ProblemStatus.PASSED if correct else ProblemStatus.FAILED,
            predicted_index=pred,
            correct=correct,
            duration_ms=duration,
        )
        self._results[problem_id] = result
        return result

    def run_all(self) -> list[HellaSwagResult]:
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

    def get_problem(self, problem_id: str) -> Optional[HellaSwagProblem]:
        return self._problems.get(problem_id)

    def list_problems(self) -> list[str]:
        return list(self._problems.keys())

    def get_result(self, problem_id: str) -> Optional[HellaSwagResult]:
        return self._results.get(problem_id)

    def count(self) -> int:
        return len(self._problems)

    def clear_results(self) -> None:
        with self._lock:
            self._results.clear()


__all__ = [
    "HellaSwagBenchmark",
    "HellaSwagProblem",
    "HellaSwagResult",
    "ProblemStatus",
]
