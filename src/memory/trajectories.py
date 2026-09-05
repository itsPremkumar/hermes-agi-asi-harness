"""
HERMES INTELLIGENCE OS — SEARCHABLE TRAJECTORY ARCHIVE
======================================================
Stores full execution traces:
State -> Decision -> Action -> Observation -> Outcome
Enables retrospective analysis, experience replay, curriculum extraction,
and cross-mission transfer without saturating prompt context windows.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("hermes.memory.trajectories")


@dataclass
class TrajectoryStep:
    step_id: str
    state_summary: str
    decision_rationale: str
    action_type: str
    action_args: dict[str, Any]
    observation: str
    outcome: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "state_summary": self.state_summary,
            "decision_rationale": self.decision_rationale,
            "action_type": self.action_type,
            "action_args": self.action_args,
            "observation": self.observation,
            "outcome": self.outcome,
            "timestamp": self.timestamp,
        }


@dataclass
class Trajectory:
    trajectory_id: str
    mission_id: str
    task_description: str
    steps: list[TrajectoryStep] = field(default_factory=list)
    success: bool = True
    total_duration_seconds: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trajectory_id": self.trajectory_id,
            "mission_id": self.mission_id,
            "task_description": self.task_description,
            "steps": [s.to_dict() for s in self.steps],
            "success": self.success,
            "total_duration_seconds": self.total_duration_seconds,
            "created_at": self.created_at,
        }


class TrajectoryArchive:
    """Persistent on-disk archive with fast lexical and keyword search."""

    def __init__(self, workspace_root: str = "."):
        self.archive_dir = Path(workspace_root) / ".hermes" / "trajectories"
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self._in_memory_index: dict[str, Trajectory] = {}
        self._load_existing()

    def _load_existing(self):
        for f in self.archive_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                steps = [
                    TrajectoryStep(
                        step_id=s["step_id"],
                        state_summary=s["state_summary"],
                        decision_rationale=s["decision_rationale"],
                        action_type=s["action_type"],
                        action_args=s.get("action_args", {}),
                        observation=s["observation"],
                        outcome=s["outcome"],
                        timestamp=s.get("timestamp", time.time()),
                    )
                    for s in data.get("steps", [])
                ]
                traj = Trajectory(
                    trajectory_id=data["trajectory_id"],
                    mission_id=data.get("mission_id", ""),
                    task_description=data.get("task_description", ""),
                    steps=steps,
                    success=data.get("success", True),
                    total_duration_seconds=data.get("total_duration_seconds", 0.0),
                    created_at=data.get("created_at", time.time()),
                )
                self._in_memory_index[traj.trajectory_id] = traj
            except Exception as e:
                logger.debug("Failed loading trajectory file %s: %s", f, e)

    def record_trajectory(self, trajectory: Trajectory) -> str:
        """Persist a completed trajectory to disk."""
        self._in_memory_index[trajectory.trajectory_id] = trajectory
        target_path = self.archive_dir / f"{trajectory.trajectory_id}.json"
        target_path.write_text(json.dumps(trajectory.to_dict(), indent=2), encoding="utf-8")
        return trajectory.trajectory_id

    def get_trajectory(self, trajectory_id: str) -> Optional[Trajectory]:
        """Retrieve an indexed trajectory by its unique ID."""
        return self._in_memory_index.get(trajectory_id)

    def search_similar(self, query: str, limit: int = 5) -> list[Trajectory]:
        """Search past trajectories matching keywords in task description or steps."""
        query_words = set(re.findall(r"\w+", query.lower()))
        scored = []

        for traj in self._in_memory_index.values():
            corpus = traj.task_description + " " + " ".join(s.action_type + " " + s.observation for s in traj.steps)
            corpus_words = set(re.findall(r"\w+", corpus.lower()))
            overlap = len(query_words & corpus_words)
            if overlap > 0:
                scored.append((overlap, traj))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:limit]]

    def count(self) -> int:
        return len(self._in_memory_index)
