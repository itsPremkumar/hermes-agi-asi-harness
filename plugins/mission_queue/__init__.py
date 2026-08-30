"""
Mission Queue Plugin — Persistent Priority-Based Mission Queue

Implements the never-stop architecture's persistent mission queue with:
priority, deadline, dependencies, risk, resources, status, retry count, owner, evidence
States: CREATED → UNDERSTANDING → PLANNED → READY → RUNNING → WAITING → BLOCKED
       → VERIFYING → COMPLETED / FAILED → RECOVERING → REPLANNING → READY
"""

import heapq
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MissionStatus(str, Enum):
    CREATED = "created"
    UNDERSTANDING = "understanding"
    PLANNED = "planned"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    BLOCKED = "blocked"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    RECOVERING = "recovering"
    REPLANNING = "replanning"


@dataclass(order=True)
class MissionEntry:
    priority: float
    deadline: float | None
    retry_count: int
    mission_id: str
    mission: dict[str, Any] = field(compare=False)
    created_at: float = field(default_factory=time.time, compare=False)

    def __post_init__(self):
        if self.deadline is not None:
            # Higher priority for sooner deadlines
            self.priority = self.priority + (1.0 / max(1, self.deadline - time.time()))


class MissionQueue:
    def __init__(self):
        self._queue: list[MissionEntry] = []
        self._entries: dict[str, MissionEntry] = {}
        self._history: list[dict[str, Any]] = []
        self._counter = 0

    def submit(self, objective: str, priority: float = 1.0,
               deadline: float | None = None,
               dependencies: list[str] | None = None,
               risk_level: str = "low",
               budget: dict[str, Any] | None = None,
               owner: str = "system") -> str:
        """Submit a new mission to the queue."""
        mission_id = f"MISSION-{uuid.uuid4().hex[:8]}"
        mission = {
            "id": mission_id,
            "objective": objective,
            "priority": priority,
            "deadline": deadline,
            "dependencies": dependencies or [],
            "risk_level": risk_level,
            "budget": budget or {},
            "owner": owner,
            "status": MissionStatus.CREATED.value,
            "retry_count": 0,
            "created_at": time.time(),
            "evidence": [],
            "requirements": [],
            "constraints": [],
            "success_criteria": [],
            "failure_conditions": [],
        }

        entry = MissionEntry(
            priority=priority,
            deadline=deadline,
            retry_count=0,
            mission_id=mission_id,
            mission=mission,
        )

        heapq.heappush(self._queue, entry)
        self._entries[mission_id] = entry
        return mission_id

    def peek(self) -> dict[str, Any] | None:
        """Get next mission without removing it."""
        if not self._queue:
            return None
        # Return the highest priority (max) entry
        entry = max(self._queue)
        return entry.mission

    def pop(self) -> dict[str, Any] | None:
        """Remove and return the highest-priority mission."""
        if not self._queue:
            return None
        # Find and remove the highest priority entry
        entry = max(self._queue)
        self._queue.remove(entry)
        heapq.heapify(self._queue)
        self._entries.pop(entry.mission_id, None)
        entry.mission["status"] = MissionStatus.RUNNING.value
        return entry.mission

    def update_status(self, mission_id: str, status: str, evidence: str | None = None) -> bool:
        """Update a mission's status."""
        mission = self._get_by_id(mission_id)
        if mission is None:
            return False
        mission["status"] = status
        mission["updated_at"] = time.time()
        if evidence:
            mission["evidence"].append({"status": status, "evidence": evidence, "timestamp": time.time()})
        if status in ("completed", "failed"):
            self._history.append({**mission, "final_status": status})
        return True

    def get_status(self, mission_id: str) -> str | None:
        mission = self._get_by_id(mission_id)
        return mission["status"] if mission else None

    def _get_by_id(self, mission_id: str) -> dict[str, Any] | None:
        # Check queue first
        for entry in self._queue:
            if entry.mission_id == mission_id:
                return entry.mission
        # Check history
        for mission in self._history:
            if mission.get("id") == mission_id:
                return mission
        return None

    def retry(self, mission_id: str, new_priority: float | None = None) -> bool:
        """Re-queue a failed mission."""
        mission = self._get_by_id(mission_id)
        if mission is None:
            return False
        mission["retry_count"] += 1
        mission["status"] = MissionStatus.RECOVERING.value
        if new_priority:
            mission["priority"] = new_priority

        # Remove from history if present
        self._history = [m for m in self._history if m.get("id") != mission_id]

        entry = MissionEntry(
            priority=mission["priority"],
            deadline=mission.get("deadline"),
            retry_count=mission["retry_count"],
            mission_id=mission_id,
            mission=mission,
        )
        heapq.heappush(self._queue, entry)
        self._entries[mission_id] = entry
        return True

    def get_all(self) -> list[dict[str, Any]]:
        return [entry.mission for entry in sorted(self._queue, reverse=True)]

    def get_completed(self) -> list[dict[str, Any]]:
        return [m for m in self._history if m.get("final_status") == "completed"]

    def get_failed(self) -> list[dict[str, Any]]:
        return [m for m in self._history if m.get("final_status") == "failed"]

    def get_stats(self) -> dict[str, Any]:
        return {
            "pending": len(self._queue),
            "completed": len(self.get_completed()),
            "failed": len(self.get_failed()),
        }


class MissionQueuePlugin:
    def __init__(self):
        self.queue = MissionQueue()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        stats = self.queue.get_stats()
        return {"status": "healthy", "stats": stats}


async def create(kernel=None):
    plugin = MissionQueuePlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
