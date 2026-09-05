"""
Self-Evaluation Plugin — Self-Assessment & Performance Tracking

Tracks: success/failure, quality scores, evidence, accuracy,
hallucination rate, user satisfaction. Provides self-improvement signals.
"""

import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class EvaluationRecord:
    task_id: str
    success: bool
    quality_score: float  # 0-1
    accuracy: float = 0.0
    hallucination_score: float = 0.0
    user_satisfaction: float = 0.0
    duration_seconds: float = 0.0
    evidence: list[str] = field(default_factory=list)
    mistakes: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "success": self.success,
            "quality_score": self.quality_score,
            "accuracy": self.accuracy,
            "hallucination_score": self.hallucination_score,
            "user_satisfaction": self.user_satisfaction,
            "duration_seconds": self.duration_seconds,
            "evidence": self.evidence,
            "mistakes": self.mistakes,
            "improvements": self.improvements,
            "timestamp": self.timestamp,
        }


class SelfEvaluation:
    """Self-evaluation engine."""

    def __init__(self, storage_path: Path | None = None):
        self._records: list[EvaluationRecord] = []
        self._quality_by_task: dict[str, list[float]] = defaultdict(list)
        self._mistakes_by_type: dict[str, int] = defaultdict(int)
        self._storage_path = storage_path

        if storage_path and storage_path.exists():
            self._load()

    def _load(self):
        try:
            with open(self._storage_path, "r") as f:
                data = json.load(f)
                for r in data.get("records", []):
                    self._records.append(EvaluationRecord(**r))
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    def _save(self):
        if not self._storage_path:
            return
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._storage_path, "w") as f:
                json.dump(
                    {"records": [r.to_dict() for r in self._records[-1000:]]},
                    f, indent=2
                )
        except Exception:
            pass

    def evaluate(self, task_id: str, success: bool, quality_score: float,
                 accuracy: float = 0.0, hallucination_score: float = 0.0,
                 user_satisfaction: float = 0.0, duration_seconds: float = 0.0,
                 evidence: list[str] | None = None, mistakes: list[str] | None = None,
                 improvements: list[str] | None = None) -> EvaluationRecord:
        """Record a self-evaluation."""
        record = EvaluationRecord(
            task_id=task_id,
            success=success,
            quality_score=max(0.0, min(1.0, quality_score)),
            accuracy=max(0.0, min(1.0, accuracy)),
            hallucination_score=max(0.0, min(1.0, hallucination_score)),
            user_satisfaction=max(0.0, min(1.0, user_satisfaction)),
            duration_seconds=duration_seconds,
            evidence=evidence or [],
            mistakes=mistakes or [],
            improvements=improvements or [],
        )
        self._records.append(record)
        self._quality_by_task[task_id].append(quality_score)
        for m in mistakes or []:
            self._mistakes_by_type[m] += 1
        self._save()
        return record

    def get_summary(self) -> dict[str, Any]:
        if not self._records:
            return {
                "total_evaluations": 0,
                "success_rate": 0.0,
                "avg_quality": 0.0,
                "avg_accuracy": 0.0,
                "avg_hallucination": 0.0,
                "avg_user_satisfaction": 0.0,
            }
        return {
            "total_evaluations": len(self._records),
            "success_rate": sum(1 for r in self._records if r.success) / len(self._records),
            "avg_quality": sum(r.quality_score for r in self._records) / len(self._records),
            "avg_accuracy": sum(r.accuracy for r in self._records) / len(self._records),
            "avg_hallucination": sum(r.hallucination_score for r in self._records) / len(self._records),
            "avg_user_satisfaction": sum(r.user_satisfaction for r in self._records) / len(self._records),
        }

    def get_mistake_patterns(self) -> list[dict[str, Any]]:
        """Identify recurring mistakes."""
        sorted_mistakes = sorted(self._mistakes_by_type.items(), key=lambda x: -x[1])
        return [{"type": m, "count": c} for m, c in sorted_mistakes[:10]]

    def get_improvement_signals(self) -> list[str]:
        """Generate improvement signals based on patterns."""
        signals = []
        summary = self.get_summary()
        if summary["success_rate"] < 0.7:
            signals.append("success_rate_below_70_percent")
        if summary["avg_quality"] < 0.6:
            signals.append("quality_below_threshold")
        if summary["avg_hallucination"] > 0.2:
            signals.append("high_hallucination_rate")
        if summary["avg_user_satisfaction"] < 0.6:
            signals.append("low_user_satisfaction")
        return signals

    def get_recent_records(self, limit: int = 10) -> list[EvaluationRecord]:
        return list(reversed(self._records[-limit:]))


class SelfEvaluationPlugin:
    def __init__(self, storage_path: Path | None = None):
        self.engine = SelfEvaluation(storage_path=storage_path)

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {
            "status": "healthy",
            "total_evaluations": len(self.engine._records),
            "summary": self.engine.get_summary(),
        }


async def create(kernel=None):
    plugin = SelfEvaluationPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
