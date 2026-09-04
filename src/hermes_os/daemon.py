"""
HERMES INTELLIGENCE OS — PLANE 18B: 24/7 BACKGROUND DAEMON & RESUMABLE CHECKPOINTS
===================================================================================
Prime Agent & DeerFlow inspired persistent daemon runtime:
- Event-driven wake and continuous background execution
- Resumable state persistence across crashes, disconnects, and process restarts
- Checkpoint / snapshot serialization to `.hermes/checkpoints/`
- Prioritized background mission queue
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes.os.daemon")


class MissionPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CheckpointSnapshot:
    """Complete checkpoint of an in-flight mission for disaster recovery."""
    checkpoint_id: str
    mission_id: str
    objective: str
    completed_steps: list[str]
    pending_steps: list[str]
    state_registers: dict[str, Any]
    world_state_summary: str
    tokens_consumed: int
    status: str  # in_progress, completed, failed, paused
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "mission_id": self.mission_id,
            "objective": self.objective,
            "completed_steps": self.completed_steps,
            "pending_steps": self.pending_steps,
            "state_registers": self.state_registers,
            "world_state_summary": self.world_state_summary,
            "tokens_consumed": self.tokens_consumed,
            "status": self.status,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CheckpointSnapshot:
        return cls(
            checkpoint_id=data["checkpoint_id"],
            mission_id=data["mission_id"],
            objective=data.get("objective", ""),
            completed_steps=data.get("completed_steps", []),
            pending_steps=data.get("pending_steps", []),
            state_registers=data.get("state_registers", {}),
            world_state_summary=data.get("world_state_summary", ""),
            tokens_consumed=data.get("tokens_consumed", 0),
            status=data.get("status", "in_progress"),
            timestamp=data.get("timestamp", time.time()),
        )


@dataclass
class QueuedMission:
    mission_id: str
    request: str
    priority: MissionPriority
    risk_level: str
    submitted_at: float = field(default_factory=time.time)


class PersistentDaemonRuntime:
    """
    24/7 background runtime managing checkpoints, crash recovery,
    and event-driven mission scheduling.
    """

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root
        self.checkpoint_dir = Path(workspace_root) / ".hermes" / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._queue: list[QueuedMission] = []
        self._checkpoints: dict[str, CheckpointSnapshot] = {}
        self._is_running: bool = False
        self._load_existing_checkpoints()

    def _load_existing_checkpoints(self):
        for f in self.checkpoint_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                snap = CheckpointSnapshot.from_dict(data)
                self._checkpoints[snap.mission_id] = snap
            except Exception as e:
                logger.debug("Failed loading checkpoint %s: %s", f, e)

    def save_checkpoint(self, snapshot: CheckpointSnapshot) -> str:
        """Persist mission state to disk."""
        self._checkpoints[snapshot.mission_id] = snapshot
        target = self.checkpoint_dir / f"{snapshot.mission_id}.json"
        target.write_text(json.dumps(snapshot.to_dict(), indent=2), encoding="utf-8")
        return snapshot.checkpoint_id

    def load_checkpoint(self, mission_id: str) -> Optional[CheckpointSnapshot]:
        return self._checkpoints.get(mission_id)

    def enqueue_mission(
        self,
        request: str,
        priority: MissionPriority = MissionPriority.NORMAL,
        risk_level: str = "medium",
    ) -> str:
        """Submit a task to the background queue."""
        mid = f"m-{uuid.uuid4().hex[:6]}"
        item = QueuedMission(
            mission_id=mid,
            request=request,
            priority=priority,
            risk_level=risk_level,
        )
        self._queue.append(item)
        # Sort queue by priority: CRITICAL > HIGH > NORMAL > LOW
        p_weights = {MissionPriority.CRITICAL: 4, MissionPriority.HIGH: 3, MissionPriority.NORMAL: 2, MissionPriority.LOW: 1}
        self._queue.sort(key=lambda x: p_weights.get(x.priority, 0), reverse=True)
        return mid

    def pop_next_mission(self) -> Optional[QueuedMission]:
        if not self._queue:
            return None
        return self._queue.pop(0)

    def pending_count(self) -> int:
        return len(self._queue)

    def active_checkpoints_count(self) -> int:
        return len(self._checkpoints)

    def reconstruct_from_crash(self) -> list[CheckpointSnapshot]:
        """Identify interrupted missions that were in progress during unexpected shutdown."""
        return [c for c in self._checkpoints.values() if c.status == "in_progress"]
