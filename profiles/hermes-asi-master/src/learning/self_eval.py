"""self_eval.py — After-action review system.

The cycle: goal → prediction → outcome → error → correction → confidence.

A review captures what was expected, what actually happened, why they diverged,
and what to do differently next time. Confidence is updated via exponential decay
on past accuracy.

Module API:
- Review: dataclass holding a single after-action review
- SelfEvaluator: accumulates reviews, tracks confidence per capability
"""

from __future__ import annotations

import dataclasses
import json
import math
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Review:
    """Immutable after-action review for a single agent run."""

    goal: str
    prediction: str
    outcome: str
    success: bool
    confidence: float  # 0.0 .. 1.0 BEFORE this review's evidence is incorporated
    error: str = ""
    correction: str = ""
    capability: str = "general"
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Review":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Confidence tracker
# ---------------------------------------------------------------------------


class ConfidenceTracker:
    """Per-capability confidence that updates on each new review.

    Uses exponential moving average with alpha=0.3 (recent-biased).
    """

    def __init__(self, alpha: float = 0.3, default: float = 0.5) -> None:
        self.alpha = alpha
        self.default = default
        self._state: dict[str, float] = defaultdict(lambda: default)
        self._history: dict[str, list[float]] = defaultdict(list)

    def get(self, capability: str) -> float:
        return self._state[capability]

    def all(self) -> dict[str, float]:
        return dict(self._state)

    def update(self, capability: str, success: bool) -> float:
        target = 1.0 if success else 0.0
        current = self._state[capability]
        new = current + self.alpha * (target - current)
        new = max(0.0, min(1.0, new))
        self._state[capability] = new
        self._history[capability].append(new)
        return new

    def history(self, capability: str) -> list[float]:
        return list(self._history[capability])

    def reset(self, capability: str) -> None:
        self._state[capability] = self.default
        self._history.pop(capability, None)


# ---------------------------------------------------------------------------
# Self-evaluator
# ---------------------------------------------------------------------------


class SelfEvaluator:
    """Accumulates after-action reviews and produces analyses.

    Usage:
        ev = SelfEvaluator()
        ev.review(goal="sort list", prediction="sorted", outcome="sorted",
                  success=True, capability="sorting")
        report = ev.analyse()
    """

    def __init__(self, confidence_alpha: float = 0.3) -> None:
        self.reviews: list[Review] = []
        self._conf = ConfidenceTracker(alpha=confidence_alpha)

    # -- main API ----------------------------------------------------------

    def review(
        self,
        *,
        goal: str,
        prediction: str,
        outcome: str,
        success: bool,
        confidence: float = 0.5,
        error: str = "",
        correction: str = "",
        capability: str = "general",
        metadata: dict[str, Any] | None = None,
    ) -> Review:
        """Record a single after-action review."""
        r = Review(
            goal=goal,
            prediction=prediction,
            outcome=outcome,
            success=success,
            confidence=confidence,
            error=error,
            correction=correction,
            capability=capability,
            metadata=metadata or {},
        )
        self.reviews.append(r)
        self._conf.update(capability, success)
        return r

    def analyse(self, capability: str | None = None) -> dict[str, Any]:
        """Return aggregate statistics over stored reviews."""
        reviews = self._filter(capability)
        if not reviews:
            return {"count": 0, "accuracy": None, "confidence": None}
        successes = sum(1 for r in reviews if r.success)
        confs = [r.confidence for r in reviews]
        return {
            "count": len(reviews),
            "accuracy": successes / len(reviews),
            "confidence": self._conf.get(capability or "general"),
            "mean_reported_confidence": statistics.mean(confs) if confs else 0.0,
            "common_errors": self._top_errors(reviews),
            "recent_corrections": [r.correction for r in reviews[-5:] if r.correction],
        }

    def prediction_error_calibration(self, capability: str | None = None) -> dict[str, float]:
        """Compare reported confidence to actual accuracy — measures calibration.

        Returns {mae, calibration_error, bin_count}.
        """
        reviews = self._filter(capability)
        if not reviews:
            return {"mae": 0.0, "calibration_error": 0.0, "bin_count": 0}
        errors = [abs(r.confidence - (1.0 if r.success else 0.0)) for r in reviews]
        return {
            "mae": statistics.mean(errors),
            "calibration_error": statistics.stdev(errors) if len(errors) > 1 else 0.0,
            "bin_count": len(reviews),
        }

    def weak_points(self, top_k: int = 3) -> list[tuple[str, float]]:
        """Capabilities with the lowest confidence, ascending."""
        return sorted(self._conf.all().items(), key=lambda kv: kv[1])[:top_k]

    def improvement_trajectory(self, capability: str) -> list[float]:
        """Return confidence values over time for a capability."""
        return self._conf.history(capability)

    def forget(self, before: float) -> int:
        """Drop reviews older than `before` (unix timestamp). Returns removed count."""
        kept = [r for r in self.reviews if r.timestamp >= before]
        removed = len(self.reviews) - len(kept)
        self.reviews = kept
        return removed

    # -- serialisation ------------------------------------------------------

    def save(self, path: str | Path) -> None:
        data = {
            "reviews": [r.to_dict() for r in self.reviews],
            "confidence": self._conf.all(),
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "SelfEvaluator":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        ev = cls()
        for r in raw.get("reviews", []):
            ev.reviews.append(Review.from_dict(r))
        for cap, val in raw.get("confidence", {}).items():
            ev._conf._state[cap] = val
        return ev

    # -- internal -----------------------------------------------------------

    def _filter(self, capability: str | None) -> list[Review]:
        if capability is None:
            return list(self.reviews)
        return [r for r in self.reviews if r.capability == capability]

    @staticmethod
    def _top_errors(reviews: Sequence[Review], top_k: int = 3) -> list[tuple[str, int]]:
        counts: dict[str, int] = defaultdict(int)
        for r in reviews:
            if r.error and not r.success:
                counts[r.error] += 1
        return sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:top_k]

    def __len__(self) -> int:
        return len(self.reviews)
