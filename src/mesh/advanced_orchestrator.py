"""Advanced Multi-Agent Orchestrator.

Coordinates multiple agents with consensus, voting, load balancing,
and automatic failover.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentStatus(Enum):
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    ERROR = "error"
    OFFLINE = "offline"


class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AgentInfo:
    agent_id: str
    name: str
    capabilities: list[str]
    status: AgentStatus = AgentStatus.IDLE
    current_task: str | None = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    last_heartbeat: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentTask:
    task_id: str
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_agent: str | None = None
    status: str = "pending"
    result: Any = None
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    retries: int = 0
    max_retries: int = 2


@dataclass
class ConsensusResult:
    task_id: str
    agreed: bool
    votes: dict[str, Any]
    result: Any = None
    confidence: float = 0.0


class MultiAgentOrchestrator:
    """Orchestrate multiple agents with consensus."""

    def __init__(self):
        self._agents: dict[str, AgentInfo] = {}
        self._tasks: dict[str, AgentTask] = {}
        self._lock = threading.RLock()
        self._consensus_threshold = 0.6
        self._task_queue: list[str] = []

    def register_agent(self, agent: AgentInfo) -> None:
        """Register an agent."""
        with self._lock:
            self._agents[agent.agent_id] = agent

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent."""
        with self._lock:
            self._agents.pop(agent_id, None)

    def submit_task(self, task: AgentTask) -> None:
        """Submit a task for execution."""
        with self._lock:
            self._tasks[task.task_id] = task
            self._task_queue.append(task.task_id)

    def assign_task(self, task_id: str, agent_id: str) -> bool:
        """Assign a task to an agent."""
        with self._lock:
            task = self._tasks.get(task_id)
            agent = self._agents.get(agent_id)
            if not task or not agent:
                return False
            if agent.status != AgentStatus.IDLE:
                return False

            task.assigned_agent = agent_id
            task.status = "assigned"
            agent.status = AgentStatus.WORKING
            agent.current_task = task_id
            return True

    def auto_assign(self) -> list[tuple[str, str]]:
        """Auto-assign pending tasks to idle agents."""
        assignments = []
        with self._lock:
            pending = [
                tid for tid in self._task_queue
                if self._tasks[tid].status == "pending"
            ]
            idle = [
                a for a in self._agents.values()
                if a.status == AgentStatus.IDLE
            ]

            for task_id, agent in zip(pending, idle):
                if self.assign_task(task_id, agent.agent_id):
                    assignments.append((task_id, agent.agent_id))

        return assignments

    def complete_task(self, task_id: str, result: Any, success: bool = True) -> None:
        """Mark a task as completed."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return

            task.result = result
            task.completed_at = time.time()

            if success:
                task.status = "completed"
                if task.assigned_agent:
                    agent = self._agents.get(task.assigned_agent)
                    if agent:
                        agent.tasks_completed += 1
                        agent.status = AgentStatus.IDLE
                        agent.current_task = None
            else:
                task.retries += 1
                if task.retries >= task.max_retries:
                    task.status = "failed"
                    if task.assigned_agent:
                        agent = self._agents.get(task.assigned_agent)
                        if agent:
                            agent.tasks_failed += 1
                            agent.status = AgentStatus.IDLE
                            agent.current_task = None
                else:
                    task.status = "pending"
                    # Reset agent to idle so it can pick up the retried task
                    if task.assigned_agent:
                        agent = self._agents.get(task.assigned_agent)
                        if agent:
                            agent.status = AgentStatus.IDLE
                            agent.current_task = None
                    task.assigned_agent = None

    def reach_consensus(self, task_id: str, votes: dict[str, Any]) -> ConsensusResult:
        """Reach consensus among agents."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return ConsensusResult(task_id=task_id, agreed=False, votes=votes)

            # Count agreements
            if not votes:
                return ConsensusResult(task_id=task_id, agreed=False, votes={})

            # Simple majority vote
            values = list(votes.values())
            most_common = max(set(values), key=values.count)
            agreement = values.count(most_common) / len(values)

            agreed = agreement >= self._consensus_threshold
            return ConsensusResult(
                task_id=task_id,
                agreed=agreed,
                votes=votes,
                result=most_common if agreed else None,
                confidence=agreement,
            )

    def heartbeat(self, agent_id: str) -> None:
        """Update agent heartbeat."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent:
                agent.last_heartbeat = time.time()

    def get_agent_status(self, agent_id: str) -> AgentInfo | None:
        """Get agent status."""
        with self._lock:
            return self._agents.get(agent_id)

    def get_all_agents(self) -> list[AgentInfo]:
        """Get all agents."""
        with self._lock:
            return list(self._agents.values())

    def get_pending_tasks(self) -> list[AgentTask]:
        """Get pending tasks."""
        with self._lock:
            return [t for t in self._tasks.values() if t.status == "pending"]

    def get_completed_tasks(self) -> list[AgentTask]:
        """Get completed tasks."""
        with self._lock:
            return [t for t in self._tasks.values() if t.status == "completed"]

    def get_stats(self) -> dict[str, Any]:
        """Get orchestrator stats."""
        with self._lock:
            return {
                "total_agents": len(self._agents),
                "idle_agents": sum(1 for a in self._agents.values() if a.status == AgentStatus.IDLE),
                "working_agents": sum(1 for a in self._agents.values() if a.status == AgentStatus.WORKING),
                "total_tasks": len(self._tasks),
                "pending_tasks": sum(1 for t in self._tasks.values() if t.status == "pending"),
                "completed_tasks": sum(1 for t in self._tasks.values() if t.status == "completed"),
                "failed_tasks": sum(1 for t in self._tasks.values() if t.status == "failed"),
            }
