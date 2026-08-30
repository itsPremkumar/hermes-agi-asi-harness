"""Evaluation Gate — Grounded feedback for the supervisor.

Key principle: NEVER trust the agent's self-assessment. Always verify externally.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List


class EvaluationType(str, Enum):
    BINARY = "binary"           # Pass/fail
    SCALED = "scaled"           # 0.0 to 1.0
    MULTI_METRIC = "multi"      # Multiple metrics


@dataclass
class EvaluationResult:
    """Result of an evaluation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_id: str = ""
    score: float = 0.0
    passed: bool = False
    feedback: str = ""
    metrics: Dict[str, float] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    evaluator: str = ""


@dataclass
class TestCase:
    """A test case for evaluation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    input: Any = None
    expected: Any = None
    actual: Any = None
    passed: bool = False
    score: float = 0.0


class EvaluationGate:
    """Grounded evaluation — never trust self-assessment."""

    def __init__(self):
        self._evaluators: Dict[str, Callable] = {}
        self._history: List[EvaluationResult] = []
        self._test_cases: Dict[str, List[TestCase]] = {}

    def register_evaluator(self, name: str, evaluator: Callable) -> None:
        """Register an evaluator function."""
        self._evaluators[name] = evaluator

    def evaluate(
        self,
        task_id: str,
        result: Any,
        expected: Any,
        evaluator_name: str | None = None,
    ) -> EvaluationResult:
        """Evaluate a result against expected output."""
        if evaluator_name and evaluator_name in self._evaluators:
            evaluator = self._evaluators[evaluator_name]
            score, feedback, details = evaluator(result, expected)
        else:
            score, feedback, details = self._default_evaluate(result, expected)

        eval_result = EvaluationResult(
            task_id=task_id,
            score=score,
            passed=score >= 1.0,
            feedback=feedback,
            details=details,
            evaluator=evaluator_name or "default",
        )
        self._history.append(eval_result)
        return eval_result

    def _default_evaluate(self, result: Any, expected: Any) -> tuple[float, str, Dict]:
        """Default evaluation: exact match."""
        if result == expected:
            return 1.0, "Correct", {"match": "exact"}
        elif str(result).strip() == str(expected).strip():
            return 1.0, "Correct (whitespace normalized)", {"match": "normalized"}
        else:
            feedback = f"Expected: {expected}\nGot: {result}"
            return 0.0, feedback, {"match": "none"}

    def evaluate_with_tests(
        self,
        task_id: str,
        result: Any,
        test_cases: List[TestCase],
    ) -> EvaluationResult:
        """Evaluate against multiple test cases."""
        passed = 0
        total = len(test_cases)
        details = {"tests": []}

        for tc in test_cases:
            tc.actual = result
            if result == tc.expected:
                tc.passed = True
                tc.score = 1.0
                passed += 1
            else:
                tc.passed = False
                tc.score = 0.0
            details["tests"].append({
                "name": tc.name,
                "passed": tc.passed,
                "expected": tc.expected,
                "actual": tc.actual,
            })

        score = passed / total if total > 0 else 0.0
        feedback = f"Passed {passed}/{total}/{total} tests"

        eval_result = EvaluationResult(
            task_id=task_id,
            score=score,
            passed=score >= 1.0,
            feedback=feedback,
            details=details,
            evaluator="test_suite",
        )
        self._history.append(eval_result)
        return eval_result

    def get_history(self, task_id: str | None = None) -> List[EvaluationResult]:
        """Get evaluation history."""
        if task_id:
            return [e for e in self._history if e.task_id == task_id]
        return self._history.copy()

    def get_average_score(self, task_id: str | None = None) -> float:
        """Get average score."""
        history = self.get_history(task_id)
        if not history:
            return 0.0
        return sum(e.score for e in history) / len(history)


class CodeEvaluationGate(EvaluationGate):
    """Evaluation gate for code tasks."""

    def __init__(self):
        super().__init__()
        self.register_evaluator("code", self._evaluate_code)

    def _evaluate_code(self, result: Any, expected: Any) -> tuple[float, str, Dict]:
        """Evaluate code output."""
        result_str = str(result).strip()
        expected_str = str(expected).strip()

        if result_str == expected_str:
            return 1.0, "Output matches expected", {"match": "exact"}

        # Try numeric comparison
        try:
            result_num = float(result_str)
            expected_num = float(expected_str)
            if abs(result_num - expected_num) < 1e-9:
                return 1.0, "Numeric match", {"match": "numeric"}
        except (ValueError, TypeError):
            pass

        # Partial credit for containing expected
        if expected_str in result_str:
            return 0.5, "Partial match (contains expected)", {"match": "partial"}

        return 0.0, f"Expected: {expected}\nGot: {result}", {"match": "none"}


class BenchmarkEvaluationGate(EvaluationGate):
    """Evaluation gate for benchmark tasks."""

    def __init__(self):
        super().__init__()
        self.register_evaluator("benchmark", self._evaluate_benchmark)

    def _evaluate_benchmark(self, result: Any, expected: Any) -> tuple[float, str, Dict]:
        """Evaluate benchmark result."""
        # For benchmarks, result is typically a dict with metrics
        if isinstance(result, dict) and isinstance(expected, dict):
            metrics = {}
            for key in expected:
                if key in result:
                    exp_val = expected[key]
                    res_val = result[key]
                    if isinstance(exp_val, (int, float)) and isinstance(res_val, (int, float)):
                        if exp_val != 0:
                            metrics[key] = min(1.0, res_val / exp_val)
                        else:
                            metrics[key] = 1.0 if res_val == 0 else 0.0

            if metrics:
                avg_score = sum(metrics.values()) / len(metrics)
                return avg_score, f"Benchmark score: {avg_score:.2%}", {"metrics": metrics}

        return self._default_evaluate(result, expected)
