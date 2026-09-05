"""
HERMES INTELLIGENCE OS — PLANE 12: AGENT FABRIC & RECURSIVE SUBAGENTS
=====================================================================
Prime-Agent inspired recursive subagent fabric:
- Ephemeral specialist spawning (Researcher, Coder, Reviewer, Verifier, Security)
- Strict recursive bounds: depth limits, budget inheritance, scope inheritance
- Typed direct agent-to-agent message routing without executive bottleneck
- Hierarchical session tree tracking
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("hermes.os.agent_fabric")


class AgentRole(str, Enum):
    RESEARCHER = "researcher"
    ARCHITECT = "architect"
    CODER = "coder"
    DEBUGGER = "debugger"
    TESTER = "tester"
    SECURITY = "security"
    VERIFIER = "verifier"
    CRITIC = "critic"
    RED_TEAM = "red_team"
    SPECIALIST = "specialist"


@dataclass
class AgentMessage:
    """Typed inter-agent message protocol."""
    message_id: str = field(default_factory=lambda: f"msg-{uuid.uuid4().hex[:8]}")
    task_id: str = ""
    sender: str = ""
    receiver: str = ""
    message_type: str = "request"  # request, response, critique, evidence, alert
    content: str = ""
    artifact_refs: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    confidence: float = 1.0
    requested_action: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "task_id": self.task_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type,
            "content": self.content,
            "artifact_refs": self.artifact_refs,
            "evidence_refs": self.evidence_refs,
            "confidence": self.confidence,
            "requested_action": self.requested_action,
            "timestamp": self.timestamp,
        }


@dataclass
class SubagentHandle:
    """Descriptor and execution control handle for a spawned subagent."""
    agent_id: str
    role: AgentRole
    parent_id: Optional[str]
    depth: int
    token_budget: int
    timeout_seconds: float
    allowed_tools: list[str]
    status: str = "running"  # running, completed, failed, cancelled
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "parent_id": self.parent_id,
            "depth": self.depth,
            "token_budget": self.token_budget,
            "timeout_seconds": self.timeout_seconds,
            "allowed_tools": self.allowed_tools,
            "status": self.status,
            "created_at": self.created_at,
        }


class RecursiveAgentFabric:
    """
    Spawns, bounds, and routes communication among recursive specialist agents.
    Enforces parent-to-child attenuation of authority and compute.
    """

    def __init__(self, max_global_depth: int = 4, max_fanout: int = 6):
        self.max_global_depth = max_global_depth
        self.max_fanout = max_fanout
        self._active_agents: dict[str, SubagentHandle] = {}
        self._message_inbox: dict[str, list[AgentMessage]] = {}
        self._message_history: list[AgentMessage] = []

    def spawn_subagent(
        self,
        role: AgentRole | str,
        parent_handle: Optional[SubagentHandle] = None,
        tool_whitelist: Optional[list[str]] = None,
        token_budget: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
    ) -> SubagentHandle:
        """Spawn a child specialist with strictly inherited bounds."""
        if isinstance(role, str):
            try:
                role = AgentRole(role.lower())
            except ValueError:
                role = AgentRole.SPECIALIST

        parent_depth = parent_handle.depth if parent_handle else 0
        child_depth = parent_depth + 1

        if child_depth > self.max_global_depth:
            raise PermissionError(f"Cannot spawn subagent: depth {child_depth} exceeds max allowed depth {self.max_global_depth}")

        # Budget attenuation
        if parent_handle:
            inherited_budget = token_budget or (parent_handle.token_budget // 2)
            inherited_budget = min(inherited_budget, parent_handle.token_budget)
            inherited_timeout = timeout_seconds or (parent_handle.timeout_seconds * 0.8)
            # Tool intersection
            tools = [t for t in (tool_whitelist or parent_handle.allowed_tools) if t in parent_handle.allowed_tools]
        else:
            inherited_budget = token_budget or 100000
            inherited_timeout = timeout_seconds or 120.0
            tools = list(tool_whitelist or ["*"])

        aid = f"ag-{role.value[:3]}-{uuid.uuid4().hex[:6]}"
        handle = SubagentHandle(
            agent_id=aid,
            role=role,
            parent_id=parent_handle.agent_id if parent_handle else None,
            depth=child_depth,
            token_budget=inherited_budget,
            timeout_seconds=inherited_timeout,
            allowed_tools=tools,
        )

        self._active_agents[aid] = handle
        self._message_inbox[aid] = []
        logger.info("Spawned subagent %s (role: %s, depth: %d, budget: %d)", aid, role.value, child_depth, inherited_budget)
        return handle

    def send_message(self, message: AgentMessage) -> None:
        """Deliver typed message directly to recipient agent inbox."""
        if message.receiver not in self._message_inbox:
            self._message_inbox[message.receiver] = []
        self._message_inbox[message.receiver].append(message)
        self._message_history.append(message)

    def receive_messages(self, agent_id: str) -> list[AgentMessage]:
        """Poll and drain pending messages for an agent."""
        inbox = self._message_inbox.get(agent_id, [])
        self._message_inbox[agent_id] = []
        return inbox

    def terminate_subagent(self, agent_id: str, outcome: str = "completed") -> None:
        """Mark agent as completed and reclaim resources."""
        if agent_id in self._active_agents:
            self._active_agents[agent_id].status = outcome

    def active_count(self) -> int:
        return sum(1 for a in self._active_agents.values() if a.status == "running")

    def session_tree(self) -> dict[str, Any]:
        """Produce hierarchical trace of all spawned agents."""
        return {
            "total_spawned": len(self._active_agents),
            "running": self.active_count(),
            "agents": [a.to_dict() for a in self._active_agents.values()],
        }
