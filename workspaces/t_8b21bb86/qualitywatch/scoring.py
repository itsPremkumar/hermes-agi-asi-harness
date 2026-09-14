"""Quality score computation and trend analysis."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from qualitywatch.models import CheckResult


def compute_score(results: list[CheckResult]) -> dict[str, Any]:
    """Aggregate check results into a quality score (0.0-100.0)."""
    if not results:
        return {"score": 100.0, "total": 0, "passed": 0, "failed": 0, "skipped": 0}

    total = len(results)
    passed = sum(1 for r in results if r.status.value == "pass")
    failed = sum(1 for r in results if r.status.value == "fail")
    skipped = sum(1 for r in results if r.status.value == "skip")

    weight_map = {"error": 1.0, "warning": 0.5, "info": 0.1}
    penalty = 0.0
    for r in results:
        if r.status.value == "fail":
            penalty += weight_map.get(r.severity.value, 1.0)

    max_penalty = total * 1.0
    score = max(0.0, round(100.0 * (1.0 - penalty / max_penalty), 2)) if max_penalty else 100.0
    return {"score": score, "total": total, "passed": passed, "failed": failed, "skipped": skipped}


class TrendTracker:
    """Tracks quality scores over time for trend analysis."""

    def __init__(self) -> None:
        self._history: list[dict[str, Any]] = []

    def add(self, score: float, timestamp: datetime | None = None) -> None:
        self._history.append({
            "score": score,
            "timestamp": (timestamp or datetime.now()).isoformat(),
        })

    @property
    def history(self) -> list[dict[str, Any]]:
        return list(self._history)

    @property
    def trend(self) -> str:
        if len(self._history) < 2:
            return "insufficient_data"
        recent = self._history[-3:]
        older = self._history[:3]
        avg_recent = sum(s["score"] for s in recent) / len(recent)
        avg_older = sum(s["score"] for s in older) / len(older)
        if avg_recent > avg_older + 2:
            return "improving"
        if avg_recent < avg_older - 2:
            return "declining"
        return "stable"

    @property
    def current(self) -> float | None:
        return self._history[-1]["score"] if self._history else None