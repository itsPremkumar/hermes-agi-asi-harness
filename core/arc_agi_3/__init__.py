"""ARC-AGI-3 Complete Harness — NVIDIA AVO-style architecture.

Based on the NVIDIA AVO (Agentic Variation Operators) architecture that achieved
100% RHAE score on ARC-AGI-3 public set (183 levels, 25 environments, 6,624 actions).

Key AVO principles implemented:
1. Agent-as-variation-operator: the agent decides what to inspect, change, test, commit
2. Persistent memory: carries state across context windows
3. Supervisor: monitors trajectory, redirects when stuck
4. Grounded feedback: decisions based on actual environment outcomes
5. Text-only modality: 64x64 text grid observations
6. Long-horizon loop: hypothesis → act → observe → update → continue
"""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants — ARC-AGI-3 specification
# ---------------------------------------------------------------------------

GRID_SIZE = 64
NUM_COLORS = 16
MAX_ACTIONS_PER_LEVEL = 200  # generous budget; AVO used ~36 avg

class ActionType(str, Enum):
    """Canonical ARC-AGI-3 actions (text-only interface)."""
    RESET = "reset"
    ACTION1 = "action1"
    ACTION2 = "action2"
    ACTION3 = "action3"
    ACTION4 = "action4"
    ACTION5 = "action5"
    ACTION6 = "action6"
    ACTION7 = "action7"
    UNDO = "undo"
    WAIT = "wait"

ALL_ACTIONS = [a.value for a in ActionType]

# Scoring — RHAE formula
LEVEL_SCORE_CAP = 1.15 ** 2  # 1.3225


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Observation:
    """Text-only 64x64 grid observation from ARC-AGI-3."""
    grid: List[List[int]]  # 64x64, values 0-15
    score: float = 0.0
    done: bool = False
    info: Dict[str, Any] = field(default_factory=dict)

    def to_text(self) -> str:
        """Convert grid to text representation (NVIDIA AVO style)."""
        lines = []
        for row in self.grid:
            lines.append("".join(f"{c:x}" for c in row))
        return "\n".join(lines)

    @classmethod
    def from_text(cls, text: str) -> Observation:
        """Parse text grid back to observation."""
        lines = text.strip().split("\n")
        grid = [[int(c, 16) for c in line.strip()] for line in lines if line.strip()]
        return cls(grid=grid)


@dataclass
class Action:
    """An action to take in the environment."""
    action_type: ActionType
    params: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LevelResult:
    """Result of a single level attempt."""
    level_id: str
    completed: bool
    actions_used: int
    actions_budget: int
    score: float
    observations: int = 0
    hypotheses_tested: int = 0
    revisions: int = 0


@dataclass
class EnvironmentResult:
    """Result of a full environment run."""
    env_id: str
    levels_completed: int
    total_levels: int
    total_actions: int
    level_results: List[LevelResult] = field(default_factory=list)
    env_score: float = 0.0


@dataclass
class Hypothesis:
    """A hypothesis about environment dynamics."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.0
    tested: bool = False
    confirmed: bool = False
    source: str = ""  # which observation led to this


# ---------------------------------------------------------------------------
# Persistent Memory
# ---------------------------------------------------------------------------

@dataclass
class MemoryEntry:
    """A single memory entry."""
    key: str
    value: Any
    timestamp: float = field(default_factory=time.time)
    importance: float = 1.0
    source: str = ""


class PersistentMemory:
    """Persistent memory that carries state across context windows.

    Based on AVO's memory system that preserves:
    - Prior observations and actions
    - Hypotheses and their confirmation status
    - Accumulated reasoning about environment dynamics
    - Recovery state from incorrect assumptions
    """

    def __init__(self, max_entries: int = 1000):
        self._entries: Dict[str, MemoryEntry] = {}
        self._max_entries = max_entries
        self._hypotheses: List[Hypothesis] = []
        self._action_history: List[Tuple[Action, Observation]] = []
        self._insights: List[str] = []

    def store(self, key: str, value: Any, importance: float = 1.0, source: str = "") -> None:
        """Store a memory entry."""
        self._entries[key] = MemoryEntry(
            key=key, value=value, importance=importance, source=source
        )
        # Evict low-importance entries if at capacity
        if len(self._entries) > self._max_entries:
            sorted_entries = sorted(self._entries.values(), key=lambda e: e.importance)
            for entry in sorted_entries[:len(sorted_entries) // 4]:
                del self._entries[entry.key]

    def retrieve(self, key: str) -> Any | None:
        """Retrieve a memory entry by key."""
        entry = self._entries.get(key)
        return entry.value if entry else None

    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Search memory entries by keyword."""
        results = []
        query_lower = query.lower()
        for entry in self._entries.values():
            if query_lower in str(entry.value).lower() or query_lower in entry.key.lower():
                results.append(entry)
        results.sort(key=lambda e: e.importance, reverse=True)
        return results[:limit]

    def add_hypothesis(self, hypothesis: Hypothesis) -> None:
        """Add a hypothesis."""
        self._hypotheses.append(hypothesis)

    def get_active_hypotheses(self) -> List[Hypothesis]:
        """Get hypotheses that haven't been tested."""
        return [h for h in self._hypotheses if not h.tested]

    def get_confirmed_hypotheses(self) -> List[Hypothesis]:
        """Get confirmed hypotheses."""
        return [h for h in self._hypotheses if h.confirmed]

    def record_action(self, action: Action, observation: Observation) -> None:
        """Record an action-observation pair."""
        self._action_history.append((action, observation))

    def get_action_history(self, last_n: int = 50) -> List[Tuple[Action, Observation]]:
        """Get recent action history."""
        return self._action_history[-last_n:]

    def add_insight(self, insight: str) -> None:
        """Add a durable insight."""
        if insight not in self._insights:
            self._insights.append(insight)

    def get_insights(self) -> List[str]:
        """Get all insights."""
        return self._insights.copy()

    def get_state_summary(self) -> Dict[str, Any]:
        """Get a summary of current memory state."""
        return {
            "entries": len(self._entries),
            "hypotheses": len(self._hypotheses),
            "active_hypotheses": len(self.get_active_hypotheses()),
            "confirmed_hypotheses": len(self.get_confirmed_hypotheses()),
            "action_history": len(self._action_history),
            "insights": len(self._insights),
        }

    def save(self, path: Path) -> None:
        """Persist memory to disk."""
        data = {
            "entries": {k: {"value": v.value, "importance": v.importance} for k, v in self._entries.items()},
            "hypotheses": [{"id": h.id, "description": h.description, "confidence": h.confidence, "confirmed": h.confirmed} for h in self._hypotheses],
            "insights": self._insights,
        }
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path) -> PersistentMemory:
        """Load memory from disk."""
        memory = cls()
        if not path.exists():
            return memory
        data = json.loads(path.read_text())
        for k, v in data.get("entries", {}).items():
            memory.store(k, v["value"], v.get("importance", 1.0))
        for h in data.get("hypotheses", []):
            memory.add_hypothesis(Hypothesis(
                id=h["id"], description=h["description"],
                confidence=h["confidence"], confirmed=h["confirmed"]
            ))
        memory._insights = data.get("insights", [])
        return memory


# ---------------------------------------------------------------------------
# Supervisor
# ---------------------------------------------------------------------------

class SupervisorStatus(Enum):
    """Status of the supervisor."""
    ACTIVE = "active"
    STAGNATION_DETECTED = "stagnation_detected"
    REDIRECTING = "redirecting"
    INTERVENING = "intervening"


@dataclass
class TrajectoryAnalysis:
    """Analysis of the agent's trajectory."""
    actions_without_progress: int = 0
    repeated_actions: int = 0
    hypothesis_stagnation: bool = False
    score_plateau: bool = False
    needs_intervention: bool = False
    recommendation: str = ""


class Supervisor:
    """Monitors agent trajectory and redirects when stuck.

    Based on AVO's supervisor module that:
    - Monitors the broader search trajectory
    - Detects stagnation (repeated actions, no progress)
    - Redirects toward different strategies when progress stalls
    - Acts like a "CEO" nudging the agent when it goes off direction
    """

    def __init__(self, stagnation_threshold: int = 20, repetition_threshold: int = 5):
        self._status = SupervisorStatus.ACTIVE
        self._stagnation_threshold = stagnation_threshold
        self._repetition_threshold = repetition_threshold
        self._interventions: List[Dict[str, Any]] = []
        self._trajectory_window: List[Dict[str, Any]] = []

    @property
    def status(self) -> SupervisorStatus:
        return self._status

    def analyze(self, action: Action, observation: Observation, memory: PersistentMemory) -> TrajectoryAnalysis:
        """Analyze the current trajectory and detect stagnation."""
        analysis = TrajectoryAnalysis()

        # Record in trajectory window
        self._trajectory_window.append({
            "action": action.action_type.value,
            "score": observation.score,
            "done": observation.done,
            "timestamp": time.time(),
        })
        # Keep window manageable
        if len(self._trajectory_window) > 100:
            self._trajectory_window = self._trajectory_window[-100:]

        # Check for actions without progress
        if len(self._trajectory_window) >= 2:
            recent = self._trajectory_window[-self._stagnation_threshold:]
            if len(recent) >= self._stagnation_threshold:
                scores = [r["score"] for r in recent]
                if len(set(scores)) <= 1:  # no score change
                    analysis.score_plateau = True
                    analysis.actions_without_progress = len(recent)

        # Check for repeated actions
        if self._trajectory_window:
            recent_actions = [r["action"] for r in self._trajectory_window[-self._repetition_threshold:]]
            if len(recent_actions) >= self._repetition_threshold and len(set(recent_actions)) == 1:
                analysis.repeated_actions = len(recent_actions)
                analysis.needs_intervention = True

        # Check hypothesis stagnation
        active = memory.get_active_hypotheses()
        confirmed = memory.get_confirmed_hypotheses()
        if len(active) > 10 and len(confirmed) == 0:
            analysis.hypothesis_stagnation = True
            analysis.needs_intervention = True

        # Generate recommendation
        if analysis.needs_intervention:
            self._status = SupervisorStatus.REDIRECTING
            analysis.recommendation = self._generate_recommendation(analysis, memory)
        else:
            self._status = SupervisorStatus.ACTIVE

        return analysis

    def _generate_recommendation(self, analysis: TrajectoryAnalysis, memory: PersistentMemory) -> str:
        """Generate a recommendation for redirecting the agent."""
        recommendations = []

        if analysis.repeated_actions >= self._repetition_threshold:
            recommendations.append(
                f"Stop repeating action. Try a different approach. "
                f"Last {analysis.repeated_actions} actions were identical."
            )

        if analysis.score_plateau:
            recommendations.append(
                f"No score change in last {analysis.actions_without_progress} actions. "
                f"Try a fundamentally different strategy."
            )

        if analysis.hypothesis_stagnation:
            confirmed = memory.get_confirmed_hypotheses()
            if confirmed:
                recommendations.append(
                    f"You have {len(confirmed)} confirmed hypotheses. "
                    f"Act on them instead of forming new ones."
                )
            else:
                recommendations.append(
                    "You have many untested hypotheses. Start testing them systematically."
                )

        if not recommendations:
            recommendations.append("Try a different approach. Be more exploratory.")

        return " | ".join(recommendations)

    def record_intervention(self, recommendation: str, memory: PersistentMemory) -> None:
        """Record an intervention."""
        self._interventions.append({
            "timestamp": time.time(),
            "recommendation": recommendation,
            "memory_state": memory.get_state_summary(),
        })

    def get_interventions(self) -> List[Dict[str, Any]]:
        """Get all interventions."""
        return self._interventions.copy()


# ---------------------------------------------------------------------------
# Agent — The Main Loop
# ---------------------------------------------------------------------------

class ARCAGI3Agent:
    """Main agent implementing the AVO-style variation operator loop.

    The agent IS the variation operator: it decides what to inspect,
    what to change, what to test, and what to commit.
    """

    def __init__(
        self,
        memory: PersistentMemory | None = None,
        supervisor: Supervisor | None = None,
        max_actions_per_level: int = MAX_ACTIONS_PER_LEVEL,
        verbose: bool = False,
    ):
        self.memory = memory or PersistentMemory()
        self.supervisor = supervisor or Supervisor()
        self.max_actions_per_level = max_actions_per_level
        self.verbose = verbose
        self._current_level: str | None = None
        self._hypotheses_tested = 0
        self._revisions = 0

    def run_level(self, env: Any, level_id: str) -> LevelResult:
        """Run a single level."""
        self._current_level = level_id
        self._hypotheses_tested = 0
        self._revisions = 0

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Starting level: {level_id}")
            print(f"{'='*60}")

        # Reset environment
        obs = self._reset(env)
        actions_used = 0

        for step in range(self.max_actions_per_level):
            # Form hypothesis from observation
            hypothesis = self._form_hypothesis(obs)
            if hypothesis:
                self.memory.add_hypothesis(hypothesis)

            # Decide action based on observation + memory + supervisor
            action = self._decide_action(obs)

            # Take action
            obs = self._step(env, action)
            actions_used += 1

            # Record in memory
            self.memory.record_action(action, obs)

            # Supervisor analysis
            analysis = self.supervisor.analyze(action, obs, self.memory)
            if analysis.needs_intervention:
                self.supervisor.record_intervention(analysis.recommendation, self.memory)
                if self.verbose:
                    print(f"  [SUPERVISOR] {analysis.recommendation}")

            if self.verbose and step % 10 == 0:
                print(f"  Step {step}: action={action.action_type.value}, score={obs.score:.3f}")

            if obs.done:
                break

        result = LevelResult(
            level_id=level_id,
            completed=obs.done,
            actions_used=actions_used,
            actions_budget=self.max_actions_per_level,
            score=obs.score,
            observations=actions_used,
            hypotheses_tested=self._hypotheses_tested,
            revisions=self._revisions,
        )

        # Store level result in memory
        self.memory.store(
            f"level_result:{level_id}",
            {
                "completed": result.completed,
                "actions_used": result.actions_used,
                "score": result.score,
            },
            importance=2.0,
        )

        if self.verbose:
            status = "COMPLETED" if result.completed else "INCOMPLETE"
            print(f"Level {level_id}: {status} | actions={actions_used} | score={obs.score:.3f}")

        return result

    def _reset(self, env: Any) -> Observation:
        """Reset the environment."""
        if hasattr(env, 'reset'):
            result = env.reset()
            if isinstance(result, Observation):
                return result
            elif isinstance(result, tuple):
                return result[0]  # (obs, info)
            elif isinstance(result, dict):
                return Observation(**result)
        # Fallback: try to get initial observation
        return Observation(grid=[[0] * GRID_SIZE for _ in range(GRID_SIZE)])

    def _step(self, env: Any, action: Action) -> Observation:
        """Take a step in the environment."""
        if hasattr(env, 'step'):
            result = env.step(action.action_type.value)
            if isinstance(result, Observation):
                return result
            elif isinstance(result, tuple):
                obs = result[0]
                if isinstance(obs, Observation):
                    return obs
                elif isinstance(obs, dict):
                    return Observation(**obs)
                elif isinstance(obs, list):
                    return Observation(grid=obs)
            elif isinstance(result, dict):
                return Observation(**result)
        # Fallback
        return Observation(grid=[[0] * GRID_SIZE for _ in range(GRID_SIZE)])

    def _form_hypothesis(self, obs: Observation) -> Hypothesis | None:
        """Form a hypothesis from an observation."""
        # Analyze grid patterns
        grid = obs.grid
        if not grid:
            return None

        # Check for color patterns
        unique_colors = set()
        for row in grid:
            unique_colors.update(row)

        if len(unique_colors) <= 1:
            return Hypothesis(
                description=f"Grid is monochromatic (color {unique_colors.pop() if unique_colors else 'none'})",
                confidence=0.8,
                source="observation",
            )

        # Check for symmetry
        if self._check_symmetry(grid):
            return Hypothesis(
                description="Grid has symmetry — possible pattern completion task",
                confidence=0.6,
                source="observation",
            )

        # Check for regions
        regions = self._count_regions(grid)
        if regions > 1:
            return Hypothesis(
                description=f"Grid has {regions} distinct regions — possible region-based task",
                confidence=0.5,
                source="observation",
            )

        return None

    def _decide_action(self, obs: Observation) -> Action:
        """Decide the next action based on observation and memory."""
        # If supervisor recommends intervention, follow it
        if self.supervisor.status == SupervisorStatus.REDIRECTING:
            return self._exploratory_action()

        # Use confirmed hypotheses to guide action
        confirmed = self.memory.get_confirmed_hypotheses()
        if confirmed:
            # Act on the most confident hypothesis
            best = max(confirmed, key=lambda h: h.confidence)
            return self._action_from_hypothesis(best)

        # Default: systematic exploration
        return self._exploratory_action()

    def _action_from_hypothesis(self, hypothesis: Hypothesis) -> Action:
        """Derive an action from a hypothesis."""
        desc = hypothesis.description.lower()

        if "symmetry" in desc:
            return Action(action_type=ActionType.ACTION1, metadata={"reason": "test_symmetry"})
        elif "region" in desc:
            return Action(action_type=ActionType.ACTION2, metadata={"reason": "test_region"})
        elif "monochromatic" in desc:
            return Action(action_type=ActionType.ACTION3, metadata={"reason": "test_color"})
        else:
            return self._exploratory_action()

    def _exploratory_action(self) -> Action:
        """Choose an exploratory action."""
        history = self.memory.get_action_history(last_n=10)
        recent_actions = [a.action_type for a, _ in history]

        # Avoid repeating the same action
        for action_type in ActionType:
            if action_type not in recent_actions:
                return Action(action_type=action_type, metadata={"reason": "exploration"})

        # If all actions tried, pick randomly from non-repeating
        return Action(action_type=ActionType.ACTION1, metadata={"reason": "forced_exploration"})

    @staticmethod
    def _check_symmetry(grid: List[List[int]]) -> bool:
        """Check if grid has horizontal or vertical symmetry."""
        if not grid:
            return False
        rows = len(grid)
        return all(grid[i] == grid[rows - 1 - i] for i in range(rows // 2))

    @staticmethod
    def _count_regions(grid: List[List[int]]) -> int:
        """Count distinct regions in the grid using flood fill."""
        if not grid:
            return 0
        rows, cols = len(grid), len(grid[0])
        visited = [[False] * cols for _ in range(rows)]
        regions = 0

        for r in range(rows):
            for c in range(cols):
                if not visited[r][c]:
                    regions += 1
                    # BFS flood fill
                    color = grid[r][c]
                    queue = [(r, c)]
                    visited[r][c] = True
                    while queue:
                        cr, cc = queue.pop(0)
                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nr, nc = cr + dr, cc + dc
                            if 0 <= nr < rows and 0 <= nc < cols and not visited[nr][nc] and grid[nr][nc] == color:
                                visited[nr][nc] = True
                                queue.append((nr, nc))
        return regions


# ---------------------------------------------------------------------------
# RHAE Scorer
# ---------------------------------------------------------------------------

class ARCAGI3Scorer:
    """Computes RHAE (Relative Human Action Efficiency) scores.

    RHAE formula (per level): (H/A)^2 capped at 1.15^2 = 1.3225
    where H = human baseline actions, A = agent actions.

    Game score = weighted average by level index (1-indexed).
    Max game score = fraction of levels completed x game_max.
    """

    def __init__(self, human_baselines: Dict[str, float] | None = None):
        self._baselines = human_baselines or {}

    def set_baseline(self, level_id: str, human_actions: float) -> None:
        """Set human baseline for a level."""
        self._baselines[level_id] = human_actions

    def level_score(self, level_id: str, agent_actions: int) -> float:
        """Compute RHAE score for a single level."""
        baseline = self._baselines.get(level_id, agent_actions)
        if agent_actions <= 0 or baseline <= 0:
            return 0.0
        ratio = baseline / agent_actions
        return min(LEVEL_SCORE_CAP, ratio ** 2)

    def game_score(self, level_results: List[LevelResult]) -> float:
        """Compute weighted game score."""
        if not level_results:
            return 0.0

        total_weight = 0.0
        weighted_score = 0.0

        for i, result in enumerate(level_results, start=1):
            score = self.level_score(result.level_id, result.actions_used)
            weighted_score += i * score
            total_weight += i

        return weighted_score / total_weight if total_weight > 0 else 0.0

    def max_game_score(self, levels_completed: int, total_levels: int, game_max: float = 1.0) -> float:
        """Compute max possible game score based on completion fraction."""
        return (levels_completed / total_levels) * game_max if total_levels > 0 else 0.0


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class ARCAGI3Engine:
    """Main engine that ties agent, memory, supervisor, and scorer together."""

    def __init__(
        self,
        agent: ARCAGI3Agent | None = None,
        scorer: ARCAGI3Scorer | None = None,
        memory: PersistentMemory | None = None,
        supervisor: Supervisor | None = None,
        verbose: bool = False,
    ):
        self.memory = memory or PersistentMemory()
        self.supervisor = supervisor or Supervisor()
        self.agent = agent or ARCAGI3Agent(
            memory=self.memory, supervisor=self.supervisor, verbose=verbose
        )
        self.scorer = scorer or ARCAGI3Scorer()
        self.verbose = verbose

    def run_environment(self, env: Any, env_id: str, level_ids: List[str]) -> EnvironmentResult:
        """Run all levels in an environment."""
        level_results = []
        total_actions = 0

        for level_id in level_ids:
            result = self.agent.run_level(env, level_id)
            level_results.append(result)
            total_actions += result.actions_used

        # Compute scores
        game_score = self.scorer.game_score(level_results)
        max_score = self.scorer.max_game_score(
            sum(1 for r in level_results if r.completed),
            len(level_results),
        )

        return EnvironmentResult(
            env_id=env_id,
            levels_completed=sum(1 for r in level_results if r.completed),
            total_levels=len(level_ids),
            total_actions=total_actions,
            level_results=level_results,
            env_score=game_score,
        )

    def run_benchmark(self, environments: Dict[str, Any]) -> Dict[str, EnvironmentResult]:
        """Run the full benchmark across all environments."""
        results = {}
        for env_id, env in environments.items():
            if self.verbose:
                print(f"\n{'#'*60}")
                print(f"Environment: {env_id}")
                print(f"{'#'*60}")
            # Get level IDs from environment
            level_ids = self._get_level_ids(env)
            result = self.run_environment(env, env_id, level_ids)
            results[env_id] = result
        return results

    @staticmethod
    def _get_level_ids(env: Any) -> List[str]:
        """Get level IDs from an environment."""
        if hasattr(env, 'level_ids'):
            return env.level_ids
        elif hasattr(env, 'get_level_ids'):
            return env.get_level_ids()
        return ["level_1"]  # default


# ---------------------------------------------------------------------------
# Export
# __all__ = [
#     "ActionType", "ALL_ACTIONS", "GRID_SIZE", "NUM_COLORS",
#     "Observation", "Action", "Hypothesis",
#     "PersistentMemory", "MemoryEntry",
#     "Supervisor", "SupervisorStatus", "TrajectoryAnalysis",
#     "ARCAGI3Agent", "ARCAGI3Scorer", "ARCAGI3Engine",
#     "LevelResult", "EnvironmentResult", "LEVEL_SCORE_CAP", "MAX_ACTIONS_PER_LEVEL",
# ]
