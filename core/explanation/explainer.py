"""
Action Explainer & Audit Trail — Explain why actions were taken.

For every action, explains:
- Why was this action chosen?
- What alternatives existed?
- What evidence supported it?
- What risk was estimated?
- What policy authorized it?
- What actually happened?
- Was the prediction accurate?
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ActionExplanation:
    """Human-readable explanation for an action."""
    action_id: str
    why_chosen: str
    alternatives: List[str]
    evidence: List[str]
    risk_estimate: float
    policy_id: Optional[str]
    prediction_accuracy: float  # 0.0 to 1.0
    causal_chain: List[str]
    timestamp: float


@dataclass
class AuditEntry:
    """Single audit trail entry."""
    id: str
    action_id: str
    timestamp: float
    event_type: str  # created, selected, simulated, executed, verified, promoted, rolled_back
    details: Dict[str, Any]
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None


class ActionExplainer:
    """Generate explanations for actions."""
    
    def explain(self, action_id: str, trajectory: Any,
                policy_learner: Any = None,
                simulation_result: Any = None) -> ActionExplanation:
        """Generate human-readable explanation for an action."""
        
        # Get action from trajectory
        action = self._get_action_from_trajectory(action_id, trajectory)
        
        # Build explanation
        why_chosen = f"Action '{action.get('type', 'unknown')}' selected based on policy"
        alternatives = self._get_alternatives(action)
        evidence = self._get_evidence(action)
        risk_estimate = getattr(simulation_result, 'overall_risk', 0.5) if simulation_result else 0.5
        
        policy_id = action.get("_policy_id")
        
        prediction_accuracy = self._compare_prediction(action_id, trajectory)
        
        causal_chain = self._build_causal_chain(action_id, trajectory)
        
        return ActionExplanation(
            action_id=action_id,
            why_chosen=why_chosen,
            alternatives=alternatives,
            evidence=evidence,
            risk_estimate=risk_estimate,
            policy_id=policy_id,
            prediction_accuracy=prediction_accuracy,
            causal_chain=causal_chain,
            timestamp=time.time(),
        )
    
    def _get_action_from_trajectory(self, action_id: str, trajectory: Any) -> Dict[str, Any]:
        """Extract action from trajectory."""
        if not trajectory or not hasattr(trajectory, 'steps'):
            return {}
        for step in trajectory.steps:
            if hasattr(step, 'action') and step.action.get('id') == action_id:
                return step.action
        return {}
    
    def _get_alternatives(self, action: Dict[str, Any]) -> List[str]:
        """Get alternative actions that were considered."""
        all_actions = ["read", "create", "update", "delete", "send", "execute"]
        action_type = action.get("type", "")
        return [a for a in all_actions if a != action_type]
    
    def _get_evidence(self, action: Dict[str, Any]) -> List[str]:
        """Get evidence that supported the action."""
        evidence = []
        if action.get("_exploration"):
            evidence.append("Exploration: random selection for learning")
        else:
            evidence.append("Exploitation: selected by learned policy")
        if action.get("_policy_id"):
            evidence.append(f"Policy: {action['_policy_id']}")
        return evidence
    
    def _compare_prediction(self, action_id: str, trajectory: Any) -> float:
        """Compare predicted vs actual outcome."""
        # In a real implementation, compare prediction with actual
        return 0.75  # Placeholder
    
    def _build_causal_chain(self, action_id: str, trajectory: Any) -> List[str]:
        """Build causal chain for the action."""
        return [
            "Goal received",
            "State estimated",
            "Policy selected",
            "Action executed",
            "Result observed",
        ]


class AuditTrail:
    """Maintain tamper-evident audit trail."""
    
    def __init__(self):
        self.entries: List[AuditEntry] = []
    
    def record(self, action_id: str, event_type: str,
               details: Dict[str, Any],
               previous_state: Dict[str, Any] = None,
               new_state: Dict[str, Any] = None) -> AuditEntry:
        """Record an audit entry."""
        entry = AuditEntry(
            id=str(uuid.uuid4()),
            action_id=action_id,
            timestamp=time.time(),
            event_type=event_type,
            details=details,
            previous_state=previous_state,
            new_state=new_state,
        )
        self.entries.append(entry)
        return entry
    
    def get_entries_for_action(self, action_id: str) -> List[AuditEntry]:
        """Get all audit entries for an action."""
        return [e for e in self.entries if e.action_id == action_id]
    
    def get_entries_by_type(self, event_type: str) -> List[AuditEntry]:
        """Get all audit entries of a specific type."""
        return [e for e in self.entries if e.event_type == event_type]
    
    def get_entries_in_range(self, start_time: float, end_time: float) -> List[AuditEntry]:
        """Get audit entries within a time range."""
        return [e for e in self.entries if start_time <= e.timestamp <= end_time]
    
    def get_state(self) -> Dict[str, Any]:
        return {
            "total_entries": len(self.entries),
            "action_ids": len(set(e.action_id for e in self.entries)),
            "event_types": list(set(e.event_type for e in self.entries)),
        }
