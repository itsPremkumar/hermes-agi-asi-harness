"""
Counterfactual Evaluation — Estimate what would have happened with different actions.

For each step in a trajectory, asks: what if we had done Z instead?
Uses historical data and simulation to estimate counterfactual outcomes.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class CounterfactualQuery:
    """A question about an alternative action."""
    trajectory_id: str
    step_number: int
    original_action: str
    alternative_action: str
    context: Dict[str, Any]


@dataclass
class CounterfactualResult:
    """Estimated outcome of a counterfactual action."""
    id: str
    query: CounterfactualQuery
    estimated_outcome: str  # success, failure, partial
    estimated_reward: float
    confidence: float
    timestamp: float
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class CounterfactualEvaluator:
    """
    Evaluate counterfactual scenarios from historical trajectories.
    
    Uses:
    - Similar past trajectories with different outcomes
    - Action-outcome correlation
    - Simulation estimates
    """

    def __init__(self):
        self.results: List[CounterfactualResult] = []
        self._action_outcomes: Dict[str, List[float]] = {}  # action → [rewards]

    def record_action_outcome(self, action: str, reward: float):
        """Record an outcome for correlation analysis."""
        if action not in self._action_outcomes:
            self._action_outcomes[action] = []
        self._action_outcomes[action].append(reward)

    def evaluate(self, query: CounterfactualQuery,
                 trajectory: Any = None,
                 simulator: Callable = None) -> CounterfactualResult:
        """Evaluate a counterfactual scenario."""
        # Estimate based on historical correlation
        estimated_reward = self._estimate_reward(query.alternative_action, query.context)
        
        # Refine with simulator if available
        confidence = 0.3
        reasoning = f"Historical average for '{query.alternative_action}': {estimated_reward:.2f}"
        
        if simulator:
            try:
                sim_result = simulator(query.alternative_action, query.context)
                sim_reward = sim_result.get('reward', estimated_reward)
                # Blend historical and simulated
                estimated_reward = (estimated_reward + sim_reward) / 2
                confidence = 0.6
                reasoning += f" | Simulated: {sim_reward:.2f}"
            except Exception:
                pass
        
        # Determine outcome label
        original_reward = self._estimate_reward(query.original_action, query.context)
        if estimated_reward > original_reward * 1.1:
            outcome = "better"
        elif estimated_reward < original_reward * 0.9:
            outcome = "worse"
        else:
            outcome = "similar"
        
        result = CounterfactualResult(
            id=str(uuid.uuid4()),
            query=query,
            estimated_outcome=outcome,
            estimated_reward=estimated_reward,
            confidence=confidence,
            timestamp=time.time(),
            reasoning=reasoning,
        )
        self.results.append(result)
        return result

    def _estimate_reward(self, action: str, context: Dict[str, Any]) -> float:
        """Estimate reward from historical data."""
        rewards = self._action_outcomes.get(action, [])
        if not rewards:
            return 0.0
        return sum(rewards) / len(rewards)

    def compare_actions(self, action_a: str, action_b: str,
                        context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Compare two actions based on historical performance."""
        reward_a = self._estimate_reward(action_a, context or {})
        reward_b = self._estimate_reward(action_b, context or {})
        
        return {
            "action_a": action_a,
            "reward_a": reward_a,
            "action_b": action_b,
            "reward_b": reward_b,
            "better": action_a if reward_a > reward_b else action_b,
            "delta": reward_a - reward_b,
        }

    def get_results(self, trajectory_id: str = None) -> List[CounterfactualResult]:
        if trajectory_id:
            return [r for r in self.results if r.query.trajectory_id == trajectory_id]
        return self.results

    def get_state(self) -> Dict[str, Any]:
        return {
            "evaluations": len(self.results),
            "actions_tracked": len(self._action_outcomes),
            "total_outcomes": sum(len(v) for v in self._action_outcomes.values()),
        }
