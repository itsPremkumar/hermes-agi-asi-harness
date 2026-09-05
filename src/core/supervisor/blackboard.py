"""Engineering Blackboard + Event Bus.

Blackboard: Current knowledge (what is true now)
Event Bus: What just happened (what changed)

Combined flow:
    EVENT → BLACKBOARD UPDATE → SUPERVISOR REASONING → ACTION
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# Event Bus
# ---------------------------------------------------------------------------

class EventType(str, Enum):
    """Types of events in the system."""
    # Mission events
    MISSION_CREATED = "mission_created"
    MISSION_COMPLETED = "mission_completed"
    MISSION_FAILED = "mission_failed"
    MISSION_REPLANNED = "mission_replanned"

    # Task events
    TASK_CREATED = "task_created"
    TASK_READY = "task_ready"
    TASK_ASSIGNED = "task_assigned"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_BLOCKED = "task_blocked"
    TASK_VERIFIED = "task_verified"

    # Worker events
    WORKER_CREATED = "worker_created"
    WORKER_STARTED = "worker_started"
    WORKER_PROGRESS = "worker_progress"
    WORKER_BLOCKED = "worker_blocked"
    WORKER_FAILED = "worker_failed"
    WORKER_STALLED = "worker_stalled"
    WORKER_COMPLETED = "worker_completed"

    # Artifact events
    ARTIFACT_CREATED = "artifact_created"
    COMMIT_CREATED = "commit_created"
    TEST_PASSED = "test_passed"
    TEST_FAILED = "test_failed"
    MERGE_READY = "merge_ready"
    MERGE_DONE = "merge_done"

    # Verification events
    VERIFICATION_PASSED = "verification_passed"
    VERIFICATION_FAILED = "verification_failed"

    # System events
    STAGNATION_DETECTED = "stagnation_detected"
    INTERVENTION = "intervention"
    REPLAN = "replan"
    CHECKPOINT = "checkpoint"


@dataclass
class Event:
    """An event in the system."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: EventType = EventType.MISSION_CREATED
    source: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class EventBus:
    """Event bus for publishing and subscribing to events."""

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._history: List[Event] = []

    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        """Subscribe to an event type."""
        self._subscribers.setdefault(event_type, []).append(callback)

    def publish(self, event: Event) -> None:
        """Publish an event."""
        self._history.append(event)
        # Notify subscribers
        for callback in self._subscribers.get(event.type, []):
            try:
                callback(event)
            except Exception:
                pass

    def get_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100,
    ) -> List[Event]:
        """Get event history."""
        events = self._history
        if event_type:
            events = [e for e in events if e.type == event_type]
        return events[-limit:]

    def get_latest(self, event_type: Optional[EventType] = None) -> Optional[Event]:
        """Get the latest event."""
        events = self.get_history(event_type, limit=1)
        return events[0] if events else None


# ---------------------------------------------------------------------------
# Engineering Blackboard
# ---------------------------------------------------------------------------

@dataclass
class BlackboardEntry:
    """An entry on the blackboard."""
    key: str = ""
    value: Any = None
    source: str = ""
    timestamp: float = field(default_factory=time.time)
    confidence: float = 1.0


class EngineeringBlackboard:
    """Shared knowledge between Supervisor and Hermes workers."""

    def __init__(self):
        self._entries: Dict[str, BlackboardEntry] = {}

    def write(self, key: str, value: Any, source: str = "", confidence: float = 1.0) -> None:
        """Write to the blackboard."""
        self._entries[key] = BlackboardEntry(
            key=key,
            value=value,
            source=source,
            confidence=confidence,
        )

    def read(self, key: str) -> Optional[Any]:
        """Read from the blackboard."""
        entry = self._entries.get(key)
        return entry.value if entry else None

    def get_entry(self, key: str) -> Optional[BlackboardEntry]:
        """Get full entry with metadata."""
        return self._entries.get(key)

    def search(self, prefix: str = "") -> Dict[str, Any]:
        """Search entries by prefix."""
        return {
            k: v.value for k, v in self._entries.items()
            if k.startswith(prefix)
        }

    def get_all(self) -> Dict[str, Any]:
        """Get all entries."""
        return {k: v.value for k, v in self._entries.items()}

    def get_state_summary(self) -> Dict[str, Any]:
        """Get a summary of the blackboard state."""
        return {
            "total_entries": len(self._entries),
            "keys": list(self._entries.keys()),
        }


# ---------------------------------------------------------------------------
# Combined Blackboard + Event Bus
# ---------------------------------------------------------------------------

class BlackboardEventSystem:
    """Combines blackboard and event bus."""

    def __init__(self):
        self._event_bus = EventBus()
        self._blackboard = EngineeringBlackboard()

        # Auto-update blackboard on events
        self._event_bus.subscribe(EventType.MISSION_CREATED, self._on_mission_created)
        self._event_bus.subscribe(EventType.TASK_COMPLETED, self._on_task_completed)
        self._event_bus.subscribe(EventType.WORKER_PROGRESS, self._on_worker_progress)
        self._event_bus.subscribe(EventType.ARTIFACT_CREATED, self._on_artifact_created)
        self._event_bus.subscribe(EventType.TEST_PASSED, self._on_test_passed)
        self._event_bus.subscribe(EventType.TEST_FAILED, self._on_test_failed)
        self._event_bus.subscribe(EventType.STAGNATION_DETECTED, self._on_stagnation)

    @property
    def events(self) -> EventBus:
        return self._event_bus

    @property
    def blackboard(self) -> EngineeringBlackboard:
        return self._blackboard

    def publish(self, event_type: EventType, source: str = "", data: Dict[str, Any] = None) -> Event:
        """Publish an event."""
        event = Event(
            type=event_type,
            source=source,
            data=data or {},
        )
        self._event_bus.publish(event)
        return event

    # --- Event handlers ---

    def _on_mission_created(self, event: Event) -> None:
        self._blackboard.write("current_mission", event.data, source="event_bus")

    def _on_task_completed(self, event: Event) -> None:
        task_id = event.data.get("task_id", "")
        self._blackboard.write(f"task.{task_id}.status", "completed", source="event_bus")

    def _on_worker_progress(self, event: Event) -> None:
        worker_id = event.data.get("worker_id", "")
        progress = event.data.get("progress", 0)
        self._blackboard.write(f"worker.{worker_id}.progress", progress, source="event_bus")

    def _on_artifact_created(self, event: Event) -> None:
        artifact = event.data.get("artifact", "")
        self._blackboard.write(f"artifact.{artifact}", event.data, source="event_bus")

    def _on_test_passed(self, event: Event) -> None:
        test_id = event.data.get("test_id", "")
        self._blackboard.write(f"test.{test_id}", "passed", source="event_bus")

    def _on_test_failed(self, event: Event) -> None:
        test_id = event.data.get("test_id", "")
        self._blackboard.write(f"test.{test_id}", "failed", source="event_bus")

    def _on_stagnation(self, event: Event) -> None:
        worker_id = event.data.get("worker_id", "")
        self._blackboard.write(f"worker.{worker_id}.stagnation", event.data, source="event_bus")

    def get_status(self) -> Dict[str, Any]:
        """Get system status."""
        return {
            "events": len(self._event_bus._history),
            "blackboard": self._blackboard.get_state_summary(),
        }
