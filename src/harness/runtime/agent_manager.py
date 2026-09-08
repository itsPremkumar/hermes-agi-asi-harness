"""
AgentManager - Spawn, track, delegate, and terminate agents.

Provides lifecycle management for agents including:
- Agent registration and spawning
- State tracking (idle, running, paused, terminated)
- Parent-child relationships
- Delegation between agents
- Health monitoring
- Graceful and force termination
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class AgentState(Enum):
    """Possible states for an agent."""
    PENDING = "pending"
    SPAWNING = "spawning"
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


@dataclass
class AgentInfo:
    """Information about a managed agent."""
    agent_id: str
    name: str
    agent_type: str
    state: AgentState = AgentState.PENDING
    parent_id: Optional[str] = None
    children_ids: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    error: Optional[str] = None
    task: Optional[str] = None
    result: Any = None
    _on_complete: Optional[Callable] = field(default=None, repr=False)

    @property
    def duration(self) -> Optional[float]:
        """Get the duration of agent execution in seconds."""
        if self.started_at is None:
            return None
        end = self.ended_at or time.time()
        return end - self.started_at

    @property
    def is_active(self) -> bool:
        """Check if the agent is currently active."""
        return self.state in (
            AgentState.IDLE,
            AgentState.RUNNING,
            AgentState.PAUSED,
            AgentState.WAITING,
        )

    @property
    def is_terminal(self) -> bool:
        """Check if the agent is in a terminal state."""
        return self.state in (
            AgentState.COMPLETED,
            AgentState.FAILED,
            AgentState.TERMINATED,
        )


class AgentManager:
    """Manages the lifecycle of agents in the harness."""

    def __init__(self):
        self._agents: Dict[str, AgentInfo] = {}
        self._lock = threading.RLock()
        self._type_index: Dict[str, Set[str]] = defaultdict(set)
        self._state_index: Dict[AgentState, Set[str]] = defaultdict(set)

    def spawn(
        self,
        name: str,
        agent_type: str = "generic",
        parent_id: Optional[str] = None,
        task: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
    ) -> AgentInfo:
        """Spawn a new agent and register it."""
        with self._lock:
            if agent_id is None:
                agent_id = f"agent-{uuid.uuid4().hex[:12]}"

            if agent_id in self._agents:
                raise ValueError(f"Agent with id '{agent_id}' already exists")

            agent = AgentInfo(
                agent_id=agent_id,
                name=name,
                agent_type=agent_type,
                state=AgentState.PENDING,
                parent_id=parent_id,
                task=task,
                metadata=metadata or {},
            )

            if parent_id and parent_id in self._agents:
                self._agents[parent_id].children_ids.add(agent_id)

            self._agents[agent_id] = agent
            self._type_index[agent_type].add(agent_id)
            self._state_index[AgentState.PENDING].add(agent_id)

            return agent

    def get(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent info by ID."""
        return self._agents.get(agent_id)

    def get_all(self) -> List[AgentInfo]:
        """Get all agents."""
        return list(self._agents.values())

    def get_by_type(self, agent_type: str) -> List[AgentInfo]:
        """Get all agents of a specific type."""
        with self._lock:
            ids = self._type_index.get(agent_type, set())
            return [self._agents[aid] for aid in ids if aid in self._agents]

    def get_by_state(self, state: AgentState) -> List[AgentInfo]:
        """Get all agents in a specific state."""
        with self._lock:
            ids = self._state_index.get(state, set())
            return [self._agents[aid] for aid in ids if aid in self._agents]

    def get_children(self, agent_id: str) -> List[AgentInfo]:
        """Get all children of an agent."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return []
            return [
                self._agents[cid]
                for cid in agent.children_ids
                if cid in self._agents
            ]

    def get_root_agents(self) -> List[AgentInfo]:
        """Get all root agents (no parent)."""
        return [a for a in self._agents.values() if a.parent_id is None]

    def transition(
        self,
        agent_id: str,
        new_state: AgentState,
        error: Optional[str] = None,
        result: Any = None,
    ) -> bool:
        """Transition an agent to a new state."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return False

            old_state = agent.state
            self._state_index[old_state].discard(agent_id)

            agent.state = new_state
            self._state_index[new_state].add(agent_id)

            if new_state == AgentState.RUNNING and agent.started_at is None:
                agent.started_at = time.time()

            if new_state in (AgentState.COMPLETED, AgentState.FAILED, AgentState.TERMINATED):
                agent.ended_at = time.time()
                if error:
                    agent.error = error
                if result is not None:
                    agent.result = result

        # Fire completion callback if set
        if new_state in (AgentState.COMPLETED, AgentState.FAILED, AgentState.TERMINATED) and agent._on_complete:
            try:
                agent._on_complete(agent)
            except Exception:
                pass

        return True

    def delegate(
        self,
        from_agent_id: str,
        to_agent_id: str,
        task: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Delegate a task from one agent to another."""
        with self._lock:
            from_agent = self._agents.get(from_agent_id)
            to_agent = self._agents.get(to_agent_id)
            if not from_agent or not to_agent:
                return False

            to_agent.task = task
            if metadata:
                to_agent.metadata.update(metadata)
            to_agent.metadata["delegated_from"] = from_agent_id
            to_agent.metadata["delegated_at"] = time.time()

        self.transition(to_agent_id, AgentState.RUNNING)
        return True

    def terminate(
        self,
        agent_id: str,
        reason: str = "manual",
        recursive: bool = True,
    ) -> bool:
        """Terminate an agent and optionally its children."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return False

            if recursive:
                for child_id in list(agent.children_ids):
                    self.terminate(child_id, reason=reason, recursive=True)

        self.transition(agent_id, AgentState.TERMINATED, error=reason)
        return True

    def set_result(self, agent_id: str, result: Any) -> bool:
        """Set the result for an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.result = result
        return True

    def set_on_complete(
        self, agent_id: str, callback: Callable[[AgentInfo], None]
    ) -> bool:
        """Set a callback to fire when the agent reaches a terminal state."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent._on_complete = callback
        return True

    def get_active_count(self) -> int:
        """Get the count of currently active agents."""
        with self._lock:
            return sum(
                1
                for a in self._agents.values()
                if a.state in (AgentState.IDLE, AgentState.RUNNING, AgentState.WAITING)
            )

    def get_stats(self) -> Dict[str, int]:
        """Get agent statistics by state."""
        with self._lock:
            return {
                state.value: len(ids)
                for state, ids in self._state_index.items()
                if ids
            }

    def remove(self, agent_id: str) -> bool:
        """Remove an agent from management entirely."""
        with self._lock:
            agent = self._agents.pop(agent_id, None)
            if not agent:
                return False

            self._type_index[agent.agent_type].discard(agent_id)
            self._state_index[agent.state].discard(agent_id)

            # Remove from parent's children
            if agent.parent_id and agent.parent_id in self._agents:
                self._agents[agent.parent_id].children_ids.discard(agent_id)

            return True

    def clear(self) -> None:
        """Remove all agents."""
        with self._lock:
            self._agents.clear()
            self._type_index.clear()
            self._state_index.clear()
