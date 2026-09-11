"""AgentKernel — Lightweight Agent Runtime."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine


class AgentState(Enum):
    CREATED = "created"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AgentMessage:
    id: str = field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:8]}")
    sender: str = ""
    receiver: str = ""
    content: str = ""
    message_type: str = "text"
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AgentTask:
    id: str = field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    status: str = "pending"
    result: Any = None
    error: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class Agent:
    id: str = field(default_factory=lambda: f"agent_{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    state: AgentState = AgentState.CREATED
    priority: AgentPriority = AgentPriority.MEDIUM
    capabilities: list[str] = field(default_factory=list)
    tasks: list[AgentTask] = field(default_factory=list)
    inbox: list[AgentMessage] = field(default_factory=list)
    outbox: list[AgentMessage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    max_concurrent_tasks: int = 1

    def create_task(self, name: str, description: str = "") -> AgentTask:
        task = AgentTask(name=name, description=description)
        self.tasks.append(task)
        return task

    def get_task(self, task_id: str) -> AgentTask | None:
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_pending_tasks(self) -> list[AgentTask]:
        return [t for t in self.tasks if t.status == "pending"]

    def get_completed_tasks(self) -> list[AgentTask]:
        return [t for t in self.tasks if t.status == "completed"]


class AgentRuntime:
    """Runtime for executing agents."""

    def __init__(self, max_agents: int = 100):
        self._agents: dict[str, Agent] = {}
        self._max_agents = max_agents
        self._running = False
        self._message_handlers: dict[str, Callable] = {}
        self._task_handlers: dict[str, Callable] = {}

    def create_agent(self, name: str, description: str = "", capabilities: list[str] | None = None, **kwargs) -> Agent:
        """Create a new agent."""
        agent = Agent(
            name=name,
            description=description,
            capabilities=capabilities or [],
            **kwargs,
        )
        self._agents[agent.id] = agent
        return agent

    def get_agent(self, agent_id: str) -> Agent | None:
        """Get an agent by ID."""
        return self._agents.get(agent_id)

    def list_agents(self, state: AgentState | None = None) -> list[Agent]:
        """List all agents, optionally filtered by state."""
        agents = list(self._agents.values())
        if state:
            agents = [a for a in agents if a.state == state]
        return agents

    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def send_message(self, sender_id: str, receiver_id: str, content: str, message_type: str = "text") -> AgentMessage | None:
        """Send a message between agents."""
        receiver = self._agents.get(receiver_id)
        if not receiver:
            return None
        message = AgentMessage(
            sender=sender_id,
            receiver=receiver_id,
            content=content,
            message_type=message_type,
        )
        receiver.inbox.append(message)
        sender = self._agents.get(sender_id)
        if sender:
            sender.outbox.append(message)
        return message

    def register_message_handler(self, message_type: str, handler: Callable) -> None:
        """Register a handler for a message type."""
        self._message_handlers[message_type] = handler

    def register_task_handler(self, task_name: str, handler: Callable) -> None:
        """Register a handler for a task type."""
        self._task_handlers[task_name] = handler

    async def execute_task(self, agent_id: str, task_id: str) -> bool:
        """Execute a task on an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        task = agent.get_task(task_id)
        if not task:
            return False

        task.status = "running"
        task.started_at = datetime.utcnow()
        agent.state = AgentState.RUNNING

        try:
            handler = self._task_handlers.get(task.name)
            if handler:
                result = handler(task)
                if asyncio.iscoroutine(result):
                    result = await result
                task.result = result
            task.status = "completed"
            task.completed_at = datetime.utcnow()
            agent.state = AgentState.COMPLETED
            return True
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.completed_at = datetime.utcnow()
            agent.state = AgentState.FAILED
            return False

    def get_stats(self) -> dict[str, Any]:
        """Get runtime statistics."""
        return {
            "total_agents": len(self._agents),
            "running": sum(1 for a in self._agents.values() if a.state == AgentState.RUNNING),
            "completed": sum(1 for a in self._agents.values() if a.state == AgentState.COMPLETED),
            "failed": sum(1 for a in self._agents.values() if a.state == AgentState.FAILED),
            "message_handlers": len(self._message_handlers),
            "task_handlers": len(self._task_handlers),
        }
