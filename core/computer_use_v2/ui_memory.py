"""
UI State Memory — Remember navigation patterns for frequently used applications.

For frequently used applications:
  Google Calendar → learn UI structure → remember navigation patterns

Store: element, location, semantic role, interaction method, success rate, state transitions
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class UIElementMemory:
    """Remembered UI element."""
    id: str
    app_name: str
    element_label: str
    element_type: str
    typical_location: tuple  # (x, y)
    semantic_role: str  # e.g., "submit_button", "navigation_menu"
    interaction_method: str  # click, type, hover, etc.
    success_count: int = 0
    failure_count: int = 0
    last_used: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NavigationPattern:
    """A remembered sequence of UI interactions."""
    id: str
    app_name: str
    name: str  # e.g., "create_new_event"
    steps: List[Dict[str, Any]]  # [{action, element_label, expected_state}]
    success_count: int = 0
    failure_count: int = 0
    average_time_ms: float = 0.0
    last_used: float = 0.0


class UIStateMemory:
    """Remember UI patterns across sessions."""

    def __init__(self):
        self.elements: Dict[str, UIElementMemory] = {}  # element_id → memory
        self.patterns: Dict[str, NavigationPattern] = {}  # pattern_id → pattern
        self._app_elements: Dict[str, List[str]] = {}  # app_name → [element_ids]
        self._app_patterns: Dict[str, List[str]] = {}  # app_name → [pattern_ids]

    def remember_element(self, app_name: str, element_label: str,
                         element_type: str, location: tuple,
                         semantic_role: str, interaction_method: str,
                         metadata: Dict[str, Any] = None) -> UIElementMemory:
        mem = UIElementMemory(
            id=str(uuid.uuid4()),
            app_name=app_name,
            element_label=element_label,
            element_type=element_type,
            typical_location=location,
            semantic_role=semantic_role,
            interaction_method=interaction_method,
            last_used=time.time(),
            metadata=metadata or {},
        )
        self.elements[mem.id] = mem
        
        if app_name not in self._app_elements:
            self._app_elements[app_name] = []
        self._app_elements[app_name].append(mem.id)
        
        return mem

    def remember_pattern(self, app_name: str, name: str,
                         steps: List[Dict[str, Any]]) -> NavigationPattern:
        pattern = NavigationPattern(
            id=str(uuid.uuid4()),
            app_name=app_name,
            name=name,
            steps=steps,
            last_used=time.time(),
        )
        self.patterns[pattern.id] = pattern
        
        if app_name not in self._app_patterns:
            self._app_patterns[app_name] = []
        self._app_patterns[app_name].append(pattern.id)
        
        return pattern

    def find_element(self, app_name: str, semantic_role: str) -> Optional[UIElementMemory]:
        """Find a remembered element by semantic role."""
        element_ids = self._app_elements.get(app_name, [])
        for eid in element_ids:
            elem = self.elements.get(eid)
            if elem and elem.semantic_role == semantic_role:
                return elem
        return None

    def find_pattern(self, app_name: str, name: str) -> Optional[NavigationPattern]:
        """Find a remembered navigation pattern."""
        pattern_ids = self._app_patterns.get(app_name, [])
        for pid in pattern_ids:
            pattern = self.patterns.get(pid)
            if pattern and pattern.name == name:
                return pattern
        return None

    def record_element_usage(self, element_id: str, success: bool):
        elem = self.elements.get(element_id)
        if elem:
            if success:
                elem.success_count += 1
            else:
                elem.failure_count += 1
            elem.last_used = time.time()

    def record_pattern_usage(self, pattern_id: str, success: bool, time_ms: float):
        pattern = self.patterns.get(pattern_id)
        if pattern:
            if success:
                pattern.success_count += 1
            else:
                pattern.failure_count += 1
            total = pattern.success_count + pattern.failure_count
            pattern.average_time_ms = (pattern.average_time_ms * (total - 1) + time_ms) / total
            pattern.last_used = time.time()

    def get_best_element(self, app_name: str, semantic_role: str) -> Optional[UIElementMemory]:
        """Get the most reliable element for a semantic role."""
        element_ids = self._app_elements.get(app_name, [])
        candidates = []
        for eid in element_ids:
            elem = self.elements.get(eid)
            if elem and elem.semantic_role == semantic_role:
                candidates.append(elem)
        
        if not candidates:
            return None
        
        def reliability(elem: UIElementMemory) -> float:
            total = elem.success_count + elem.failure_count
            if total == 0:
                return 0.5
            return elem.success_count / total
        
        return max(candidates, key=reliability)

    def get_state(self) -> Dict[str, Any]:
        return {
            "elements": len(self.elements),
            "patterns": len(self.patterns),
            "apps": len(self._app_elements),
        }
