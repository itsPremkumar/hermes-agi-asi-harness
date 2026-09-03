#!/usr/bin/env python3
"""
HERMES AGI/ASI HARNESS v7.0 — INTER-AGENT COMMUNICATION PROTOCOL
=================================================================
Structured message passing, pub/sub channels, priority queuing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes_protocol")


class MessagePriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MessageType(str, Enum):
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    EVENT = "event"
    COMMAND = "command"
    QUERY = "query"


@dataclass
class Message:
    """An inter-agent message."""
    message_id: str
    sender_id: str
    receiver_id: str
    message_type: MessageType
    content: Any
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class CommunicationProtocol:
    """
    Inter-agent communication protocol.
    
    Features:
    - Structured message passing
    - Request/response patterns
    - Publish/subscribe channels
    - Broadcast and multicast
    - Priority queuing
    - Message persistence and replay
    """
    
    def __init__(self):
        self._message_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._channels: dict[str, list[str]] = {}  # channel -> agent_ids
        self._message_log: list[Message] = []
        self._handlers: dict[MessageType, list[Callable]] = {}
    
    async def send(self, sender: str, receiver: str, content: Any,
                   msg_type: MessageType = MessageType.REQUEST,
                   priority: MessagePriority = MessagePriority.NORMAL) -> str:
        """Send a message."""
        msg = Message(
            message_id=str(uuid.uuid4()),
            sender_id=sender,
            receiver_id=receiver,
            message_type=msg_type,
            content=content,
            priority=priority
        )
        
        priority_value = {
            MessagePriority.LOW: 3,
            MessagePriority.NORMAL: 2,
            MessagePriority.HIGH: 1,
            MessagePriority.CRITICAL: 0
        }[priority]
        
        await self._message_queue.put((priority_value, msg))
        self._message_log.append(msg)
        
        return msg.message_id
    
    async def broadcast(self, sender: str, content: Any,
                        msg_type: MessageType = MessageType.BROADCAST) -> str:
        """Broadcast to all agents."""
        msg = Message(
            message_id=str(uuid.uuid4()),
            sender_id=sender,
            receiver_id="*",
            message_type=msg_type,
            content=content
        )
        
        self._message_log.append(msg)
        return msg.message_id
    
    async def subscribe(self, agent_id: str, channel: str):
        """Subscribe to a channel."""
        if channel not in self._channels:
            self._channels[channel] = []
        self._channels[channel].append(agent_id)
    
    async def publish(self, channel: str, content: Any, sender: str = "system"):
        """Publish to a channel."""
        if channel in self._channels:
            for agent_id in self._channels[channel]:
                await self.send(sender, agent_id, content, MessageType.EVENT)
    
    async def process_messages(self, timeout: float = 0.1) -> list[Message]:
        """Process messages from the queue."""
        messages = []
        try:
            while True:
                _priority, msg = await asyncio.wait_for(
                    self._message_queue.get(), timeout=timeout
                )
                messages.append(msg)
        except asyncio.TimeoutError:
            pass
        
        return messages
    
    def register_handler(self, msg_type: MessageType, handler: Callable):
        """Register a message handler."""
        if msg_type not in self._handlers:
            self._handlers[msg_type] = []
        self._handlers[msg_type].append(handler)
    
    def get_message_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get message history."""
        return [
            {
                "id": msg.message_id,
                "sender": msg.sender_id,
                "receiver": msg.receiver_id,
                "type": msg.message_type.value,
                "priority": msg.priority.value,
                "timestamp": msg.timestamp
            }
            for msg in self._message_log[-limit:]
        ]
    
    async def health(self) -> dict[str, Any]:
        """Health check."""
        return {
            "status": "healthy",
            "queue_size": self._message_queue.qsize(),
            "channels": len(self._channels),
            "total_messages": len(self._message_log)
        }
