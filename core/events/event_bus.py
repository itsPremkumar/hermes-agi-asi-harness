
"""
Event Bus — the central nervous system of Hermes.

All communication between plugins goes through the event bus.
This enables: replay, debugging, observability, auditing, recovery.

Extracted & enhanced from:
- agi-hermes-advanced-master: event_bus.py
- hermes-agent: monitoring/events.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    # Kernel events
    KERNEL_BOOT = "kernel.booted"
    KERNEL_SHUTDOWN = "kernel.shutdown"
    KERNEL_ERROR = "kernel.error"
    
    # Task events
    TASK_SUBMITTED = "task.submitted"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    
    # Agent events
    AGENT_SPAWNED = "agent.spawned"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    AGENT_STEP_START = "agent.step_start"
    AGENT_STEP_END = "agent.step_end"
    
    # Tool events
    TOOL_REQUESTED = "tool.requested"
    TOOL_APPROVED = "tool.approved"
    TOOL_EXECUTED = "tool.executed"
    TOOL_FAILED = "tool.failed"
    TOOL_PRE_EXECUTE = "tool.pre_execute"
    TOOL_POST_EXECUTE = "tool.post_execute"
    
    # Memory events
    MEMORY_FORMED = "memory.formed"
    MEMORY_RETRIEVED = "memory.retrieved"
    MEMORY_CONSOLIDATED = "memory.consolidated"
    
    # Verification events
    VERIFICATION_STARTED = "verification.started"
    VERIFICATION_PASSED = "verification.passed"
    VERIFICATION_FAILED = "verification.failed"
    
    # Recovery events
    RECOVERY_STARTED = "recovery.started"
    RECOVERY_COMPLETED = "recovery.completed"
    
    # Evolution events
    EVOLUTION_CANDIDATE = "evolution.candidate"
    EVOLUTION_PROMOTED = "evolution.promoted"
    EVOLUTION_REJECTED = "evolution.rejected"
    
    # Ecosystem events
    ECOSYSTEM_DISCOVERY = "ecosystem.discovery"
    ECOSYSTEM_INTEGRATION = "ecosystem.integration"
    
    # Security events
    SECURITY_VIOLATION = "security.violation"
    PERMISSION_DENIED = "permission.denied"


@dataclass
class Event:
    """An event in the system."""
    type: str
    data: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = "kernel"
    parent_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "parent_id": self.parent_id,
        }


class EventBus:
    """
    Central event bus for all inter-plugin communication.
    
    Supports:
    - Pub/sub event routing
    - Event persistence for replay
    - Event filtering and transformation
    - Dead letter queue for failed handlers
    - Wildcard subscriptions
    """
    
    def __init__(self, kernel: Any = None, persist_path: Optional[Path] = None):
        self.kernel = kernel
        self.persist_path = persist_path
        self._subscribers: Dict[str, List[Callable[[Event], Awaitable[None]]]] = defaultdict(list)
        self._event_log: List[Event] = []
        self._running = False
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._dead_letter: List[Event] = []
    
    async def start(self):
        """Start the event bus."""
        self._running = True
        asyncio.create_task(self._process_events())
        logger.info("Event bus started")
    
    async def stop(self):
        """Stop the event bus."""
        self._running = False
        logger.info("Event bus stopped")
    
    async def emit(self, event_type: str, data: Dict[str, Any], source: str = "kernel"):
        """Emit an event."""
        event = Event(type=event_type, data=data, source=source)
        await self._queue.put(event)
        
        # Persist if configured
        if self.persist_path:
            self._persist_event(event)
    
    def subscribe(self, event_type: str, handler: Callable[[Event], Awaitable[None]]):
        """Subscribe to events of a given type. Use '*' for wildcard."""
        self._subscribers[event_type].append(handler)
    
    def unsubscribe(self, event_type: str, handler: Callable[[Event], Awaitable[None]]):
        """Unsubscribe from events."""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)
    
    async def _process_events(self):
        """Main event processing loop."""
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                self._event_log.append(event)
                
                # Route to type-specific subscribers
                handlers = self._subscribers.get(event.type, [])
                for handler in handlers:
                    try:
                        await handler(event)
                    except Exception as e:
                        logger.error("Event handler error (%s): %s", event.type, e)
                        self._dead_letter.append(event)
                
                # Also route to wildcard subscribers
                wildcard_handlers = self._subscribers.get("*", [])
                for handler in wildcard_handlers:
                    try:
                        await handler(event)
                    except Exception as e:
                        logger.error("Wildcard handler error: %s", e)
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Event processing error: %s", e)
    
    def _persist_event(self, event: Event):
        """Persist event to disk."""
        try:
            with open(self.persist_path, "a") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
        except Exception as e:
            logger.warning("Failed to persist event: %s", e)
    
    def get_event_log(self, event_type: Optional[str] = None, limit: int = 100) -> List[Event]:
        """Get event log, optionally filtered by type."""
        events = self._event_log
        if event_type:
            events = [e for e in events if e.type == event_type]
        return events[-limit:]
    
    async def replay(self, event_type: Optional[str] = None):
        """Replay events from the log."""
        events = self._event_log
        if event_type:
            events = [e for e in events if e.type == event_type]
        
        for event in events:
            handlers = self._subscribers.get(event.type, [])
            for handler in handlers:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error("Replay handler error: %s", e)
    
    async def health(self) -> Dict[str, Any]:
        return {
            "status": "healthy" if self._running else "stopped",
            "subscribers": {k: len(v) for k, v in self._subscribers.items()},
            "event_log_size": len(self._event_log),
            "dead_letter_size": len(self._dead_letter),
            "queue_size": self._queue.qsize(),
        }


async def create(kernel: Any) -> EventBus:
    """Factory function for the event bus."""
    persist_path = None
    if kernel and hasattr(kernel, 'config'):
        persist_path = kernel.config.state_path / "events.jsonl"
    bus = EventBus(kernel=kernel, persist_path=persist_path)
    return bus
