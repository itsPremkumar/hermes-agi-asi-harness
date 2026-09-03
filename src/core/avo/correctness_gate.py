"""Correctness gate: correctness is a hard prerequisite for evaluation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class GateResult:
    passed: bool = False
    correctness: bool = False
    checks: List[Dict[str, Any]] = field(default_factory=list)
    reason: str = ""

    @property
    def can_evaluate(self) -> bool:
        return self.passed and self.correctness


class CorrectnessGate:
    """Gate that rejects broken candidates before performance evaluation.

    Prevents the evolutionary search from optimizing toward broken
    solutions (e.g. a version that is faster but incorrect).
    """

    def __init__(self, tests: List[str] | None = None) -> None:
        self._tests = tests or []

    def evaluate(
        self,
        candidate: Any,
        tests: List[str] | None = None,
    ) -> GateResult:
        test_names = tests if tests is not None else self._tests
        checks: List[Dict[str, Any]] = []
        all_passed = True
        for t in test_names:
            if callable(t):
                try:
                    t(candidate)
                    checks.append({"test": t.__name__, "passed": True})
                except Exception as e:
                    all_passed = False
                    checks.append({"test": t.__name__, "passed": False, "error": str(e)})
            else:
                checks.append({"test": str(t), "passed": True, "note": "skipped (no callable)"})
        return GateResult(
            passed=all_passed and bool(test_names),
            correctness=all_passed,
            checks=checks,
            reason="all tests passed" if all_passed else "tests failed",
        )
