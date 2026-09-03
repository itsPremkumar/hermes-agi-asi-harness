"""ARC-AGI-3 Environment Connector — interface with the ARC-AGI-3 environment."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConnectionStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class ActionType(str, Enum):
    """Types of actions in ARC-AGI-3."""
    MOVE = "move"
    ROTATE = "rotate"
    COLOR = "color"
    FILL = "fill"
    ERASE = "erase"
    PLACE = "place"
    REMOVE = "remove"
    SUBMIT = "submit"


@dataclass
class Action:
    """An action to take in the environment."""
    id: str
    action_type: ActionType
    params: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Observation:
    """An observation from the environment."""
    id: str
    grid: list[list[int]]
    score: float = 0.0
    done: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """An ARC-AGI-3 task."""
    id: str
    name: str
    description: str
    examples: list[dict[str, Any]] = field(default_factory=list)
    test_grids: list[list[list[int]]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class EnvironmentConnector:
    """Connect to and interact with ARC-AGI-3 environment."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._status = ConnectionStatus.DISCONNECTED
        self._tasks: dict[str, Task] = {}
        self._current_task: Task | None = None
        self._observations: list[Observation] = []
        self._actions: list[Action] = []

    def connect(self) -> bool:
        """Connect to the ARC-AGI-3 environment."""
        self._status = ConnectionStatus.CONNECTING
        # Simulate connection
        self._status = ConnectionStatus.CONNECTED
        return True

    def disconnect(self) -> None:
        """Disconnect from the environment."""
        self._status = ConnectionStatus.DISCONNECTED
        self._current_task = None

    @property
    def status(self) -> ConnectionStatus:
        return self._status

    def load_task(self, task_id: str) -> Task | None:
        """Load a task by ID."""
        task = self._tasks.get(task_id)
        if task:
            self._current_task = task
        return task

    def register_task(self, task: Task) -> None:
        """Register a task."""
        self._tasks[task.id] = task

    def get_current_task(self) -> Task | None:
        """Get the current task."""
        return self._current_task

    def get_observation(self) -> Observation | None:
        """Get the current observation."""
        if not self._observations:
            # Generate a default observation
            task = self._current_task
            if task and task.test_grids:
                return Observation(
                    id=str(uuid.uuid4()),
                    grid=task.test_grids[0],
                )
        return self._observations[-1] if self._observations else None

    def take_action(self, action: Action) -> Observation | None:
        """Take an action in the environment."""
        self._actions.append(action)
        # Simulate observation after action
        obs = Observation(
            id=str(uuid.uuid4()),
            grid=[[0]],  # Placeholder
            score=0.0,
            done=action.action_type == ActionType.SUBMIT,
        )
        self._observations.append(obs)
        return obs

    def submit(self, grid: list[list[int]]) -> dict[str, Any]:
        """Submit a solution."""
        action = Action(
            id=str(uuid.uuid4()),
            action_type=ActionType.SUBMIT,
            params={"grid": grid},
        )
        obs = self.take_action(action)
        return {
            "correct": obs.score > 0.5 if obs else False,
            "score": obs.score if obs else 0.0,
        }

    def get_available_tasks(self) -> list[Task]:
        """Get all available tasks."""
        return list(self._tasks.values())

    def get_state(self) -> dict[str, Any]:
        return {
            "status": self._status.value,
            "current_task": self._current_task.id if self._current_task else None,
            "tasks_loaded": len(self._tasks),
            "observations": len(self._observations),
            "actions": len(self._actions),
        }
