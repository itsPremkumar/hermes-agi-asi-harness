"""
Universal Action Protocol (UAP) + Action Algebra.

Normalizes all actions into composable primitives:
READ, CREATE, UPDATE, DELETE, MOVE, COPY, SEND, EXECUTE, APPROVE, REJECT,
SEARCH, TRANSFORM, OBSERVE, WAIT, SUBSCRIBE
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ActionType(str, Enum):
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MOVE = "move"
    COPY = "copy"
    SEND = "send"
    EXECUTE = "execute"
    APPROVE = "approve"
    REJECT = "reject"
    SEARCH = "search"
    TRANSFORM = "transform"
    OBSERVE = "observe"
    WAIT = "wait"
    SUBSCRIBE = "subscribe"


class ActionStatus(str, Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    SIMULATING = "simulating"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    COMPENSATED = "compensated"


@dataclass
class Action:
    id: str
    type: ActionType
    target: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: ActionStatus = ActionStatus.PENDING
    parent_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    consequences: List[str] = field(default_factory=list)  # action IDs this causes
    invalidates: List[str] = field(default_factory=list)  # action IDs this invalidates
    enables: List[str] = field(default_factory=list)      # action IDs this enables
    blocks: List[str] = field(default_factory=list)       # action IDs this blocks
    reversibility: str = "high"
    compensation_action: Optional[str] = None
    requires_approval: bool = False
    risk_score: float = 0.0
    created_at: float = field(default_factory=time.time)
    executed_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    error: Optional[str] = None


@dataclass
class ActionEvent:
    id: str
    type: str  # created, updated, deleted, failed, completed, expired, changed, alert
    source: str
    timestamp: float
    payload: Dict[str, Any]
    affected_resources: List[str] = field(default_factory=list)


class UniversalActionProtocol:
    """
    Universal Action Protocol — normalize all actions into composable primitives.
    
    Drivers translate universal actions into app-specific operations.
    The core executive sees environment-neutral primitives.
    """

    # Action type categories
    READ_TYPES = {ActionType.READ, ActionType.SEARCH, ActionType.OBSERVE}
    WRITE_TYPES = {ActionType.CREATE, ActionType.UPDATE, ActionType.DELETE}
    FLOW_TYPES = {ActionType.MOVE, ActionType.COPY, ActionType.SEND}
    CONTROL_TYPES = {ActionType.EXECUTE, ActionType.APPROVE, ActionType.REJECT}
    META_TYPES = {ActionType.WAIT, ActionType.SUBSCRIBE, ActionType.TRANSFORM}

    def __init__(self):
        self.actions: Dict[str, Action] = {}
        self.events: List[ActionEvent] = []
        self._action_graph: Dict[str, List[str]] = {}  # action_id → dependent action ids

    # ── Action Creation ────────────────────────────────────────────────────

    def create_action(
        self,
        type: ActionType,
        target: str,
        parameters: Dict[str, Any] = None,
        parent_id: str = None,
        dependencies: List[str] = None,
    ) -> Action:
        action = Action(
            id=str(uuid.uuid4()),
            type=type,
            target=target,
            parameters=parameters or {},
            parent_id=parent_id,
            dependencies=dependencies or [],
        )
        self.actions[action.id] = action
        
        # Register in action graph
        if parent_id and parent_id in self.actions:
            if parent_id not in self._action_graph:
                self._action_graph[parent_id] = []
            self._action_graph[parent_id].append(action.id)
        
        return action

    def get_action(self, action_id: str) -> Optional[Action]:
        return self.actions.get(action_id)

    # ── Action Graph ───────────────────────────────────────────────────────

    def link_actions(self, source_id: str, target_id: str, relation: str):
        """Link two actions with a causal/temporal relationship."""
        source = self.actions.get(source_id)
        target = self.actions.get(target_id)
        if not source or not target:
            return
        
        if relation == "causes":
            source.consequences.append(target_id)
        elif relation == "invalidates":
            source.invalidates.append(target_id)
        elif relation == "enables":
            source.enables.append(target_id)
        elif relation == "blocks":
            source.blocks.append(target_id)

    def get_causal_chain(self, action_id: str) -> List[str]:
        """Get all actions causally downstream of the given action."""
        chain = []
        to_process = [action_id]
        visited = set()
        while to_process:
            current = to_process.pop(0)
            if current in visited:
                continue
            visited.add(current)
            action = self.actions.get(current)
            if action:
                chain.extend(action.consequences)
                to_process.extend(action.consequences)
        return chain

    def get_blocked_actions(self, action_id: str) -> List[str]:
        """Get all actions blocked by the given action."""
        action = self.actions.get(action_id)
        if not action:
            return []
        return list(action.blocks)

    # ── Event Model ───────────────────────────────────────────────────────

    def emit_event(self, type: str, source: str, payload: Dict[str, Any],
                   affected_resources: List[str] = None) -> ActionEvent:
        event = ActionEvent(
            id=str(uuid.uuid4()),
            type=type,
            source=source,
            timestamp=time.time(),
            payload=payload,
            affected_resources=affected_resources or [],
        )
        self.events.append(event)
        return event

    def get_events_for_resource(self, resource: str) -> List[ActionEvent]:
        return [e for e in self.events if resource in e.affected_resources]

    def get_events_by_type(self, event_type: str) -> List[ActionEvent]:
        return [e for e in self.events if e.type == event_type]

    # ── Action Composition ─────────────────────────────────────────────────

    def compose(self, *actions: Action, mode: str = "sequence") -> List[Action]:
        """Compose multiple actions into a sequence or parallel batch."""
        if mode == "sequence":
            for i in range(len(actions) - 1):
                self.link_actions(actions[i].id, actions[i + 1].id, "enables")
            return list(actions)
        elif mode == "parallel":
            # Parallel actions have no dependencies
            return list(actions)
        return list(actions)

    # ── Action Algebra Operations ──────────────────────────────────────────

    def is_read(self, action: Action) -> bool:
        return action.type in self.READ_TYPES

    def is_write(self, action: Action) -> bool:
        return action.type in self.WRITE_TYPES

    def is_safe(self, action: Action) -> bool:
        """A safe action is read-only and reversible."""
        return action.type in self.READ_TYPES and action.reversibility == "high"

    def get_risk_level(self, action: Action) -> str:
        if action.risk_score < 0.2:
            return "low"
        elif action.risk_score < 0.5:
            return "medium"
        elif action.risk_score < 0.8:
            return "high"
        return "critical"

    # ── Query & Summary ────────────────────────────────────────────────────

    def get_state(self) -> Dict[str, Any]:
        status_counts = {}
        for action in self.actions.values():
            status_counts[action.status.value] = status_counts.get(action.status.value, 0) + 1
        return {
            "total_actions": len(self.actions),
            "total_events": len(self.events),
            "status_counts": status_counts,
            "graph_edges": sum(len(v) for v in self._action_graph.values()),
        }

    def get_pending_actions(self) -> List[Action]:
        return [a for a in self.actions.values() if a.status == ActionStatus.PENDING]

    def get_actions_by_type(self, action_type: ActionType) -> List[Action]:
        return [a for a in self.actions.values() if a.type == action_type]
