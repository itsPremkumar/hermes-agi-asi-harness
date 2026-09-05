"""
Agent Team Coordinator — Apodex 1.1 Pattern
============================================
Dynamic parallel sub-agent coordination with shared task state.
"""

from .agent_team import (
    AgentTeamCoordinator,
    AgentTeamResult,
    SubAgent,
    SubTask,
    SharedTaskState,
    AgentRole,
    AgentStatus,
    run_agent_team,
)

__all__ = [
    "AgentTeamCoordinator",
    "AgentTeamResult",
    "SubAgent",
    "SubTask",
    "SharedTaskState",
    "AgentRole",
    "AgentStatus",
    "run_agent_team",
]