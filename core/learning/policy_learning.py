"""
Policy Learning — Learn when tool X beats tool Y.

Policy Library: state + goal → policy → action
Learn from historical trajectories and replay results.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PolicySource(str, Enum):
    DEFAULT = "default"
    LEARNED = "learned"
    EVOLVED = "evolved"
    MANUAL = "manual"


@dataclass
class Policy:
    id: str
    name: str
    task_type: str
    conditions: Dict[str, Any]
    action_preferences: Dict[str, float]  # action → weight
    source: PolicySource
    created_at: float
    success_rate: float = 0.5
    total_uses: int = 0
    successful_uses: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyOutcome:
    policy_id: str
    task_type: str
    action_taken: str
    success: bool
    reward: float
    timestamp: float
    context: Dict[str, Any] = field(default_factory=dict)


class PolicyLearner:
    """Learn and improve action policies from experience."""

    def __init__(self):
        self.policies: Dict[str, Policy] = {}
        self.outcomes: List[PolicyOutcome] = []
        self._load_default_policies()

    def _load_default_policies(self):
        """Load default policies for common task types."""
        defaults = [
            Policy(
                id=str(uuid.uuid4()),
                name="file_operations",
                task_type="file_ops",
                conditions={"file_size_mb": "<10", "is_production": False},
                action_preferences={"python_tool": 0.7, "shell_tool": 0.3},
                source=PolicySource.DEFAULT,
                created_at=time.time(),
            ),
            Policy(
                id=str(uuid.uuid4()),
                name="deployment",
                task_type="deploy",
                conditions={"environment": "production"},
                action_preferences={"api_call": 0.6, "cli_tool": 0.4},
                source=PolicySource.DEFAULT,
                created_at=time.time(),
            ),
            Policy(
                id=str(uuid.uuid4()),
                name="research",
                task_type="research",
                conditions={"depth": "high"},
                action_preferences={"web_search": 0.5, "browser_tool": 0.3, "api_call": 0.2},
                source=PolicySource.DEFAULT,
                created_at=time.time(),
            ),
        ]
        for policy in defaults:
            self.policies[policy.id] = policy

    def select_action(self, task_type: str, context: Dict[str, Any]) -> Optional[str]:
        """Select best action for a task type given context."""
        matching = self._find_matching_policies(task_type, context)
        if not matching:
            return None

        # Pick policy with highest success rate
        best = max(matching, key=lambda p: p.success_rate)
        if not best.action_preferences:
            return None

        # Return action with highest weight
        return max(best.action_preferences, key=best.action_preferences.get)

    def record_outcome(self, policy_id: str, task_type: str, action_taken: str,
                       success: bool, reward: float = 0.0,
                       context: Dict[str, Any] = None) -> PolicyOutcome:
        """Record the outcome of using a policy."""
        outcome = PolicyOutcome(
            policy_id=policy_id,
            task_type=task_type,
            action_taken=action_taken,
            success=success,
            reward=reward,
            timestamp=time.time(),
            context=context or {},
        )
        self.outcomes.append(outcome)

        # Update policy stats
        policy = self.policies.get(policy_id)
        if policy:
            policy.total_uses += 1
            if success:
                policy.successful_uses += 1
            policy.success_rate = policy.successful_uses / policy.total_uses

        return outcome

    def learn_from_trajectories(self, trajectories: List[Any]):
        """Learn policies from historical trajectories."""
        for traj in trajectories:
            if traj.outcome != "success":
                continue
            
            task_type = traj.metadata.get("task_type", "unknown")
            matching = [p for p in self.policies.values() if p.task_type == task_type]
            
            for step in traj.steps:
                action = step.action.get("type", "unknown")
                for policy in matching:
                    if action in policy.action_preferences:
                        policy.action_preferences[action] += 0.1

    def _find_matching_policies(self, task_type: str,
                                 context: Dict[str, Any]) -> List[Policy]:
        """Find policies matching task type and context."""
        matching = []
        for policy in self.policies.values():
            if policy.task_type != task_type:
                continue
            
            # Check conditions
            match = True
            for key, value in policy.conditions.items():
                if key in context:
                    ctx_val = context[key]
                    if isinstance(value, str) and value.startswith("<"):
                        threshold = float(value[1:])
                        if isinstance(ctx_val, (int, float)) and ctx_val >= threshold:
                            match = False
                            break
                    elif ctx_val != value:
                        match = False
                        break
            
            if match:
                matching.append(policy)
        
        return matching

    def get_best_policy(self, task_type: str) -> Optional[Policy]:
        """Get the best-performing policy for a task type."""
        relevant = [p for p in self.policies.values() if p.task_type == task_type]
        if not relevant:
            return None
        return max(relevant, key=lambda p: p.success_rate * p.total_uses)

    def get_state(self) -> Dict[str, Any]:
        return {
            "policies": len(self.policies),
            "outcomes": len(self.outcomes),
            "learned": sum(1 for p in self.policies.values() if p.source == PolicySource.LEARNED),
            "evolved": sum(1 for p in self.policies.values() if p.source == PolicySource.EVOLVED),
        }
