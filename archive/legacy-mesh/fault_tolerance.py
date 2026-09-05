"""Fault Tolerance — handle node failures and recovery."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FailureType(str, Enum):
    NODE_DOWN = "node_down"
    NETWORK_PARTITION = "network_partition"
    TIMEOUT = "timeout"
    CRASH = "crash"


class RecoveryAction(str, Enum):
    RESTART = "restart"
    MIGRATE = "migrate"
    RETRY = "retry"
    IGNORE = "ignore"


@dataclass
class FailureEvent:
    id: str
    node_id: str
    failure_type: FailureType
    detected_at: float = 0.0
    resolved: bool = False
    recovery_action: RecoveryAction | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class FaultTolerance:
    """Handle failures and recovery."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._failures: dict[str, FailureEvent] = {}
        self._strategies: dict[FailureType, RecoveryAction] = {}

    def detect(self, node_id: str, failure_type: FailureType) -> FailureEvent:
        event = FailureEvent(id=str(uuid.uuid4()), node_id=node_id, failure_type=failure_type)
        self._failures[event.id] = event
        return event

    def resolve(self, event_id: str, action: RecoveryAction) -> bool:
        if event_id in self._failures:
            self._failures[event_id].resolved = True
            self._failures[event_id].recovery_action = action
            return True
        return False

    def set_strategy(self, failure_type: FailureType, action: RecoveryAction) -> None:
        self._strategies[failure_type] = action

    def get_strategy(self, failure_type: FailureType) -> RecoveryAction | None:
        return self._strategies.get(failure_type)

    def get_failures(self, node_id: str | None = None) -> list[FailureEvent]:
        if node_id is None:
            return list(self._failures.values())
        return [f for f in self._failures.values() if f.node_id == node_id]

    def get_unresolved(self) -> list[FailureEvent]:
        return [f for f in self._failures.values() if not f.resolved]

    def count(self) -> int:
        return len(self._failures)
