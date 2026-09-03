"""
Application Digital Twin — Model for frequently used systems.

REAL APPLICATION ↔ DIGITAL REPRESENTATION

The model contains: entities, screens, actions, states, permissions,
workflows, failure modes.

Hermes can reason against the model before acting against reality.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TwinEntity:
    id: str
    name: str
    type: str
    state: dict[str, Any] = field(default_factory=dict)
    actions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TwinScreen:
    id: str
    name: str
    elements: list[dict[str, Any]] = field(default_factory=list)
    actions_available: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TwinWorkflow:
    id: str
    name: str
    steps: list[dict[str, Any]]
    preconditions: list[str] = field(default_factory=list)
    postconditions: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)


@dataclass
class TwinFailureMode:
    id: str
    name: str
    trigger: str
    effect: str
    recovery: str
    probability: float = 0.1


class ApplicationDigitalTwin:
    """
    Digital representation of a real application.
    
    Hermes can:
    - Reason about the application without touching it
    - Plan workflows before executing them
    - Predict failure modes
    - Simulate actions safely
    """

    def __init__(self, app_name: str, app_type: str = "generic"):
        self.app_name = app_name
        self.app_type = app_type
        self.id = str(uuid.uuid4())
        self.entities: dict[str, TwinEntity] = {}
        self.screens: dict[str, TwinScreen] = {}
        self.workflows: dict[str, TwinWorkflow] = {}
        self.failure_modes: dict[str, TwinFailureMode] = {}
        self.permissions: dict[str, list[str]] = {}  # role → [actions]
        self.metadata: dict[str, Any] = {
            "created_at": time.time(),
            "version": "1.0",
        }

    def add_entity(self, name: str, type: str, state: dict[str, Any] | None = None,
                   actions: list[str] | None = None) -> TwinEntity:
        entity = TwinEntity(
            id=str(uuid.uuid4()),
            name=name,
            type=type,
            state=state or {},
            actions=actions or [],
        )
        self.entities[entity.id] = entity
        return entity

    def add_screen(self, name: str, elements: list[dict[str, Any]] | None = None,
                   actions_available: list[str] | None = None) -> TwinScreen:
        screen = TwinScreen(
            id=str(uuid.uuid4()),
            name=name,
            elements=elements or [],
            actions_available=actions_available or [],
        )
        self.screens[screen.id] = screen
        return screen

    def add_workflow(self, name: str, steps: list[dict[str, Any]],
                     preconditions: list[str] | None = None,
                     postconditions: list[str] | None = None,
                     failure_modes: list[str] | None = None) -> TwinWorkflow:
        workflow = TwinWorkflow(
            id=str(uuid.uuid4()),
            name=name,
            steps=steps,
            preconditions=preconditions or [],
            postconditions=postconditions or [],
            failure_modes=failure_modes or [],
        )
        self.workflows[workflow.id] = workflow
        return workflow

    def add_failure_mode(self, name: str, trigger: str, effect: str,
                         recovery: str, probability: float = 0.1) -> TwinFailureMode:
        fm = TwinFailureMode(
            id=str(uuid.uuid4()),
            name=name,
            trigger=trigger,
            effect=effect,
            recovery=recovery,
            probability=probability,
        )
        self.failure_modes[fm.id] = fm
        return fm

    def simulate_action(self, action: str, target: str,
                        context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Simulate an action against the digital twin."""
        result = {
            "action": action,
            "target": target,
            "success": True,
            "predicted_state_changes": {},
            "potential_failures": [],
        }

        # Check if action is valid for target
        entity = None
        for e in self.entities.values():
            if e.name == target or e.id == target:
                entity = e
                break

        if entity:
            if action not in entity.actions:
                result["success"] = False
                result["error"] = f"Action '{action}' not available for entity '{target}'"
            else:
                result["predicted_state_changes"] = {action: "completed"}

        # Check for potential failures
        for fm in self.failure_modes.values():
            if fm.trigger in action or (context and fm.trigger in str(context)):
                result["potential_failures"].append({
                    "name": fm.name,
                    "effect": fm.effect,
                    "recovery": fm.recovery,
                    "probability": fm.probability,
                })

        return result

    def get_workflow(self, name: str) -> TwinWorkflow | None:
        for w in self.workflows.values():
            if w.name == name:
                return w
        return None

    def get_entity(self, name: str) -> TwinEntity | None:
        for e in self.entities.values():
            if e.name == name:
                return e
        return None

    def get_state(self) -> dict[str, Any]:
        return {
            "app_name": self.app_name,
            "app_type": self.app_type,
            "entities": len(self.entities),
            "screens": len(self.screens),
            "workflows": len(self.workflows),
            "failure_modes": len(self.failure_modes),
        }
