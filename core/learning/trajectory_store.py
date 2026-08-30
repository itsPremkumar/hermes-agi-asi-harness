"""
Trajectory Store — Record, replay, and learn from action sequences.

Every action sequence becomes a trajectory:
  STATE₀ → ACTION₀ → OBSERVATION₀ → STATE₁ → ACTION₁ → OBSERVATION₁ → ...

Used for: debugging, learning, benchmarking, counterfactuals, policy evaluation.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TrajectoryStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class TrajectoryStep:
    step_number: int
    state_before: Dict[str, Any]
    action: Dict[str, Any]
    observation: Dict[str, Any]
    state_after: Dict[str, Any]
    timestamp: float
    confidence: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Trajectory:
    id: str
    mission_id: str
    goal: str
    steps: List[TrajectoryStep]
    status: TrajectoryStatus
    created_at: float
    completed_at: Optional[float] = None
    outcome: Optional[str] = None
    total_reward: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class TrajectoryStore:
    """Store and manage action trajectories."""

    def __init__(self):
        self.trajectories: Dict[str, Trajectory] = {}
        self._step_counts: Dict[str, int] = {}  # trajectory_id → step count

    def create_trajectory(self, mission_id: str, goal: str,
                          initial_state: Dict[str, Any] = None) -> Trajectory:
        traj = Trajectory(
            id=str(uuid.uuid4()),
            mission_id=mission_id,
            goal=goal,
            steps=[],
            status=TrajectoryStatus.IN_PROGRESS,
            created_at=time.time(),
            metadata={"initial_state": initial_state or {}},
        )
        self.trajectories[traj.id] = traj
        self._step_counts[traj.id] = 0
        return traj

    def add_step(self, trajectory_id: str, state_before: Dict[str, Any],
                 action: Dict[str, Any], observation: Dict[str, Any],
                 state_after: Dict[str, Any], confidence: float = 0.5,
                 metadata: Dict[str, Any] = None) -> Optional[TrajectoryStep]:
        traj = self.trajectories.get(trajectory_id)
        if not traj:
            return None
        
        step = TrajectoryStep(
            step_number=self._step_counts[traj.id],
            state_before=state_before,
            action=action,
            observation=observation,
            state_after=state_after,
            timestamp=time.time(),
            confidence=confidence,
            metadata=metadata or {},
        )
        traj.steps.append(step)
        self._step_counts[traj.id] += 1
        return step

    def complete_trajectory(self, trajectory_id: str, outcome: str,
                            reward: float = 0.0):
        traj = self.trajectories.get(trajectory_id)
        if not traj:
            return
        traj.status = TrajectoryStatus.COMPLETED if outcome == "success" else TrajectoryStatus.FAILED
        traj.completed_at = time.time()
        traj.outcome = outcome
        traj.total_reward = reward

    def get_trajectory(self, trajectory_id: str) -> Optional[Trajectory]:
        return self.trajectories.get(trajectory_id)

    def get_trajectories_by_mission(self, mission_id: str) -> List[Trajectory]:
        return [t for t in self.trajectories.values() if t.mission_id == mission_id]

    def get_trajectories_by_outcome(self, outcome: str) -> List[Trajectory]:
        return [t for t in self.trajectories.values() if t.outcome == outcome]

    def get_all_trajectories(self) -> List[Trajectory]:
        return list(self.trajectories.values())

    def get_state(self) -> Dict[str, Any]:
        return {
            "total_trajectories": len(self.trajectories),
            "completed": sum(1 for t in self.trajectories.values() if t.status == TrajectoryStatus.COMPLETED),
            "failed": sum(1 for t in self.trajectories.values() if t.status == TrajectoryStatus.FAILED),
            "in_progress": sum(1 for t in self.trajectories.values() if t.status == TrajectoryStatus.IN_PROGRESS),
        }
