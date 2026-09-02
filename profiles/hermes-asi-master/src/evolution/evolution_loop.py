"""evolution_loop.py — Controlled self-improvement with sandbox+rollback.

This module implements the main evolution loop that observes agent performance,
generates hypotheses for improvement, tests them in a sandbox, validates
safety, and promotes or rolls back changes.

Module API:
- EvolutionState: tracks the current state of evolution
- Sandbox: isolated environment for testing evolution hypotheses
- RollbackManager: manages checkpoints and rollback operations
- EvolutionLoop: the main evolution loop
- Hypothesis: a proposed improvement to test
- HypothesisResult: result of testing a hypothesis
"""

from __future__ import annotations

import copy
import dataclasses
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclass
class Hypothesis:
    """A proposed improvement to test."""

    hypothesis_id: str
    description: str
    target_module: str
    changes: dict[str, Any]  # parameter changes to apply
    expected_improvement: float = 0.1
    priority: int = 1
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Hypothesis":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class HypothesisResult:
    """Result of testing a hypothesis."""

    hypothesis: Hypothesis
    success: bool
    score_before: float
    score_after: float
    improvement: float
    safety_passed: bool
    sandbox_id: str
    tested_at: float = field(default_factory=time.time)
    error: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def promoted(self) -> bool:
        return self.success and self.safety_passed and self.improvement > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis": self.hypothesis.to_dict(),
            "success": self.success,
            "score_before": self.score_before,
            "score_after": self.score_after,
            "improvement": self.improvement,
            "safety_passed": self.safety_passed,
            "sandbox_id": self.sandbox_id,
            "tested_at": self.tested_at,
            "error": self.error,
            "details": self.details,
        }


@dataclass
class Checkpoint:
    """A snapshot of agent state for rollback."""

    checkpoint_id: str
    state: dict[str, Any]
    label: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Checkpoint":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Evolution State
# ---------------------------------------------------------------------------


@dataclass
class EvolutionState:
    """Tracks the current state of the evolution system."""

    generation: int = 0
    current_score: float = 0.0
    best_score: float = 0.0
    total_hypotheses_tested: int = 0
    total_hypotheses_promoted: int = 0
    total_rollbacks: int = 0
    current_strategy: dict[str, Any] = field(default_factory=dict)
    history: list[HypothesisResult] = field(default_factory=list)
    last_updated: float = field(default_factory=time.time)

    def record_result(self, result: HypothesisResult) -> None:
        """Record a hypothesis result."""
        self.history.append(result)
        self.total_hypotheses_tested += 1
        if result.promoted:
            self.total_hypotheses_promoted += 1
            self.current_score = result.score_after
            if self.current_score > self.best_score:
                self.best_score = self.current_score
        self.last_updated = time.time()

    def summary(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "current_score": self.current_score,
            "best_score": self.best_score,
            "total_hypotheses_tested": self.total_hypotheses_tested,
            "total_hypotheses_promoted": self.total_hypotheses_promoted,
            "total_rollbacks": self.total_rollbacks,
            "promotion_rate": (
                self.total_hypotheses_promoted / self.total_hypotheses_tested
                if self.total_hypotheses_tested > 0
                else 0.0
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "current_score": self.current_score,
            "best_score": self.best_score,
            "total_hypotheses_tested": self.total_hypotheses_tested,
            "total_hypotheses_promoted": self.total_hypotheses_promoted,
            "total_rollbacks": self.total_rollbacks,
            "current_strategy": self.current_strategy,
            "history": [h.to_dict() for h in self.history],
            "last_updated": self.last_updated,
        }


# ---------------------------------------------------------------------------
# Sandbox
# ---------------------------------------------------------------------------


class Sandbox:
    """Isolated environment for testing evolution hypotheses.

    Provides a copy of agent state that can be modified without affecting
    the production state. Changes are applied and evaluated in isolation.
    """

    def __init__(self, sandbox_id: str, base_state: dict[str, Any]) -> None:
        self.sandbox_id = sandbox_id
        self._base_state = copy.deepcopy(base_state)
        self._working_state = copy.deepcopy(base_state)
        self._applied_changes: list[dict[str, Any]] = []
        self.created_at = time.time()

    @property
    def state(self) -> dict[str, Any]:
        return copy.deepcopy(self._working_state)

    def apply(self, changes: dict[str, Any]) -> None:
        """Apply changes to the sandbox state."""
        self._applied_changes.append(changes)
        self._deep_update(self._working_state, changes)

    def reset(self) -> None:
        """Reset sandbox to base state."""
        self._working_state = copy.deepcopy(self._base_state)
        self._applied_changes = []

    def snapshot(self) -> dict[str, Any]:
        """Take a snapshot of the current sandbox state."""
        return copy.deepcopy(self._working_state)

    @staticmethod
    def _deep_update(base: dict[str, Any], updates: dict[str, Any]) -> None:
        """Recursively update nested dicts."""
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                Sandbox._deep_update(base[key], value)
            else:
                base[key] = value


# ---------------------------------------------------------------------------
# Rollback Manager
# ---------------------------------------------------------------------------


class RollbackManager:
    """Manages checkpoints and rollback operations."""

    def __init__(self, max_checkpoints: int = 10) -> None:
        self._checkpoints: list[Checkpoint] = []
        self._max_checkpoints = max_checkpoints

    def create_checkpoint(
        self,
        state: dict[str, Any],
        label: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Checkpoint:
        """Create a new checkpoint from the given state."""
        checkpoint_id = f"ckpt-{len(self._checkpoints)}-{int(time.time() * 1000)}"
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            state=copy.deepcopy(state),
            label=label or f"checkpoint-{len(self._checkpoints)}",
            metadata=metadata or {},
        )
        self._checkpoints.append(checkpoint)
        if len(self._checkpoints) > self._max_checkpoints:
            self._checkpoints.pop(0)
        return checkpoint

    def rollback(self, checkpoint_id: str | None = None) -> Checkpoint | None:
        """Rollback to a checkpoint. If no id given, rollback to the latest."""
        if not self._checkpoints:
            return None

        if checkpoint_id is None:
            return self._checkpoints[-1]

        for i, ckpt in enumerate(self._checkpoints):
            if ckpt.checkpoint_id == checkpoint_id:
                # Remove all checkpoints after this one
                self._checkpoints = self._checkpoints[: i + 1]
                return ckpt

        return None

    def latest(self) -> Checkpoint | None:
        """Get the latest checkpoint."""
        return self._checkpoints[-1] if self._checkpoints else None

    def list_checkpoints(self) -> list[Checkpoint]:
        """List all checkpoints."""
        return list(self._checkpoints)

    def __len__(self) -> int:
        return len(self._checkpoints)


# ---------------------------------------------------------------------------
# Evolution Loop
# ---------------------------------------------------------------------------


class EvolutionLoop:
    """The main evolution loop.

    Observes weakness → hypothesis → sandbox → benchmark → safety gate → promote/rollback

    Usage:
        loop = EvolutionLoop(initial_state={"strategy": {"temperature": 0.5}})
        loop.set_benchmark_fn(my_benchmark)
        loop.set_hypothesis_fn(my_hypothesis_gen)
        loop.set_safety_fn(my_safety_check)
        result = loop.run(max_iterations=10)
    """

    def __init__(
        self,
        initial_state: dict[str, Any] | None = None,
        max_iterations: int = 100,
        promotion_threshold: float = 0.01,
        rollback_threshold: float = -0.05,
        safety_required: bool = True,
    ) -> None:
        self.state = EvolutionState(current_strategy=initial_state or {})
        self.rollback_manager = RollbackManager()
        self.max_iterations = max_iterations
        self.promotion_threshold = promotion_threshold
        self.rollback_threshold = rollback_threshold
        self.safety_required = safety_required

        # Callables
        self._benchmark_fn: Callable[[dict[str, Any]], float] | None = None
        self._hypothesis_fn: Callable[[EvolutionState], Hypothesis | None] | None = None
        self._safety_fn: Callable[[dict[str, Any]], tuple[bool, list[str]]] | None = None

    def set_benchmark_fn(self, fn: Callable[[dict[str, Any]], float]) -> None:
        """Set the benchmark function. Takes state, returns score."""
        self._benchmark_fn = fn

    def set_hypothesis_fn(self, fn: Callable[[EvolutionState], Hypothesis | None]) -> None:
        """Set the hypothesis generation function."""
        self._hypothesis_fn = fn

    def set_safety_fn(self, fn: Callable[[dict[str, Any]], tuple[bool, list[str]]]) -> None:
        """Set the safety validation function."""
        self._safety_fn = fn

    def run(self, max_iterations: int | None = None) -> dict[str, Any]:
        """Run the evolution loop.

        Returns a summary of the run.
        """
        max_iter = max_iterations or self.max_iterations

        # Create initial checkpoint
        self.rollback_manager.create_checkpoint(
            self.state.current_strategy, label="initial"
        )

        # Benchmark initial state
        if self._benchmark_fn:
            self.state.current_score = self._benchmark_fn(self.state.current_strategy)
            self.state.best_score = self.state.current_score

        for i in range(max_iter):
            self.state.generation = i + 1

            # 1. Observe and generate hypothesis
            if self._hypothesis_fn is None:
                break
            hypothesis = self._hypothesis_fn(self.state)
            if hypothesis is None:
                break

            # 2. Test in sandbox
            result = self._test_hypothesis(hypothesis)
            self.state.record_result(result)

            # 3. Safety gate and promote/rollback
            if result.promoted and result.improvement >= self.promotion_threshold:
                self._promote(hypothesis, result)
            elif result.improvement <= self.rollback_threshold:
                self._rollback()
            # else: neutral result, continue

        return self.state.summary()

    def _test_hypothesis(self, hypothesis: Hypothesis) -> HypothesisResult:
        """Test a hypothesis in a sandbox."""
        sandbox_id = f"sbox-{int(time.time() * 1000)}"
        sandbox = Sandbox(sandbox_id, self.state.current_strategy)
        sandbox.apply(hypothesis.changes)

        # Safety check
        safety_passed = True
        safety_violations: list[str] = []
        if self._safety_fn and self.safety_required:
            safety_passed, safety_violations = self._safety_fn(sandbox.state)

        # Benchmark
        score_before = self.state.current_score
        score_after = score_before
        error = ""

        if self._benchmark_fn:
            try:
                score_after = self._benchmark_fn(sandbox.state)
            except Exception as exc:  # noqa: BLE001
                error = str(exc)
                score_after = 0.0

        improvement = score_after - score_before

        return HypothesisResult(
            hypothesis=hypothesis,
            success=error == "",
            score_before=score_before,
            score_after=score_after,
            improvement=improvement,
            safety_passed=safety_passed,
            sandbox_id=sandbox_id,
            error=error,
            details={"safety_violations": safety_violations},
        )

    def _promote(self, hypothesis: Hypothesis, result: HypothesisResult) -> None:
        """Promote a hypothesis: apply to production state."""
        # Create checkpoint before promoting
        self.rollback_manager.create_checkpoint(
            self.state.current_strategy,
            label=f"pre-promote-{hypothesis.hypothesis_id}",
        )
        sandbox = Sandbox("promote", self.state.current_strategy)
        sandbox.apply(hypothesis.changes)
        self.state.current_strategy = sandbox.state
        self.state.current_score = result.score_after
        if self.state.current_score > self.state.best_score:
            self.state.best_score = self.state.current_score

    def _rollback(self) -> None:
        """Rollback to the last checkpoint."""
        checkpoint = self.rollback_manager.rollback()
        if checkpoint is not None:
            self.state.current_strategy = copy.deepcopy(checkpoint.state)
            self.state.total_rollbacks += 1

    def inject_hypothesis(
        self,
        description: str,
        changes: dict[str, Any],
        target_module: str = "strategy",
        expected_improvement: float = 0.1,
    ) -> HypothesisResult:
        """Manually inject and test a hypothesis."""
        hypothesis = Hypothesis(
            hypothesis_id=f"inj-{int(time.time() * 1000)}",
            description=description,
            target_module=target_module,
            changes=changes,
            expected_improvement=expected_improvement,
        )
        result = self._test_hypothesis(hypothesis)
        self.state.record_result(result)
        return result
