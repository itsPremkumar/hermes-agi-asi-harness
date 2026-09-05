"""
Dynamic Decision Engine — Make real-time decisions based on scenario state.

Makes decisions about:
- Which modules to activate/deactivate
- When to switch strategies
- When to escalate or rollback
- How to allocate resources
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any

from core.dynamic.planning_engine import PlanStep, StepStatus, StepType
from core.dynamic.scenario_analyzer import ScenarioProfile


class DecisionType(str, Enum):
    STRATEGY_SWITCH = "strategy_switch"
    MODULE_ACTIVATION = "module_activation"
    RESOURCE_ALLOCATION = "resource_allocation"
    ESCALATION = "escalation"
    ROLLBACK = "rollback"
    PARALLELISM_CHANGE = "parallelism_change"
    QUALITY_GATE_ADJUSTMENT = "quality_gate_adjustment"
    SCOPE_CHANGE = "scope_change"


class DecisionUrgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Decision:
    id: str
    decision_type: DecisionType
    urgency: DecisionUrgency
    description: str
    rationale: str
    action: dict[str, Any]
    timestamp: float
    applied: bool = False


class DynamicDecisionEngine:
    """
    Make real-time decisions based on scenario state and execution progress.
    
    This engine continuously monitors execution and makes dynamic decisions
    to optimize the workflow.
    """
    
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.decisions: list[Decision] = []
    
    def evaluate_step_completion(self, step: PlanStep,
                                   result: Any) -> list[Decision]:
        """Evaluate a completed step and make decisions."""
        decisions = []
        
        if step.status == StepStatus.FAILED:
            decisions.extend(self._handle_failure(step, result))
        elif step.status == StepStatus.COMPLETED:
            decisions.extend(self._handle_success(step, result))
        
        return decisions
    
    def _handle_failure(self, step: PlanStep, result: Any) -> list[Decision]:
        """Handle step failure."""
        decisions = []
        
        # Decide whether to retry, skip, or escalate
        if step.step_type == "implementation" or step.step_type == StepType.IMPLEMENTATION:
            decisions.append(Decision(
                id=str(uuid.uuid4()),
                decision_type=DecisionType.STRATEGY_SWITCH,
                urgency=DecisionUrgency.HIGH,
                description=f"Implementation failed: {step.name}",
                rationale="Try alternative implementation approach",
                action={"type": "retry_with_alternative", "step_id": step.id},
                timestamp=0.0,
            ))
        elif step.step_type == "verification" or step.step_type == StepType.VERIFICATION:
            decisions.append(Decision(
                id=str(uuid.uuid4()),
                decision_type=DecisionType.ESCALATION,
                urgency=DecisionUrgency.HIGH,
                description=f"Verification failed: {step.name}",
                rationale="Escalate to human review",
                action={"type": "escalate", "step_id": step.id},
                timestamp=0.0,
            ))
        
        return decisions
    
    def _handle_success(self, step: PlanStep, result: Any) -> list[Decision]:
        """Handle step success."""
        decisions = []
        
        # Check if we can increase parallelism
        if step.step_type.value == "analysis":
            decisions.append(Decision(
                id=str(uuid.uuid4()),
                decision_type=DecisionType.PARALLELISM_CHANGE,
                urgency=DecisionUrgency.LOW,
                description=f"Analysis complete: {step.name}",
                rationale="Can increase parallelism for implementation",
                action={"type": "increase_parallelism", "step_id": step.id},
                timestamp=0.0,
            ))
        
        return decisions
    
    def should_switch_strategy(self, profile: ScenarioProfile,
                                 current_step: PlanStep,
                                 metrics: dict[str, Any]) -> Decision | None:
        """Determine if we should switch strategies."""
        failure_rate = metrics.get("failure_rate", 0.0)
        
        if failure_rate > 0.5:
            return Decision(
                id=str(uuid.uuid4()),
                decision_type=DecisionType.STRATEGY_SWITCH,
                urgency=DecisionUrgency.CRITICAL,
                description="High failure rate detected",
                rationale="Switch to more conservative strategy",
                action={"type": "switch_to_sequential"},
                timestamp=0.0,
            )
        
        return None
    
    def should_rollback(self, step: PlanStep, result: Any) -> Decision | None:
        """Determine if we should rollback."""
        if step.status == StepStatus.FAILED and step.step_type.value == "deployment":
            return Decision(
                id=str(uuid.uuid4()),
                decision_type=DecisionType.ROLLBACK,
                urgency=DecisionUrgency.CRITICAL,
                description="Deployment failed - rollback required",
                rationale="Automatic rollback to previous version",
                action={"type": "rollback", "step_id": step.id},
                timestamp=0.0,
            )
        
        return None
    
    def get_state(self) -> dict[str, Any]:
        return {
            "decisions": len(self.decisions),
            "applied": sum(1 for d in self.decisions if d.applied),
        }
