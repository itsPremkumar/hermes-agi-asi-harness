"""ARC-AGI-3 Strategy Optimizer — optimize solving strategies."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StrategyType(str, Enum):
    """Types of solving strategies."""
    GREEDY = "greedy"
    BACKTRACK = "backtrack"
    DYNAMIC_PROGRAMMING = "dynamic_programming"
    DIVIDE_AND_CONQUER = "divide_and_conquer"
    PATTERN_MATCH = "pattern_match"
    BRUTE_FORCE = "brute_force"
    HEURISTIC = "heuristic"
    HYBRID = "hybrid"


@dataclass
class Strategy:
    """A solving strategy."""
    id: str
    strategy_type: StrategyType
    name: str
    description: str
    success_rate: float = 0.0
    avg_time_ms: float = 0.0
    params: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyResult:
    """Result of applying a strategy."""
    strategy_id: str
    success: bool
    score: float = 0.0
    time_ms: float = 0.0
    steps: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class StrategyOptimizer:
    """Optimize strategies for ARC-AGI-3 tasks."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._strategies: dict[str, Strategy] = {}
        self._results: list[StrategyResult] = []

    def register_strategy(self, strategy_type: StrategyType, name: str,
                          description: str = "", params: dict[str, Any] | None = None) -> Strategy:
        """Register a new strategy."""
        strategy = Strategy(
            id=str(uuid.uuid4()),
            strategy_type=strategy_type,
            name=name,
            description=description,
            params=params or {},
        )
        self._strategies[strategy.id] = strategy
        return strategy

    def get_strategy(self, strategy_id: str) -> Strategy | None:
        """Get a strategy by ID."""
        return self._strategies.get(strategy_id)

    def list_strategies(self) -> list[Strategy]:
        """List all registered strategies."""
        return list(self._strategies.values())

    def evaluate(self, strategy_id: str, task_id: str, success: bool,
                 score: float = 0.0, time_ms: float = 0.0, steps: int = 0) -> StrategyResult:
        """Evaluate a strategy on a task."""
        result = StrategyResult(
            strategy_id=strategy_id,
            success=success,
            score=score,
            time_ms=time_ms,
            steps=steps,
        )
        self._results.append(result)

        # Update strategy stats
        if strategy_id in self._strategies:
            strategy = self._strategies[strategy_id]
            # Update success rate
            strategy_results = [r for r in self._results if r.strategy_id == strategy_id]
            if strategy_results:
                strategy.success_rate = sum(1 for r in strategy_results if r.success) / len(strategy_results)
                strategy.avg_time_ms = sum(r.time_ms for r in strategy_results) / len(strategy_results)

        return result

    def get_best_strategy(self) -> Strategy | None:
        """Get the best performing strategy."""
        if not self._strategies:
            return None
        return max(self._strategies.values(), key=lambda s: s.success_rate)

    def get_state(self) -> dict[str, Any]:
        return {
            "total_strategies": len(self._strategies),
            "total_evaluations": len(self._results),
            "best_strategy": self.get_best_strategy().name if self.get_best_strategy() else None,
        }
