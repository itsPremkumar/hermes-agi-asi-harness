"""
Agent Fabric Registry — Sections 26-28 of v7 spec

Dynamic agent population with structured lifecycle:
create → initialize → assign → execute → publish → complete → archive
Plus pause/resume/checkpoint/handoff.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentInstance:
    """A dynamic agent instance."""
    agent_id: str
    role: str  # planner, researcher, coder, reviewer, etc.
    status: str = "created"  # created, initialized, assigned, executing, paused, completed, archived
    mission_id: str | None = None
    task_id: str | None = None
    checkpoint: dict[str, Any] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    subscriptions: list[str] = field(default_factory=list)


class AgentFabricRegistry:
    """Dynamic agent population management."""

    def __init__(self):
        self._agents: dict[str, AgentInstance] = {}
        self._roles: dict[str, list[str]] = {}  # role → [agent_ids]

    def create_agent(self, role: str) -> AgentInstance:
        """Create a new agent."""
        agent = AgentInstance(agent_id=str(uuid.uuid4()), role=role)
        self._agents[agent.agent_id] = agent
        
        if role not in self._roles:
            self._roles[role] = []
        self._roles[role].append(agent.agent_id)
        
        logger.debug(f"Created agent: {agent.agent_id} (role={role})")
        return agent

    def initialize_agent(self, agent_id: str, mission_id: str | None = None, config: dict[str, Any] | None = None):
        """Initialize an agent with mission context."""
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        agent.status = "initialized"
        agent.mission_id = mission_id
        if config:
            agent.checkpoint.update(config)
        agent.updated_at = time.time()
        return agent

    def assign_task(self, agent_id: str, task_id: str):
        """Assign a task to an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        agent.status = "assigned"
        agent.task_id = task_id
        agent.updated_at = time.time()
        return agent

    def start_execution(self, agent_id: str):
        """Mark agent as executing."""
        agent = self._agents.get(agent_id)
        if agent:
            agent.status = "executing"
            agent.updated_at = time.time()

    def pause_agent(self, agent_id: str):
        """Pause a running agent."""
        agent = self._agents.get(agent_id)
        if agent and agent.status == "executing":
            agent.status = "paused"
            agent.updated_at = time.time()

    def resume_agent(self, agent_id: str):
        """Resume a paused agent."""
        agent = self._agents.get(agent_id)
        if agent and agent.status == "paused":
            agent.status = "executing"
            agent.updated_at = time.time()

    def checkpoint_agent(self, agent_id: str, state: dict[str, Any]):
        """Save agent checkpoint."""
        agent = self._agents.get(agent_id)
        if agent:
            agent.checkpoint.update(state)
            agent.updated_at = time.time()

    def complete_agent(self, agent_id: str, artifacts: list[str] | None = None):
        """Mark agent as completed."""
        agent = self._agents.get(agent_id)
        if agent:
            agent.status = "completed"
            if artifacts:
                agent.artifacts.extend(artifacts)
            agent.updated_at = time.time()

    def archive_agent(self, agent_id: str):
        """Archive a completed agent."""
        agent = self._agents.get(agent_id)
        if agent:
            agent.status = "archived"
            agent.updated_at = time.time()

    def get_agent(self, agent_id: str) -> AgentInstance | None:
        return self._agents.get(agent_id)

    def get_agents(self, role: str | None = None, status: str | None = None, mission_id: str | None = None) -> list[AgentInstance]:
        """Get agents filtered by role, status, or mission."""
        results = list(self._agents.values())
        if role:
            results = [a for a in results if a.role == role]
        if status:
            results = [a for a in results if a.status == status]
        if mission_id:
            results = [a for a in results if a.mission_id == mission_id]
        return results

    def get_stats(self) -> dict[str, Any]:
        return {
            "total": len(self._agents),
            "by_role": {role: len(ids) for role, ids in self._roles.items()},
            "by_status": {
                status: sum(1 for a in self._agents.values() if a.status == status)
                for status in {a.status for a in self._agents.values()}
            },
        }


class AgentFabricPlugin:
    def __init__(self):
        self.registry = AgentFabricRegistry()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {"status": "healthy", **self.registry.get_stats()}

    async def create(self, role: str):
        return self.registry.create_agent(role)

    async def get_stats(self):
        return self.registry.get_stats()


async def create(kernel=None):
    plugin = AgentFabricPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
