"""ARC-AGI-3 Level Tracker — track progress through ARC-AGI-3 levels."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LevelStatus(str, Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


@dataclass
class LevelAttempt:
    """An attempt at a level."""
    id: str
    level_id: str
    success: bool
    score: float = 0.0
    time_ms: float = 0.0
    steps: int = 0
    strategy_used: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Level:
    """An ARC-AGI-3 level."""
    id: str
    name: str
    description: str
    difficulty: Difficulty
    status: LevelStatus = LevelStatus.LOCKED
    best_score: float = 0.0
    attempts: int = 0
    solved: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class LevelTracker:
    """Track progress through ARC-AGI-3 levels."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._levels: dict[str, Level] = {}
        self._attempts: list[LevelAttempt] = []

    def register_level(self, name: str, description: str,
                       difficulty: Difficulty, level_id: str | None = None) -> Level:
        """Register a level."""
        level = Level(
            id=level_id or str(uuid.uuid4()),
            name=name,
            description=description,
            difficulty=difficulty,
        )
        self._levels[level.id] = level
        return level

    def get_level(self, level_id: str) -> Level | None:
        """Get a level by ID."""
        return self._levels.get(level_id)

    def list_levels(self) -> list[Level]:
        """List all levels."""
        return list(self._levels.values())

    def unlock(self, level_id: str) -> bool:
        """Unlock a level."""
        if level_id in self._levels:
            self._levels[level_id].status = LevelStatus.UNLOCKED
            return True
        return False

    def start_level(self, level_id: str) -> bool:
        """Mark a level as in progress."""
        if level_id in self._levels:
            self._levels[level_id].status = LevelStatus.IN_PROGRESS
            return True
        return False

    def record_attempt(self, level_id: str, success: bool, score: float = 0.0,
                       time_ms: float = 0.0, steps: int = 0,
                       strategy_used: str = "") -> LevelAttempt:
        """Record an attempt at a level."""
        attempt = LevelAttempt(
            id=str(uuid.uuid4()),
            level_id=level_id,
            success=success,
            score=score,
            time_ms=time_ms,
            steps=steps,
            strategy_used=strategy_used,
        )
        self._attempts.append(attempt)

        # Update level
        if level_id in self._levels:
            level = self._levels[level_id]
            level.attempts += 1
            if success:
                level.solved = True
                level.status = LevelStatus.COMPLETED
                level.best_score = max(level.best_score, score)
            else:
                level.status = LevelStatus.FAILED

        return attempt

    def get_attempts(self, level_id: str) -> list[LevelAttempt]:
        """Get all attempts at a level."""
        return [a for a in self._attempts if a.level_id == level_id]

    def get_solved_count(self) -> int:
        """Get number of solved levels."""
        return sum(1 for l in self._levels.values() if l.solved)

    def get_total_count(self) -> int:
        """Get total number of levels."""
        return len(self._levels)

    def get_progress(self) -> float:
        """Get overall progress (0.0 to 1.0)."""
        if not self._levels:
            return 0.0
        return self.get_solved_count() / len(self._levels)

    def get_state(self) -> dict[str, Any]:
        return {
            "total": self.get_total_count(),
            "solved": self.get_solved_count(),
            "progress": self.get_progress(),
            "attempts": len(self._attempts),
        }
