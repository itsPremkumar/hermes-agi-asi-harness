"""curriculum.py — Capability gap discovery → difficulty estimation → select → practice → evaluate.

The curriculum system identifies what the agent is bad at, estimates how hard
each gap is to close, selects a sequence of practice tasks, runs them, and
evaluates progress.

Module API:
- CapabilityGap: a discovered weakness
- PracticeTask: a single practice exercise
- Curriculum: ordered sequence of practice tasks
- CurriculumBuilder: discovers gaps, estimates difficulty, builds curriculum
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import random
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclass
class CapabilityGap:
    """A discovered capability gap."""

    capability: str
    current_score: float  # 0.0 .. 1.0
    target_score: float  # 0.0 .. 1.0
    difficulty: float = 0.5  # 0.0 (easy) .. 1.0 (hard)
    evidence: list[str] = field(default_factory=list)

    @property
    def gap_size(self) -> float:
        return max(0.0, self.target_score - self.current_score)

    @property
    def priority(self) -> float:
        """Higher = more urgent. Combines gap size and inverse difficulty."""
        if self.difficulty <= 0:
            return self.gap_size
        return self.gap_size / self.difficulty

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CapabilityGap":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class PracticeTask:
    """A single practice exercise."""

    id: str
    capability: str
    description: str
    difficulty: float  # 0.0 .. 1.0
    expected_outcome: str = ""
    max_attempts: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PracticeTask":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class PracticeResult:
    """Outcome of attempting a practice task."""

    task_id: str
    success: bool
    attempts: int
    duration: float = 0.0
    score: float = 0.0  # 0.0 .. 1.0
    timestamp: float = field(default_factory=time.time)
    notes: str = ""


@dataclass
class Curriculum:
    """Ordered sequence of practice tasks targeting capability gaps."""

    id: str
    tasks: list[PracticeTask] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_task(self, task: PracticeTask) -> None:
        self.tasks.append(task)

    def remaining(self, completed: set[str]) -> list[PracticeTask]:
        return [t for t in self.tasks if t.id not in completed]

    def completion_rate(self, completed: set[str]) -> float:
        if not self.tasks:
            return 1.0
        return len(completed) / len(self.tasks)

    def to_skill_md(self) -> str:
        """Render this curriculum as a Hermes-compatible SKILL.md string."""
        frontmatter = {
            "name": self.id,
            "description": f"Curriculum with {len(self.tasks)} practice tasks",
            "version": 1,
        }
        lines = ["---"]
        for k, v in frontmatter.items():
            lines.append(f"{k}: {v}")
        lines.append("---")
        lines.append("")
        lines.append(f"# {self.id}")
        lines.append("")
        lines.append(f"This curriculum contains {len(self.tasks)} practice tasks.")
        lines.append("")
        if self.tasks:
            lines.append("## Tasks")
            lines.append("")
            for t in self.tasks:
                lines.append(f"- **{t.id}** (difficulty: {t.difficulty}): {t.description}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tasks": [t.to_dict() for t in self.tasks],
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Curriculum":
        tasks = [PracticeTask.from_dict(t) for t in data.pop("tasks", [])]
        return cls(tasks=tasks, **{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Curriculum builder
# ---------------------------------------------------------------------------


class CurriculumBuilder:
    """Discovers gaps, estimates difficulty, builds curriculum.

    Usage:
        builder = CurriculumBuilder()
        gaps = builder.discover_gaps(evaluator)
        curr = builder.build(gaps, task_pool)
    """

    def __init__(
        self,
        target_score: float = 0.8,
        gap_threshold: float = 0.2,
        difficulty_model: str = "inverse_score",
        seed: int | None = None,
    ) -> None:
        self.target_score = target_score
        self.gap_threshold = gap_threshold
        self.difficulty_model = difficulty_model
        self._rng = random.Random(seed)

    # -- gap discovery -----------------------------------------------------

    def discover_gaps(
        self,
        scores: dict[str, float],
        evidence: dict[str, list[str]] | None = None,
    ) -> list[CapabilityGap]:
        """Identify capabilities below target. Returns sorted by priority (highest first)."""
        gaps: list[CapabilityGap] = []
        evidence = evidence or {}
        for cap, score in scores.items():
            if score < self.target_score - self.gap_threshold:
                diff = self._estimate_difficulty(cap, score)
                gaps.append(
                    CapabilityGap(
                        capability=cap,
                        current_score=score,
                        target_score=self.target_score,
                        difficulty=diff,
                        evidence=evidence.get(cap, []),
                    )
                )
        return sorted(gaps, key=lambda g: g.priority, reverse=True)

    # -- difficulty estimation --------------------------------------------

    def _estimate_difficulty(self, capability: str, current_score: float) -> float:
        """Estimate how hard it is to close the gap for a capability.

        Models:
        - "inverse_score": harder when current score is low (foundational gap)
        - "linear": proportional to gap size
        - "constant": always 0.5
        """
        if self.difficulty_model == "inverse_score":
            return max(0.0, min(1.0, 1.0 - current_score))
        if self.difficulty_model == "linear":
            return max(0.0, min(1.0, self.target_score - current_score))
        if self.difficulty_model == "constant":
            return 0.5
        return 0.5

    # -- curriculum construction -------------------------------------------

    def build(
        self,
        gaps: Sequence[CapabilityGap],
        task_pool: Sequence[PracticeTask],
        max_tasks: int = 10,
    ) -> Curriculum:
        """Select tasks from the pool that target the discovered gaps.

        Strategy: for each gap (in priority order), pick the hardest task that
        doesn't exceed the gap's difficulty + 0.2 buffer. Fill up to max_tasks.
        """
        curriculum = Curriculum(id=self._make_id(gaps))
        used: set[str] = set()
        for gap in gaps:
            if len(curriculum.tasks) >= max_tasks:
                break
            # Find matching tasks
            matching = [
                t for t in task_pool
                if t.capability == gap.capability and t.id not in used
            ]
            # Sort by how close difficulty is to gap difficulty (prefer slightly harder)
            matching.sort(
                key=lambda t: abs(t.difficulty - min(gap.difficulty + 0.2, 1.0))
            )
            for t in matching:
                if len(curriculum.tasks) >= max_tasks:
                    break
                curriculum.add_task(t)
                used.add(t.id)
        return curriculum

    def build_sparse(
        self,
        gaps: Sequence[CapabilityGap],
        task_pool: Sequence[PracticeTask],
        max_tasks: int = 10,
    ) -> Curriculum:
        """Build curriculum with interleaved capabilities (round-robin)."""
        curriculum = Curriculum(id=self._make_id(gaps))
        by_cap: dict[str, list[PracticeTask]] = {}
        for t in task_pool:
            by_cap.setdefault(t.capability, []).append(t)
        gap_caps = [g.capability for g in gaps]
        idx = 0
        used: set[str] = set()
        while len(curriculum.tasks) < max_tasks and gap_caps:
            cap = gap_caps[idx % len(gap_caps)]
            available = [t for t in by_cap.get(cap, []) if t.id not in used]
            if available:
                task = self._rng.choice(available)
                curriculum.add_task(task)
                used.add(task.id)
            else:
                gap_caps = [c for c in gap_caps if c != cap]
                if not gap_caps:
                    break
            idx += 1
        return curriculum

    # -- evaluation --------------------------------------------------------

    def evaluate(
        self,
        curriculum: Curriculum,
        results: Sequence[PracticeResult],
    ) -> dict[str, Any]:
        """Evaluate curriculum completion and per-capability progress."""
        if not results:
            return {"completed": 0, "total": len(curriculum.tasks), "pass_rate": 0.0}
        by_cap: dict[str, list[float]] = {}
        for r in results:
            task = next((t for t in curriculum.tasks if t.id == r.task_id), None)
            if task:
                by_cap.setdefault(task.capability, []).append(r.score)
        per_capability = {
            cap: {"mean_score": statistics.mean(scores), "count": len(scores)}
            for cap, scores in by_cap.items()
        }
        return {
            "completed": len(results),
            "total": len(curriculum.tasks),
            "pass_rate": sum(1 for r in results if r.success) / len(results),
            "avg_score": statistics.mean(r.score for r in results),
            "per_capability": per_capability,
        }

    # -- internal ----------------------------------------------------------

    @staticmethod
    def _make_id(gaps: Sequence[CapabilityGap]) -> str:
        content = ",".join(sorted(g.capability for g in gaps))
        h = hashlib.sha256(content.encode()).hexdigest()[:8]
        return f"curr-{h}"


# ---------------------------------------------------------------------------
# Task pool helpers
# ---------------------------------------------------------------------------


def make_task_id(description: str) -> str:
    """Generate a stable task id from description."""
    h = hashlib.sha256(description.encode()).hexdigest()[:8]
    return f"task-{h}"


def simple_task_pool(capabilities: Sequence[str]) -> list[PracticeTask]:
    """Generate a basic task pool for given capabilities (for testing/demo)."""
    tasks: list[PracticeTask] = []
    for cap in capabilities:
        for level, diff in enumerate([0.2, 0.4, 0.6, 0.8]):
            desc = f"Practice {cap} at difficulty {level + 1}"
            tasks.append(
                PracticeTask(
                    id=make_task_id(desc),
                    capability=cap,
                    description=desc,
                    difficulty=diff,
                    expected_outcome=f"correct_{cap}",
                )
            )
    return tasks
