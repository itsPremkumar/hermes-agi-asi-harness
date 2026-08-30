"""
Trajectory Replay — Replay and compare action sequences.

Enables:
- Replay original trajectory with modified policy
- Compare outcomes
- Counterfactual evaluation: what if we had done Z instead?
"""

from __future__ import annotations

import copy
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ReplayResult:
    id: str
    original_trajectory_id: str
    modified_policy: str
    steps_replayed: int
    outcome: str
    reward: float
    reward_delta: float  # vs original
    timestamp: float
    notes: List[str] = field(default_factory=list)


@dataclass
class Counterfactual:
    id: str
    trajectory_id: str
    step_number: int
    original_action: Dict[str, Any]
    alternative_action: Dict[str, Any]
    predicted_outcome: str
    predicted_reward: float
    timestamp: float


class TrajectoryReplay:
    """Replay trajectories with modified policies for learning."""

    def __init__(self):
        self.replay_results: List[ReplayResult] = []
        self.counterfactuals: List[Counterfactual] = []

    def replay(self, trajectory: Any, policy_modifier: Callable,
               executor: Callable = None) -> ReplayResult:
        """Replay a trajectory with a modified policy."""
        result = ReplayResult(
            id=str(uuid.uuid4()),
            original_trajectory_id=trajectory.id,
            modified_policy=getattr(policy_modifier, '__name__', 'unknown'),
            steps_replayed=0,
            outcome="unknown",
            reward=0.0,
            reward_delta=0.0,
            timestamp=time.time(),
        )

        if not trajectory.steps:
            result.notes.append("No steps to replay")
            return result

        total_reward = 0.0
        for step in trajectory.steps:
            # Apply policy modifier
            modified_action = policy_modifier(step.action, step.state_before)
            
            if executor:
                try:
                    obs = executor(modified_action, step.state_before)
                    total_reward += obs.get('reward', 0.0)
                    result.steps_replayed += 1
                except Exception as e:
                    result.notes.append(f"Step {step.step_number} failed: {e}")
                    break
            else:
                total_reward += step.metadata.get('reward', 0.0)
                result.steps_replayed += 1

        result.reward = total_reward
        result.reward_delta = total_reward - trajectory.total_reward
        result.outcome = "success" if total_reward > trajectory.total_reward else "failure"
        
        self.replay_results.append(result)
        return result

    def generate_counterfactual(self, trajectory: Any, step_number: int,
                                alternative_action: Dict[str, Any],
                                predicted_outcome: str = "unknown",
                                predicted_reward: float = 0.0) -> Optional[Counterfactual]:
        """Generate a counterfactual: what if we had done Z instead?"""
        if step_number >= len(trajectory.steps):
            return None
        
        step = trajectory.steps[step_number]
        cf = Counterfactual(
            id=str(uuid.uuid4()),
            trajectory_id=trajectory.id,
            step_number=step_number,
            original_action=step.action,
            alternative_action=alternative_action,
            predicted_outcome=predicted_outcome,
            predicted_reward=predicted_reward,
            timestamp=time.time(),
        )
        self.counterfactuals.append(cf)
        return cf

    def get_counterfactuals_for_trajectory(self, trajectory_id: str) -> List[Counterfactual]:
        return [c for c in self.counterfactuals if c.trajectory_id == trajectory_id]

    def get_replay_results(self, trajectory_id: str = None) -> List[ReplayResult]:
        if trajectory_id:
            return [r for r in self.replay_results if r.original_trajectory_id == trajectory_id]
        return self.replay_results

    def get_state(self) -> Dict[str, Any]:
        return {
            "replays": len(self.replay_results),
            "counterfactuals": len(self.counterfactuals),
            "positive_delta": sum(1 for r in self.replay_results if r.reward_delta > 0),
        }
