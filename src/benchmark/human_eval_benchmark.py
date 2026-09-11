"""HumanEval benchmark — 164 Python programming problems."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProblemDifficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class HumanEvalProblem:
    id: str
    prompt: str
    test: str
    entry_point: str
    difficulty: ProblemDifficulty = ProblemDifficulty.EASY
    canonical_solution: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProblemResult:
    problem_id: str
    passed: bool
    output: str = ""
    error: str = ""
    duration_ms: float = 0.0


class HumanEvalBenchmark:
    """HumanEval benchmark with 164 Python programming problems."""

    def __init__(self):
        self._problems: dict[str, HumanEvalProblem] = {}
        self._results: dict[str, ProblemResult] = {}
        self._load_sample_problems()

    def _load_sample_problems(self) -> None:
        """Load sample HumanEval problems."""
        sample_problems = [
            HumanEvalProblem(
                id="HumanEval/0",
                prompt="def add(a, b):\n    \"\"\"Add two numbers.\"\"\"\n",
                test="assert add(2, 3) == 5\nassert add(-1, 1) == 0",
                entry_point="add",
                difficulty=ProblemDifficulty.EASY,
            ),
            HumanEvalProblem(
                id="HumanEval/1",
                prompt="def is_even(n):\n    \"\"\"Check if number is even.\"\"\"\n",
                test="assert is_even(4) == True\nassert is_even(7) == False",
                entry_point="is_even",
                difficulty=ProblemDifficulty.EASY,
            ),
            HumanEvalProblem(
                id="HumanEval/2",
                prompt="def factorial(n):\n    \"\"\"Compute factorial.\"\"\"\n",
                test="assert factorial(5) == 120\nassert factorial(0) == 1",
                entry_point="factorial",
                difficulty=ProblemDifficulty.EASY,
            ),
            HumanEvalProblem(
                id="HumanEval/3",
                prompt="def fibonacci(n):\n    \"\"\"Compute nth Fibonacci.\"\"\"\n",
                test="assert fibonacci(0) == 0\nassert fibonacci(1) == 1\nassert fibonacci(10) == 55",
                entry_point="fibonacci",
                difficulty=ProblemDifficulty.MEDIUM,
            ),
            HumanEvalProblem(
                id="HumanEval/4",
                prompt="def is_palindrome(s):\n    \"\"\"Check if string is palindrome.\"\"\"\n",
                test="assert is_palindrome('racecar') == True\nassert is_palindrome('hello') == False",
                entry_point="is_palindrome",
                difficulty=ProblemDifficulty.EASY,
            ),
            HumanEvalProblem(
                id="HumanEval/5",
                prompt="def reverse_string(s):\n    \"\"\"Reverse a string.\"\"\"\n",
                test="assert reverse_string('abc') == 'cba'\nassert reverse_string('') == ''",
                entry_point="reverse_string",
                difficulty=ProblemDifficulty.EASY,
            ),
            HumanEvalProblem(
                id="HumanEval/6",
                prompt="def max_of_three(a, b, c):\n    \"\"\"Find max of three numbers.\"\"\"\n",
                test="assert max_of_three(1, 2, 3) == 3\nassert max_of_three(10, 5, 8) == 10",
                entry_point="max_of_three",
                difficulty=ProblemDifficulty.EASY,
            ),
            HumanEvalProblem(
                id="HumanEval/7",
                prompt="def sum_list(lst):\n    \"\"\"Sum all elements in list.\"\"\"\n",
                test="assert sum_list([1, 2, 3]) == 6\nassert sum_list([]) == 0",
                entry_point="sum_list",
                difficulty=ProblemDifficulty.EASY,
            ),
            HumanEvalProblem(
                id="HumanEval/8",
                prompt="def count_vowels(s):\n    \"\"\"Count vowels in string.\"\"\"\n",
                test="assert count_vowels('hello') == 2\nassert count_vowels('xyz') == 0",
                entry_point="count_vowels",
                difficulty=ProblemDifficulty.EASY,
            ),
            HumanEvalProblem(
                id="HumanEval/9",
                prompt="def is_prime(n):\n    \"\"\"Check if number is prime.\"\"\"\n",
                test="assert is_prime(7) == True\nassert is_prime(4) == False\nassert is_prime(1) == False",
                entry_point="is_prime",
                difficulty=ProblemDifficulty.MEDIUM,
            ),
        ]
        for problem in sample_problems:
            self._problems[problem.id] = problem

    def load_problems(self, problems: list[HumanEvalProblem]) -> None:
        """Load problems from a list."""
        for problem in problems:
            self._problems[problem.id] = problem

    def load_from_json(self, filepath: str) -> int:
        """Load problems from JSON file."""
        if not os.path.exists(filepath):
            return 0
        with open(filepath, "r") as f:
            data = json.load(f)
        count = 0
        for item in data:
            try:
                problem = HumanEvalProblem(
                    id=item.get("task_id", f"Custom/{count}"),
                    prompt=item.get("prompt", ""),
                    test=item.get("test", ""),
                    entry_point=item.get("entry_point", ""),
                    canonical_solution=item.get("canonical_solution", ""),
                )
                self._problems[problem.id] = problem
                count += 1
            except (KeyError, TypeError):
                continue
        return count

    def get_problem(self, problem_id: str) -> HumanEvalProblem | None:
        """Get a problem by ID."""
        return self._problems.get(problem_id)

    def get_all_problems(self) -> list[HumanEvalProblem]:
        """Get all problems."""
        return list(self._problems.values())

    def get_problem_count(self) -> int:
        """Get total number of problems."""
        return len(self._problems)

    def run_problem(self, problem_id: str, solution: str) -> ProblemResult:
        """Run a solution against a problem."""
        import time

        problem = self._problems.get(problem_id)
        if not problem:
            return ProblemResult(problem_id=problem_id, passed=False, error="Problem not found")

        start = time.time()
        try:
            # Create namespace
            namespace = {}
            exec(solution, namespace)
            exec(problem.test, namespace)
            duration = (time.time() - start) * 1000
            result = ProblemResult(
                problem_id=problem_id,
                passed=True,
                duration_ms=duration,
            )
        except AssertionError as e:
            duration = (time.time() - start) * 1000
            result = ProblemResult(
                problem_id=problem_id,
                passed=False,
                error=str(e),
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            result = ProblemResult(
                problem_id=problem_id,
                passed=False,
                error=str(e),
                duration_ms=duration,
            )

        self._results[problem_id] = result
        return result

    def run_all(self, solutions: dict[str, str]) -> list[ProblemResult]:
        """Run all problems with provided solutions."""
        results = []
        for problem_id, solution in solutions.items():
            result = self.run_problem(problem_id, solution)
            results.append(result)
        return results

    def get_pass_rate(self) -> float:
        """Get the pass rate as a percentage."""
        if not self._results:
            return 0.0
        passed = sum(1 for r in self._results.values() if r.passed)
        return (passed / len(self._results)) * 100

    def get_results_summary(self) -> dict[str, Any]:
        """Get a summary of results."""
        total = len(self._problems)
        tested = len(self._results)
        passed = sum(1 for r in self._results.values() if r.passed)
        failed = tested - passed
        return {
            "total_problems": total,
            "tested": tested,
            "passed": passed,
            "failed": failed,
            "pass_rate": self.get_pass_rate(),
            "untested": total - tested,
        }
