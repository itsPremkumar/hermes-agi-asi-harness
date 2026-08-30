"""
UI State Graph — Model application UI as a state machine.

MISSION → APP MODEL → UI STATE GRAPH → SUBGOAL → ELEMENT TARGET → ACTION → OBSERVE → STATE TRANSITION

The agent learns: screen state A → action → screen state B
rather than treating every screenshot as an isolated image.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class UIElementType(str, Enum):
    BUTTON = "button"
    TEXT_FIELD = "text_field"
    DROPDOWN = "dropdown"
    CHECKBOX = "checkbox"
    LINK = "link"
    IMAGE = "image"
    MENU = "menu"
    DIALOG = "dialog"
    TABLE = "table"
    UNKNOWN = "unknown"


@dataclass
class UIElement:
    id: str
    element_type: UIElementType
    label: str
    location: Tuple[int, int]  # x, y
    size: Tuple[int, int]  # width, height
    enabled: bool = True
    visible: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UIState:
    id: str
    name: str
    elements: List[UIElement]
    screenshot_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class StateTransition:
    id: str
    from_state_id: str
    to_state_id: str
    action: Dict[str, Any]
    element_target: Optional[str] = None
    success_count: int = 0
    failure_count: int = 0
    average_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class UIStateGraph:
    """
    Model an application's UI as a graph of states and transitions.
    
    Enables the agent to:
    - Know what screen state it's in
    - Plan multi-step UI navigation
    - Learn from successful/failed transitions
    """

    def __init__(self, app_name: str):
        self.app_name = app_name
        self.states: Dict[str, UIState] = {}
        self.transitions: List[StateTransition] = []
        self.current_state: Optional[str] = None

    def add_state(self, name: str, elements: List[UIElement] = None,
                  screenshot_path: str = None, metadata: Dict[str, Any] = None) -> UIState:
        state = UIState(
            id=str(uuid.uuid4()),
            name=name,
            elements=elements or [],
            screenshot_path=screenshot_path,
            metadata=metadata or {},
        )
        self.states[state.id] = state
        return state

    def add_transition(self, from_state_id: str, to_state_id: str,
                       action: Dict[str, Any], element_target: str = None) -> StateTransition:
        transition = StateTransition(
            id=str(uuid.uuid4()),
            from_state_id=from_state_id,
            to_state_id=to_state_id,
            action=action,
            element_target=element_target,
        )
        self.transitions.append(transition)
        return transition

    def record_transition(self, transition_id: str, success: bool, time_ms: float):
        for t in self.transitions:
            if t.id == transition_id:
                if success:
                    t.success_count += 1
                else:
                    t.failure_count += 1
                # Update running average
                total = t.success_count + t.failure_count
                t.average_time_ms = (t.average_time_ms * (total - 1) + time_ms) / total
                break

    def get_transitions_from(self, state_id: str) -> List[StateTransition]:
        return [t for t in self.transitions if t.from_state_id == state_id]

    def get_transitions_to(self, state_id: str) -> List[StateTransition]:
        return [t for t in self.transitions if t.to_state_id == state_id]

    def find_path(self, from_state_id: str, to_state_id: str) -> List[StateTransition]:
        """Find a path between states using BFS."""
        if from_state_id == to_state_id:
            return []
        
        visited = {from_state_id}
        queue = [(from_state_id, [])]
        
        while queue:
            current, path = queue.pop(0)
            for transition in self.get_transitions_from(current):
                next_state = transition.to_state_id
                new_path = path + [transition]
                
                if next_state == to_state_id:
                    return new_path
                
                if next_state not in visited:
                    visited.add(next_state)
                    queue.append((next_state, new_path))
        
        return []  # No path found

    def get_best_transition(self, from_state_id: str) -> Optional[StateTransition]:
        """Get the most reliable transition from a state."""
        transitions = self.get_transitions_from(from_state_id)
        if not transitions:
            return None
        
        def reliability(t: StateTransition) -> float:
            total = t.success_count + t.failure_count
            if total == 0:
                return 0.5
            return t.success_count / total
        
        return max(transitions, key=reliability)

    def get_state(self) -> Dict[str, Any]:
        return {
            "app_name": self.app_name,
            "states": len(self.states),
            "transitions": len(self.transitions),
            "current_state": self.current_state,
        }
