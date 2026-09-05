"""Monitor — Tracks progress and detects stalls."""
from __future__ import annotations

import time
from typing import Any, Dict

from core.supervisor import Goal


class Monitor:
    """Monitors sub-agent progress and detects stalls."""

    def __init__(self, stall_timeout: float = 300.0):
        self._stall_timeout = stall_timeout
        self._checkpoints: Dict[str, float] = {}

    def checkpoint(self, goal_id: str) -> None:
        """Record a checkpoint for a goal."""
        self._checkpoints[goal_id] = time.time()

    def is_stalled(self, goal_id: str) -> bool:
        """Check if a goal has stalled."""
        if goal_id not in self._checkpoints:
            return False
        elapsed = time.time() - self._checkpoints[goal_id]
        return elapsed > self._stall_timeout

    def get_progress(self, goal: Goal) -> Dict[str, Any]:
        """Get progress summary for a goal."""
        total = len(goal.sub_goals)
        completed = sum(1 for sg in goal.sub_goals if sg.status == "completed")
        failed = sum(1 for sg in goal.sub_goals if sg.status == "failed")
        in_progress = sum(1 for sg in goal.sub_goals if sg.status == "running")

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": total - completed - failed - in_progress,
            "percent": (completed / total * 100) if total > 0 else 0,
        }
