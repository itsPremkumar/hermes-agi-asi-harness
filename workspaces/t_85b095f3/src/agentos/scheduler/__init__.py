"""Agent scheduler with priority, fairness, and preemption support."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class Priority(IntEnum):
    """Agent priority levels (lower value = higher priority)."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class Agent:
    """Represents an AI agent task in the scheduler."""
    id: str
    name: str
    priority: Priority = Priority.NORMAL
    cpu_quota: float = 1.0  # CPU cores
    memory_quota: int = 512  # MB
    api_rate_limit: int = 60  # requests per minute
    tenant_id: str = "default"
    payload: Any = None
    created_at: float = field(default_factory=time.time)
    preemptible: bool = True
    state: str = "pending"  # pending, running, paused, completed, failed

    def __post_init__(self) -> None:
        if self.cpu_quota <= 0:
            raise ValueError("cpu_quota must be positive")
        if self.memory_quota <= 0:
            raise ValueError("memory_quota must be positive")
        if self.api_rate_limit <= 0:
            raise ValueError("api_rate_limit must be positive")


@dataclass
class ScheduleResult:
    """Result of a scheduling decision."""
    agent_id: str
    action: str  # "scheduled", "preempted", "queued", "rejected"
    reason: str = ""
    preempted_id: str | None = None


class Scheduler:
    """Priority-based agent scheduler with fairness and preemption."""

    def __init__(self, max_concurrent: int = 4, max_cpu: float = 8.0,
                 max_memory: int = 16384) -> None:
        self.max_concurrent = max_concurrent
        self.max_cpu = max_cpu
        self.max_memory = max_memory
        self._queue: list[Agent] = []
        self._running: dict[str, Agent] = {}
        self._paused_agents: set[str] = set()
        self._history: list[ScheduleResult] = []
        self._tenant_usage: dict[str, dict[str, float]] = defaultdict(
            lambda: {"cpu": 0.0, "memory": 0.0, "agents": 0}
        )

    @property
    def queue_size(self) -> int:
        return len(self._queue)

    @property
    def running_count(self) -> int:
        return len(self._running)

    @property
    def running_agents(self) -> list[Agent]:
        return list(self._running.values())

    def submit(self, agent: Agent) -> ScheduleResult:
        """Submit an agent for scheduling."""
        if agent.id in self._running:
            return ScheduleResult(agent.id, "rejected", "Agent already running")

        # Check if we can schedule immediately
        if self._can_schedule(agent):
            self._start(agent)
            result = ScheduleResult(agent.id, "scheduled")
        elif agent.priority == Priority.CRITICAL and agent.preemptible:
            # Try to preempt a lower-priority agent
            preempted = self._preempt_for(agent)
            if preempted:
                self._start(agent)
                result = ScheduleResult(
                    agent.id, "scheduled", preempted_id=preempted.id
                )
            else:
                self._enqueue(agent)
                result = ScheduleResult(agent.id, "queued", "No preemptable agent")
        else:
            self._enqueue(agent)
            result = ScheduleResult(agent.id, "queued", "Resources unavailable")

        self._history.append(result)
        return result

    def complete(self, agent_id: str) -> ScheduleResult | None:
        """Mark an agent as completed and schedule next from queue."""
        agent = self._running.pop(agent_id, None)
        if agent is None:
            return None

        agent.state = "completed"
        usage = self._tenant_usage[agent.tenant_id]
        usage["cpu"] -= agent.cpu_quota
        usage["memory"] -= agent.memory_quota
        usage["agents"] -= 1

        # Try to schedule next from queue
        self._schedule_queue()
        return ScheduleResult(agent_id, "completed")

    def fail(self, agent_id: str, reason: str = "") -> ScheduleResult | None:
        """Mark an agent as failed."""
        agent = self._running.pop(agent_id, None)
        if agent is None:
            return None

        agent.state = "failed"
        usage = self._tenant_usage[agent.tenant_id]
        usage["cpu"] -= agent.cpu_quota
        usage["memory"] -= agent.memory_quota
        usage["agents"] -= 1

        self._schedule_queue()
        return ScheduleResult(agent_id, "failed", reason)

    def pause(self, agent_id: str) -> bool:
        """Pause a running agent (preempt)."""
        agent = self._running.pop(agent_id, None)
        if agent is None:
            return False

        agent.state = "paused"
        usage = self._tenant_usage[agent.tenant_id]
        usage["cpu"] -= agent.cpu_quota
        usage["memory"] -= agent.memory_quota
        usage["agents"] -= 1

        # Re-queue with original priority but mark as paused
        agent.state = "pending"
        self._paused_agents.add(agent.id)
        self._enqueue(agent)
        # Schedule other waiting agents (not the paused one)
        self._schedule_queue()
        return True

    def resume(self, agent_id: str) -> bool:
        """Resume a paused agent."""
        if agent_id not in self._paused_agents:
            return False
        self._paused_agents.discard(agent_id)
        self._schedule_queue()
        return True

    def get_history(self) -> list[ScheduleResult]:
        """Return scheduling history."""
        return list(self._history)

    def _can_schedule(self, agent: Agent) -> bool:
        """Check if agent can be scheduled."""
        if len(self._running) >= self.max_concurrent:
            return False

        usage = self._tenant_usage[agent.tenant_id]
        total_cpu = sum(a.cpu_quota for a in self._running.values())
        total_memory = sum(a.memory_quota for a in self._running.values())

        if total_cpu + agent.cpu_quota > self.max_cpu:
            return False
        if total_memory + agent.memory_quota > self.max_memory:
            return False
        return True

    def _start(self, agent: Agent) -> None:
        """Start an agent."""
        agent.state = "running"
        self._running[agent.id] = agent
        usage = self._tenant_usage[agent.tenant_id]
        usage["cpu"] += agent.cpu_quota
        usage["memory"] += agent.memory_quota
        usage["agents"] += 1

    def _enqueue(self, agent: Agent) -> None:
        """Add agent to priority queue."""
        agent.state = "pending"
        self._queue.append(agent)
        # Sort by priority (lower = higher priority), then by creation time
        self._queue.sort(key=lambda a: (a.priority.value, a.created_at))

    def _preempt_for(self, agent: Agent) -> Agent | None:
        """Find and preempt a lower-priority agent."""
        # Find lowest priority, latest-created preemptible agent
        candidates = [
            a for a in self._running.values()
            if a.preemptible and a.priority > agent.priority
        ]
        if not candidates:
            return None

        # Sort by priority descending (lowest priority first), then by created_at descending
        candidates.sort(key=lambda a: (-a.priority.value, -a.created_at))
        victim = candidates[0]
        self.pause(victim.id)
        return victim

    def _schedule_queue(self) -> None:
        """Try to schedule agents from the queue (skip paused)."""
        scheduled = []
        for agent in self._queue:
            if agent.id in self._paused_agents:
                continue
            if self._can_schedule(agent):
                self._start(agent)
                scheduled.append(agent)
                self._history.append(ScheduleResult(agent.id, "scheduled"))

        for agent in scheduled:
            self._queue.remove(agent)
