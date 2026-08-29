"""experience_replay.py — Store and replay past missions for training.

Experience replay stores complete mission records (observations, actions, rewards)
so they can be replayed later for training, fine-tuning, or curriculum design.

This is inspired by experience replay in reinforcement learning but adapted for
LLG agent workflows: store trajectories, sample minibatches, re-execute.

Module API:
- Step: a single step in a mission (observation, action, reward)
- Mission: a complete trajectory
- ExperienceBuffer: stores missions, samples minibatches
- Replayer: replays stored missions against a runner for training
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import random
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator, Sequence


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclass
class Step:
    """A single step in a mission trajectory."""

    observation: str
    action: str
    reward: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Step":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Mission:
    """A complete mission trajectory."""

    id: str
    goal: str
    steps: list[Step] = field(default_factory=list)
    success: bool = False
    final_reward: float = 0.0
    capability: str = "general"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    @property
    def length(self) -> int:
        return len(self.steps)

    @property
    def total_reward(self) -> float:
        return sum(s.reward for s in self.steps) + self.final_reward

    @property
    def average_reward(self) -> float:
        if not self.steps:
            return 0.0
        return self.total_reward / (len(self.steps) + 1)

    def add_step(self, observation: str, action: str, reward: float = 0.0, **meta: Any) -> Step:
        step = Step(observation=observation, action=action, reward=reward, metadata=meta)
        self.steps.append(step)
        return step

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "success": self.success,
            "final_reward": self.final_reward,
            "capability": self.capability,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Mission":
        steps = [Step.from_dict(s) for s in data.pop("steps", [])]
        return cls(steps=steps, **{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Experience buffer
# ---------------------------------------------------------------------------


class ExperienceBuffer:
    """Stores missions for replay. Supports prioritised sampling and pruning.

    Usage:
        buf = ExperienceBuffer(capacity=1000)
        buf.store(mission)
        batch = buf.sample(32)
        buf.prune(oldest=100)
    """

    def __init__(
        self,
        capacity: int = 10_000,
        priority: str = "uniform",
        seed: int | None = None,
    ) -> None:
        self.capacity = capacity
        self.priority = priority
        self._rng = random.Random(seed)
        self._missions: list[Mission] = []
        self._priorities: list[float] = []

    # -- storage -----------------------------------------------------------

    def store(self, mission: Mission) -> None:
        """Store a mission. Evicts oldest if at capacity."""
        if len(self._missions) >= self.capacity:
            self._missions.pop(0)
            if self._priorities:
                self._priorities.pop(0)
        self._missions.append(mission)
        if self.priority == "reward":
            self._priorities.append(max(0.0, mission.total_reward))
        elif self.priority == "length":
            self._priorities.append(float(mission.length))
        else:
            self._priorities.append(1.0)

    def extend(self, missions: Sequence[Mission]) -> None:
        for m in missions:
            self.store(m)

    # -- sampling ----------------------------------------------------------

    def sample(self, n: int, strategy: str | None = None) -> list[Mission]:
        """Sample n missions. Strategy overrides instance default."""
        if not self._missions:
            return []
        strat = strategy or self.priority
        n = min(n, len(self._missions))
        if strat == "uniform":
            return self._rng.sample(self._missions, n)
        if strat == "reward" and self._priorities:
            return self._weighted_sample(n)
        if strat == "length" and self._priorities:
            return self._weighted_sample(n)
        if strat == "recent":
            return self._missions[-n:]
        return self._rng.sample(self._missions, n)

    def sample_steps(self, n: int) -> list[Step]:
        """Sample n individual steps across all missions."""
        all_steps = [s for m in self._missions for s in m.steps]
        if not all_steps:
            return []
        n = min(n, len(all_steps))
        return self._rng.sample(all_steps, n)

    def _weighted_sample(self, n: int) -> list[Mission]:
        total = sum(self._priorities)
        if total <= 0:
            return self._rng.sample(self._missions, n)
        probs = [p / total for p in self._priorities]
        indices = self._rng.choices(range(len(self._missions)), weights=probs, k=n)
        return [self._missions[i] for i in indices]

    # -- queries -----------------------------------------------------------

    def filter_by(self, capability: str | None = None, success: bool | None = None) -> list[Mission]:
        """Filter missions by capability and/or success."""
        result = list(self._missions)
        if capability is not None:
            result = [m for m in result if m.capability == capability]
        if success is not None:
            result = [m for m in result if m.success == success]
        return result

    def get(self, mission_id: str) -> Mission | None:
        return next((m for m in self._missions if m.id == mission_id), None)

    # -- stats ------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        if not self._missions:
            return {"count": 0, "avg_length": 0.0, "avg_reward": 0.0, "success_rate": 0.0}
        lengths = [m.length for m in self._missions]
        rewards = [m.total_reward for m in self._missions]
        successes = sum(1 for m in self._missions if m.success)
        by_cap: dict[str, list[float]] = defaultdict(list)
        for m in self._missions:
            by_cap[m.capability].append(m.total_reward)
        return {
            "count": len(self._missions),
            "avg_length": statistics.mean(lengths),
            "avg_reward": statistics.mean(rewards),
            "success_rate": successes / len(self._missions),
            "by_capability": {
                cap: {"count": len(rs), "avg_reward": statistics.mean(rs)}
                for cap, rs in by_cap.items()
            },
        }

    def reward_distribution(self, bins: int = 10) -> list[int]:
        """Histogram of total rewards across missions."""
        if not self._missions:
            return []
        rewards = [m.total_reward for m in self._missions]
        lo, hi = min(rewards), max(rewards)
        if lo == hi:
            return [len(rewards)]
        width = (hi - lo) / bins
        counts = [0] * bins
        for r in rewards:
            idx = int((r - lo) / width)
            idx = min(idx, bins - 1)
            counts[idx] += 1
        return counts

    # -- maintenance -------------------------------------------------------

    def prune(self, *, oldest: int | None = None, min_reward: float | None = None) -> int:
        """Remove missions. Returns count removed."""
        start_len = len(self._missions)
        if oldest is not None and oldest > 0:
            self._missions = self._missions[-oldest:]
            self._priorities = self._priorities[-oldest:]
        if min_reward is not None:
            kept = [(m, p) for m, p in zip(self._missions, self._priorities) if m.total_reward >= min_reward]
            if kept:
                self._missions, self._priorities = zip(*kept)  # type: ignore[assignment]
                self._missions = list(self._missions)
                self._priorities = list(self._priorities)
            else:
                self._missions = []
                self._priorities = []
        return start_len - len(self._missions)

    def clear(self) -> None:
        self._missions.clear()
        self._priorities.clear()

    # -- serialisation ----------------------------------------------------

    def save(self, path: str | Path) -> None:
        data = {
            "capacity": self.capacity,
            "priority": self.priority,
            "missions": [m.to_dict() for m in self._missions],
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "ExperienceBuffer":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        buf = cls(capacity=raw.get("capacity", 10_000), priority=raw.get("priority", "uniform"))
        for m_data in raw.get("missions", []):
            buf._missions.append(Mission.from_dict(m_data))
        return buf

    # -- iterators ---------------------------------------------------------

    def __iter__(self) -> Iterator[Mission]:
        return iter(self._missions)

    def __len__(self) -> int:
        return len(self._missions)

    def __contains__(self, mission_id: str) -> bool:
        return any(m.id == mission_id for m in self._missions)


# ---------------------------------------------------------------------------
# Replayer
# ---------------------------------------------------------------------------


class Replayer:
    """Replay stored missions against a runner for training/evaluation.

    The runner is a callable that takes (observation, action) -> new_observation.
    The replayer executes the stored steps and compares the runner's output
    to the stored trajectory.

    Usage:
        replayer = Replayer(buffer)
        report = replayer.replay(mission_id, runner=my_policy)
    """

    def __init__(self, buffer: ExperienceBuffer) -> None:
        self.buffer = buffer
        self.replay_logs: list[dict[str, Any]] = []

    def replay(
        self,
        mission_id: str,
        runner: Callable[[str, str], str],
        max_steps: int | None = None,
    ) -> dict[str, Any]:
        """Replay a single mission. Returns a replay report."""
        mission = self.buffer.get(mission_id)
        if mission is None:
            return {"error": "mission not found", "mission_id": mission_id}
        total_match = 0
        total_steps = 0
        trajectory: list[dict[str, Any]] = []
        for i, step in enumerate(mission.steps):
            if max_steps is not None and i >= max_steps:
                break
            predicted = runner(step.observation, step.action)
            match = self._fuzzy_match(predicted, step.action)
            if match:
                total_match += 1
            total_steps += 1
            trajectory.append(
                {
                    "step": i,
                    "observation": step.observation,
                    "expected_action": step.action,
                    "predicted_action": predicted,
                    "match": match,
                }
            )
        accuracy = total_match / total_steps if total_steps > 0 else 0.0
        report = {
            "mission_id": mission_id,
            "total_steps": total_steps,
            "matches": total_match,
            "accuracy": accuracy,
            "trajectory": trajectory,
        }
        self.replay_logs.append(report)
        return report

    def replay_all(
        self,
        runner: Callable[[str, str], str],
        capability: str | None = None,
        max_per_mission: int | None = None,
    ) -> dict[str, Any]:
        """Replay all matching missions. Returns aggregate report."""
        missions = self.buffer.filter_by(capability=capacity)
        if not missions:
            return {"missions_replayed": 0, "avg_accuracy": 0.0}
        reports: list[dict[str, Any]] = []
        for m in missions:
            r = self.replay(m.id, runner, max_steps=max_per_mission)
            if "error" not in r:
                reports.append(r)
        if not reports:
            return {"missions_replayed": 0, "avg_accuracy": 0.0}
        return {
            "missions_replayed": len(reports),
            "avg_accuracy": statistics.mean(r["accuracy"] for r in reports),
            "avg_steps": statistics.mean(r["total_steps"] for r in reports),
            "reports": reports,
        }

    def compare_runners(
        self,
        mission_id: str,
        runners: dict[str, Callable[[str, str], str]],
    ) -> dict[str, Any]:
        """Compare multiple runners on the same mission."""
        results: dict[str, Any] = {}
        for name, runner in runners.items():
            report = self.replay(mission_id, runner)
            results[name] = {
                "accuracy": report.get("accuracy", 0.0),
                "matches": report.get("matches", 0),
                "total_steps": report.get("total_steps", 0),
            }
        return {
            "mission_id": mission_id,
            "runner_count": len(runners),
            "results": results,
        }

    # -- internal ----------------------------------------------------------

    @staticmethod
    def _fuzzy_match(a: str, b: str, threshold: float = 0.8) -> bool:
        """Simple token-overlap match."""
        a_tokens = set(a.lower().split())
        b_tokens = set(b.lower().split())
        if not a_tokens or not b_tokens:
            return a == b
        overlap = a_tokens & b_tokens
        score = len(overlap) / max(len(a_tokens), len(b_tokens))
        return score >= threshold


# ---------------------------------------------------------------------------
# Training helpers
# ---------------------------------------------------------------------------


def make_mission_id(goal: str, ts: float | None = None) -> str:
    """Generate a deterministic mission id."""
    ts = ts or time.time()
    content = f"{goal}:{ts}"
    h = hashlib.sha256(content.encode()).hexdigest()[:12]
    return f"mission-{h}"


def generate_synthetic_missions(
    n: int,
    capabilities: Sequence[str],
    steps_range: tuple[int, int] = (3, 8),
    seed: int | None = None,
) -> list[Mission]:
    """Generate synthetic missions for testing/demo."""
    rng = random.Random(seed)
    missions: list[Mission] = []
    for _ in range(n):
        cap = rng.choice(capabilities)
        goal = f"solve_{cap}_{rng.randint(1, 1000)}"
        m = Mission(id=make_mission_id(goal), goal=goal, capability=cap)
        n_steps = rng.randint(*steps_range)
        for i in range(n_steps):
            reward = rng.uniform(-0.5, 1.0)
            m.add_step(
                observation=f"obs_{i}",
                action=f"act_{i}",
                reward=reward,
            )
        m.success = rng.random() > 0.3
        m.final_reward = rng.uniform(0, 5) if m.success else rng.uniform(-2, 0)
        missions.append(m)
    return missions
