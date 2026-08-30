"""Deep Agents Coordination — team/crew patterns, delegation, sub-agent spawning, consensus."""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from ..errors import DeepAgentError

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    PLANNER = "planner"
    EXECUTOR = "executor"
    REVIEWER = "reviewer"
    RESEARCHER = "researcher"
    VERIFIER = "verifier"
    COORDINATOR = "coordinator"


class AgentStatus(Enum):
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentTask:
    """A task assigned to an agent."""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    description: str = ""
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    assigned_to: Optional[str] = None
    parent_task_id: Optional[str] = None
    subtask_ids: list[str] = field(default_factory=list)


@dataclass
class Agent:
    """A deep agent."""

    agent_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = "agent"
    role: AgentRole = AgentRole.EXECUTOR
    status: AgentStatus = AgentStatus.IDLE
    capabilities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def can_handle(self, task_description: str) -> bool:
        return True


class DelegationPattern(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"
    CONSENSUS = "consensus"


@dataclass
class Delegation:
    """A delegation of tasks to agents."""

    pattern: DelegationPattern
    task: AgentTask
    assigned_agents: list[Agent] = field(default_factory=list)
    results: list[dict[str, Any]] = field(default_factory=list)


class Team:
    """A team of agents working together."""

    def __init__(self, name: str = "team") -> None:
        self.name = name
        self.team_id = str(uuid.uuid4())[:12]
        self.agents: dict[str, Agent] = {}
        self._lock = threading.Lock()

    def add_agent(self, agent: Agent) -> None:
        with self._lock:
            self.agents[agent.agent_id] = agent

    def remove_agent(self, agent_id: str) -> Optional[Agent]:
        with self._lock:
            return self.agents.pop(agent_id, None)

    def get_by_role(self, role: AgentRole) -> list[Agent]:
        return [a for a in self.agents.values() if a.role == role]

    def get_available(self) -> list[Agent]:
        return [a for a in self.agents.values() if a.status == AgentStatus.IDLE]

    @property
    def size(self) -> int:
        return len(self.agents)


class SubAgentSpawner:
    """Spawn sub-agents for complex tasks."""

    def __init__(self, max_concurrent: int = 5) -> None:
        self.max_concurrent = max_concurrent
        self._active: dict[str, Agent] = {}
        self._lock = threading.Lock()

    def spawn(self, name: str, role: AgentRole, capabilities: Optional[list[str]] = None) -> Agent:
        agent = Agent(name=name, role=role, capabilities=capabilities or [])
        with self._lock:
            self._active[agent.agent_id] = agent
        logger.info(f"Spawned sub-agent: {name} ({role.value})")
        return agent

    def terminate(self, agent_id: str) -> bool:
        with self._lock:
            agent = self._active.pop(agent_id, None)
            if agent:
                agent.status = AgentStatus.COMPLETED
                return True
        return False

    def get_active(self) -> list[Agent]:
        with self._lock:
            return list(self._active.values())

    @property
    def active_count(self) -> int:
        return len(self._active)


class ConsensusBuilder:
    """Build consensus among multiple agents."""

    def __init__(self, min_agreement: float = 0.6) -> None:
        self.min_agreement = min_agreement

    def vote(self, agents: list[Agent], proposals: list[str]) -> dict[str, Any]:
        if not agents or not proposals:
            return {"consensus": False, "winner": None, "votes": {}}

        votes: dict[str, int] = {}
        for agent in agents:
            vote = hash(agent.agent_id) % len(proposals)
            choice = proposals[vote]
            votes[choice] = votes.get(choice, 0) + 1

        total = sum(votes.values())
        winner = max(votes, key=votes.get)
        agreement = votes[winner] / total if total > 0 else 0

        return {
            "consensus": agreement >= self.min_agreement,
            "winner": winner if agreement >= self.min_agreement else None,
            "agreement": agreement,
            "votes": votes,
        }

    def multi_round_vote(self, agents: list[Agent], proposals: list[str], max_rounds: int = 3) -> dict[str, Any]:
        for round_num in range(max_rounds):
            result = self.vote(agents, proposals)
            if result["consensus"]:
                result["rounds"] = round_num + 1
                return result
        return {"consensus": False, "winner": None, "rounds": max_rounds, "votes": {}}


class CrewOrchestrator:
    """Orchestrate a crew of agents."""

    def __init__(self, team: Team) -> None:
        self.team = team
        self.spawner = SubAgentSpawner()
        self.consensus = ConsensusBuilder()

    def delegate(self, task: AgentTask, pattern: DelegationPattern = DelegationPattern.SEQUENTIAL) -> Delegation:
        delegation = Delegation(pattern=pattern, task=task)
        available = self.team.get_available()
        if not available:
            raise DeepAgentError("No available agents for delegation")
        delegation.assigned_agents = available[:3]
        return delegation

    def execute_sequential(self, tasks: list[AgentTask]) -> list[dict[str, Any]]:
        results = []
        for task in tasks:
            available = self.team.get_available()
            if available:
                agent = available[0]
                agent.status = AgentStatus.WORKING
                task.assigned_to = agent.agent_id
                task.status = "completed"
                results.append({"task_id": task.task_id, "agent": agent.name, "status": "done"})
                agent.status = AgentStatus.IDLE
        return results

    def execute_parallel(self, tasks: list[AgentTask]) -> list[dict[str, Any]]:
        results = []
        available = self.team.get_available()
        for i, task in enumerate(tasks):
            if i < len(available):
                agent = available[i]
                task.assigned_to = agent.agent_id
                task.status = "completed"
                results.append({"task_id": task.task_id, "agent": agent.name, "status": "done"})
        return results
