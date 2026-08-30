"""JudgeBench — LLM evaluation and benchmarking."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class JudgeStatus(str, Enum):
    PENDING = "pending"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class JudgeResult:
    id: str
    model: str
    score: float
    details: dict[str, Any] = field(default_factory=dict)


class JudgeBench:
    """Evaluate models."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._results: dict[str, JudgeResult] = {}

    def evaluate(self, model: str, score: float, details: dict[str, Any] | None = None) -> JudgeResult:
        result = JudgeResult(id=str(uuid.uuid4()), model=model, score=score, details=details or {})
        self._results[result.id] = result
        return result

    def get(self, result_id: str) -> JudgeResult | None:
        return self._results.get(result_id)

    def list_all(self) -> list[JudgeResult]:
        return list(self._results.values())

    def get_best(self) -> JudgeResult | None:
        if not self._results:
            return None
        return max(self._results.values(), key=lambda r: r.score)

    def count(self) -> int:
        return len(self._results)
