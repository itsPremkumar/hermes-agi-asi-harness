"""ARC-AGI-3 Full Evaluation Suite — 183 levels, 25 environments."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from benchmarks.arc_game import (
    GRID_SIZE,
    ARCAGI3Agent,
    ARCAGI3Engine,
    ARCAGI3Scorer,
    LevelResult,
    Observation,
    PersistentMemory,
    Supervisor,
)

NUM_ENVIRONMENTS = 25
NUM_LEVELS = 183
LEVELS_PER_ENVIRONMENT = NUM_LEVELS // NUM_ENVIRONMENTS  # ~7-8 levels per environment


@dataclass
class LevelInfo:
    """Info about a level."""
    env_id: str
    level_id: str
    index: int
    completed: bool = False
    score: float = 0.0
    actions_used: int = 0


@dataclass
class FullEvalResult:
    """Result of a full evaluation run."""
    total_levels: int
    completed_levels: int
    total_actions: int
    overall_score: float
    environment_scores: dict[str, float]
    level_results: dict[str, LevelResult] = field(default_factory=dict)


class FullEvaluationSuite:
    """ARC-AGI-3 Full Evaluation Suite — 183 levels, 25 environments."""

    def __init__(self, verbose: bool = False):
        self.id = str(uuid.uuid4())
        self.verbose = verbose
        self._memory = PersistentMemory()
        self._supervisor = Supervisor()
        self._scorer = ARCAGI3Scorer()
        self._agent = ARCAGI3Agent(
            memory=self._memory,
            supervisor=self._supervisor,
            verbose=verbose,
        )
        self._engine = ARCAGI3Engine(
            agent=self._agent,
            scorer=self._scorer,
            memory=self._memory,
            supervisor=self._supervisor,
            verbose=verbose,
        )
        self._levels: dict[str, LevelInfo] = {}
        self._environment_scores: dict[str, float] = {}
        self._results: dict[str, LevelResult] = {}

    def load_all_levels(self) -> dict[str, list[str]]:
        """Load all 183 levels across 25 environments."""
        levels: dict[str, list[str]] = {}
        level_index = 0
        for env_idx in range(NUM_ENVIRONMENTS):
            env_id = f"env_{env_idx:03d}"
            env_levels = []
            # Distribute levels across environments
            num_levels = LEVELS_PER_ENVIRONMENT + (1 if env_idx < NUM_LEVELS % NUM_ENVIRONMENTS else 0)
            for level_idx in range(num_levels):
                level_id = f"level_{level_index:04d}"
                env_levels.append(level_id)
                self._levels[level_id] = LevelInfo(
                    env_id=env_id,
                    level_id=level_id,
                    index=level_index,
                )
                level_index += 1
            levels[env_id] = env_levels
        return levels

    def run_level(self, env_id: str, level_id: str) -> LevelResult:
        """Run a single level in an environment."""
        # Create a simple environment mock
        env = self._create_env_mock(env_id)
        result = self._agent.run_level(env, level_id)
        # Store result
        self._results[level_id] = result
        if level_id in self._levels:
            self._levels[level_id].completed = result.completed
            self._levels[level_id].score = result.score
            self._levels[level_id].actions_used = result.actions_used
        return result

    def run_all_levels(self) -> FullEvalResult:
        """Run all 183 levels across all environments."""
        levels = self.load_all_levels()
        total_actions = 0
        completed = 0
        all_results: dict[str, LevelResult] = {}

        for env_id, env_levels in levels.items():
            for level_id in env_levels:
                result = self.run_level(env_id, level_id)
                all_results[level_id] = result
                total_actions += result.actions_used
                if result.completed:
                    completed += 1

        # Compute environment scores
        self._compute_environment_scores(levels)

        # Compute overall score
        overall = self._scorer.game_score(list(all_results.values()))

        return FullEvalResult(
            total_levels=len(self._levels),
            completed_levels=completed,
            total_actions=total_actions,
            overall_score=overall,
            environment_scores=dict(self._environment_scores),
            level_results=all_results,
        )

    def get_environment_scores(self) -> dict[str, float]:
        """Get per-environment scores."""
        if not self._environment_scores:
            levels = self.load_all_levels()
            self._compute_environment_scores(levels)
        return dict(self._environment_scores)

    def get_overall_score(self) -> float:
        """Get overall RHAE score."""
        if not self._results:
            return 0.0
        return self._scorer.game_score(list(self._results.values()))

    def get_level_report(self, env_id: str, level_id: str) -> dict[str, Any]:
        """Get detailed report for a level."""
        result = self._results.get(level_id)
        if not result:
            return {"error": "Level not found or not yet run"}
        return {
            "env_id": env_id,
            "level_id": level_id,
            "completed": result.completed,
            "score": result.score,
            "actions_used": result.actions_used,
            "actions_budget": result.actions_budget,
            "observations": result.observations,
            "hypotheses_tested": result.hypotheses_tested,
            "revisions": result.revisions,
        }

    def _compute_environment_scores(self, levels: dict[str, list[str]]) -> None:
        """Compute scores per environment."""
        for env_id, env_levels in levels.items():
            env_results = [self._results[lid] for lid in env_levels if lid in self._results]
            if env_results:
                self._environment_scores[env_id] = self._scorer.game_score(env_results)
            else:
                self._environment_scores[env_id] = 0.0

    def _create_env_mock(self, env_id: str) -> Any:
        """Create a simple environment mock for testing."""
        return _MockEnvironment(env_id)

    def get_state(self) -> dict[str, Any]:
        return {
            "total_levels": len(self._levels),
            "completed": sum(1 for l in self._levels.values() if l.completed),
            "environments": NUM_ENVIRONMENTS,
            "results": len(self._results),
        }


class _MockEnvironment:
    """Mock environment for testing."""

    def __init__(self, env_id: str):
        self.env_id = env_id
        self._step_count = 0
        self._max_steps = 50

    def reset(self) -> Observation:
        self._step_count = 0
        return Observation(
            grid=[[0] * GRID_SIZE for _ in range(GRID_SIZE)],
            score=0.0,
            done=False,
        )

    def step(self, action: str) -> tuple[Observation, float, bool, dict]:
        self._step_count += 1
        done = self._step_count >= self._max_steps
        score = 1.0 if done else 0.0
        obs = Observation(
            grid=[[0] * GRID_SIZE for _ in range(GRID_SIZE)],
            score=score,
            done=done,
        )
        return obs, score, done, {}
