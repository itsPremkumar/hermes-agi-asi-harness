"""
Policy Bridge — Connect Policy Learner to Action Selection.

Implements epsilon-greedy exploration vs exploitation.
Tracks policy usage and outcomes.
Handles policy versioning and rollback.
"""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PolicyUsageRecord:
    policy_id: str
    action: Dict[str, Any]
    success: bool
    reward: float
    timestamp: float
    exploration: bool


@dataclass
class PolicyVersion:
    id: str
    policy_id: str
    version: int
    preferences: Dict[str, float]
    created_at: float
    promoted: bool = False
    rollback_reason: Optional[str] = None


class PolicyBridge:
    """Bridge between Policy Learner and Action Execution."""
    
    def __init__(self, policy_learner: Any, epsilon: float = 0.1):
        self.policy_learner = policy_learner
        self.epsilon = epsilon
        self.usage_records: List[PolicyUsageRecord] = []
        self.policy_versions: List[PolicyVersion] = []
        self._version_counter: Dict[str, int] = {}
    
    def select_action_with_policy(self, goal: str, context: Dict[str, Any],
                                   explore: bool = True) -> tuple:
        """Select action using learned policy, with exploration."""
        task_type = context.get("task_type", "unknown")
        policy = self.policy_learner.get_best_policy(task_type)
        
        action = None
        is_exploration = False
        
        if explore and random.random() < self.epsilon:
            # Explore: random action
            action = self._random_action(context)
            is_exploration = True
        elif policy:
            # Exploit: use policy - result may be a string (action name)
            selected = self.policy_learner.select_action(task_type, context)
            if isinstance(selected, str):
                action = {"type": selected, "target": context.get("target", "unknown"), "timestamp": time.time()}
            else:
                action = selected or {}
            is_exploration = False
        else:
            # No policy found, use random
            action = self._random_action(context)
            is_exploration = True
        
        if action is None:
            action = self._random_action(context)
            is_exploration = True
        
        action["_exploration"] = is_exploration
        action["_policy_id"] = policy.id if policy else None
        
        return action, policy
    
    def _random_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a random action for exploration."""
        available = context.get("available_actions", ["read", "create", "update", "delete"])
        return {
            "type": random.choice(available),
            "target": context.get("target", "unknown"),
            "timestamp": time.time(),
        }
    
    def record_outcome(self, policy_id: str, action: Dict[str, Any],
                       success: bool, reward: float):
        """Feed outcome back to policy learner."""
        record = PolicyUsageRecord(
            policy_id=policy_id or "",
            action=action,
            success=success,
            reward=reward,
            timestamp=time.time(),
            exploration=action.get("_exploration", False),
        )
        self.usage_records.append(record)
        
        # Update policy learner
        if policy_id:
            self.policy_learner.record_outcome(
                policy_id,
                action.get("task_type", "unknown"),
                action.get("type", "unknown"),
                success,
                reward,
            )
    
    def create_policy_version(self, policy_id: str,
                               preferences: Dict[str, float]) -> PolicyVersion:
        """Create a new policy version."""
        version_num = self._version_counter.get(policy_id, 0) + 1
        self._version_counter[policy_id] = version_num
        
        version = PolicyVersion(
            id=str(uuid.uuid4()),
            policy_id=policy_id,
            version=version_num,
            preferences=preferences.copy(),
            created_at=time.time(),
        )
        self.policy_versions.append(version)
        return version
    
    def promote_version(self, version_id: str):
        """Promote a policy version."""
        for v in self.policy_versions:
            if v.id == version_id:
                v.promoted = True
                break
    
    def rollback_version(self, version_id: str, reason: str):
        """Rollback a policy version."""
        for v in self.policy_versions:
            if v.id == version_id:
                v.rollback_reason = reason
                break
    
    def get_exploration_rate(self) -> float:
        return self.epsilon
    
    def set_exploration_rate(self, epsilon: float):
        self.epsilon = max(0.0, min(1.0, epsilon))
    
    def get_stats(self) -> Dict[str, Any]:
        total = len(self.usage_records)
        if total == 0:
            return {"total": 0, "epsilon": self.epsilon}
        
        successes = sum(1 for r in self.usage_records if r.success)
        explorations = sum(1 for r in self.usage_records if r.exploration)
        
        return {
            "total": total,
            "successes": successes,
            "success_rate": successes / total,
            "explorations": explorations,
            "exploration_rate": explorations / total,
            "epsilon": self.epsilon,
            "versions": len(self.policy_versions),
            "promoted": sum(1 for v in self.policy_versions if v.promoted),
        }
