"""
Agent Communication Contract — Section 29 of v7 spec

Agents communicate through structured envelopes.
Free-form conversation remains possible inside an agent, but cross-agent state transitions should be structured.
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentMessage:
    """Structured agent-to-agent message envelope."""
    task_id: str
    sender: str
    receiver: str
    message_type: str  # result, request, handoff, review, alert
    status: str = "pending"  # pending, processing, complete, failed
    artifact_refs: list[str] = field(default_factory=list)
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    payload: dict[str, Any] = field(default_factory=dict)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "task_id": self.task_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type,
            "status": self.status,
            "artifact_refs": self.artifact_refs,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "limitations": self.limitations,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }


class AgentCommunicationBus:
    """Structured inter-agent messaging."""

    def __init__(self):
        self._messages: list[AgentMessage] = []
        self._inboxes: dict[str, list[AgentMessage]] = {}
        self._handlers: dict[str, Any] = {}

    def send(self, message: AgentMessage):
        """Send a structured message."""
        self._messages.append(message)
        
        # Route to receiver inbox
        if message.receiver not in self._inboxes:
            self._inboxes[message.receiver] = []
        self._inboxes[message.receiver].append(message)
        
        logger.debug(f"Message: {message.sender} -> {message.receiver} ({message.message_type})")

    def get_inbox(self, agent_id: str, limit: int = 10) -> list[AgentMessage]:
        """Get messages for an agent."""
        return self._inboxes.get(agent_id, [])[-limit:]

    def get_messages(
        self,
        task_id: str | None = None,
        sender: str | None = None,
        receiver: str | None = None,
        message_type: str | None = None,
        limit: int = 50,
    ) -> list[AgentMessage]:
        """Query messages with filters."""
        results = self._messages
        if task_id:
            results = [m for m in results if m.task_id == task_id]
        if sender:
            results = [m for m in results if m.sender == sender]
        if receiver:
            results = [m for m in results if m.receiver == receiver]
        if message_type:
            results = [m for m in results if m.message_type == message_type]
        return results[-limit:]

    def create_handoff(
        self,
        task_id: str,
        from_agent: str,
        to_agent: str,
        artifact_refs: list[str],
        context: dict[str, Any],
    ) -> AgentMessage:
        """Create a structured handoff message."""
        return AgentMessage(
            task_id=task_id,
            sender=from_agent,
            receiver=to_agent,
            message_type="handoff",
            artifact_refs=artifact_refs,
            payload={"context": context},
        )

    def create_review_request(
        self,
        task_id: str,
        from_agent: str,
        to_agent: str,
        artifact_refs: list[str],
    ) -> AgentMessage:
        """Create a review request."""
        return AgentMessage(
            task_id=task_id,
            sender=from_agent,
            receiver=to_agent,
            message_type="review",
            artifact_refs=artifact_refs,
        )

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_messages": len(self._messages),
            "agents": len(self._inboxes),
            "by_type": {
                mtype: sum(1 for m in self._messages if m.message_type == mtype)
                for mtype in {m.message_type for m in self._messages}
            },
        }


class AgentCommunicationPlugin:
    def __init__(self):
        self.bus = AgentCommunicationBus()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {"status": "healthy", **self.bus.get_stats()}

    async def send(self, **kwargs):
        msg = AgentMessage(**kwargs)
        self.bus.send(msg)
        return msg

    async def get_inbox(self, agent_id: str):
        return self.bus.get_inbox(agent_id)


async def create(kernel=None):
    plugin = AgentCommunicationPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
