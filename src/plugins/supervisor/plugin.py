"""
plugin.py — Re-export module.
"""
from . import (
    DreamCycleRunner,
    HeartbeatRecord,
    ResourceBudget,
    SupervisorState,
    TaskSupervisor,
    create,
)

# Backward-compatible aliases for names referenced by older integrations
FailureRecord = HeartbeatRecord
SupervisorHealthMetrics = SupervisorState

__all__ = [
    "DreamCycleRunner",
    "FailureRecord",
    "HeartbeatRecord",
    "ResourceBudget",
    "SupervisorHealthMetrics",
    "SupervisorState",
    "TaskSupervisor",
    "create",
]
