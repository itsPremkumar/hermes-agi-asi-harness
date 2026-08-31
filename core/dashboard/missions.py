"""Mission control — create, track, and manage missions."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MissionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Mission:
    id: str
    goal: str
    status: MissionStatus = MissionStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    result: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class MissionController:
    """Manage mission lifecycle."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._missions: dict[str, Mission] = {}

    def create(self, goal: str) -> Mission:
        mission = Mission(id=str(uuid.uuid4()), goal=goal)
        self._missions[mission.id] = mission
        return mission

    def start(self, mission_id: str) -> bool:
        if mission_id in self._missions:
            self._missions[mission_id].status = MissionStatus.RUNNING
            self._missions[mission_id].started_at = time.time()
            return True
        return False

    def complete(self, mission_id: str, result: Any = None) -> bool:
        if mission_id in self._missions:
            self._missions[mission_id].status = MissionStatus.COMPLETED
            self._missions[mission_id].completed_at = time.time()
            self._missions[mission_id].result = result
            return True
        return False

    def fail(self, mission_id: str, error: str = "") -> bool:
        if mission_id in self._missions:
            self._missions[mission_id].status = MissionStatus.FAILED
            self._missions[mission_id].completed_at = time.time()
            self._missions[mission_id].error = error
            return True
        return False

    def get(self, mission_id: str) -> Mission | None:
        return self._missions.get(mission_id)

    def list_all(self) -> list[Mission]:
        return list(self._missions.values())

    def list_by_status(self, status: MissionStatus) -> list[Mission]:
        return [m for m in self._missions.values() if m.status == status]

    def count(self) -> int:
        return len(self._missions)

    def get_state(self) -> dict[str, Any]:
        return {
            "total": self.count(),
            "pending": len(self.list_by_status(MissionStatus.PENDING)),
            "running": len(self.list_by_status(MissionStatus.RUNNING)),
            "completed": len(self.list_by_status(MissionStatus.COMPLETED)),
            "failed": len(self.list_by_status(MissionStatus.FAILED)),
        }
