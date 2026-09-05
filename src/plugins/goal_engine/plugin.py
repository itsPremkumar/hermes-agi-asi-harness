"""
plugin.py — Re-export module.
"""
from . import (
    Goal,
    GoalEngine,
    SubTask,
    TaskStatus,
    create,
)

# Backward-compatible aliases
HierarchicalGoal = Goal
GoalStatus = TaskStatus

__all__ = [
    "Goal",
    "GoalEngine",
    "GoalStatus",
    "HierarchicalGoal",
    "SubTask",
    "TaskStatus",
    "create",
]
