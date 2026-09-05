"""
Consequence Simulator — Predict outcomes before acting.

Before high-impact actions:
  ACTION → SIMULATE → immediate consequence → second-order → third-order
           → failure scenarios → RISK/BENEFIT → EXECUTE or REJECT
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConsequenceType(str, Enum):
    IMMEDIATE = "immediate"
    SECOND_ORDER = "second_order"
    THIRD_ORDER = "third_order"
    FAILURE = "failure"
    SIDE_EFFECT = "side_effect"


class Severity(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ConsequencePrediction:
    type: ConsequenceType
    description: str
    probability: float  # 0.0 to 1.0
    severity: Severity
    affected_entities: list[str] = field(default_factory=list)
    verification_method: str = ""
    mitigation: str = ""
    timeframe_seconds: int = 0  # when this consequence is expected


@dataclass
class SimulationResult:
    action: str
    target: str
    predictions: list[ConsequencePrediction]
    overall_risk: float  # 0.0 to 1.0
    should_execute: bool
    requires_approval: bool
    timestamp: float
    confidence: float = 0.5
    alternatives_considered: list[str] = field(default_factory=list)


class ConsequenceSimulator:
    """
    Simulate consequences before executing actions.
    
    Uses a combination of:
    - Causal models (learned patterns)
    - Rule-based heuristics
    - Historical trajectories
    """

    def __init__(self):
        self._rules: list[dict[str, Any]] = []
        self._historical: list[dict[str, Any]] = []
        self._simulation_count = 0

    # ── Rule-Based Simulation ──────────────────────────────────────────────

    def add_rule(
        self,
        action_pattern: str,
        consequence_type: ConsequenceType,
        description: str,
        probability: float,
        severity: Severity,
        verification_method: str = "",
        mitigation: str = "",
    ):
        """Add a simulation rule."""
        self._rules.append({
            "id": str(uuid.uuid4()),
            "action_pattern": action_pattern,
            "consequence_type": consequence_type.value,
            "description": description,
            "probability": probability,
            "severity": severity.value,
            "verification_method": verification_method,
            "mitigation": mitigation,
        })

    def load_default_rules(self):
        """Load default simulation rules."""
        defaults = [
            {
                "action_pattern": "deploy",
                "consequence_type": ConsequenceType.IMMEDIATE.value,
                "description": "Service version changes; new code active",
                "probability": 1.0,
                "severity": Severity.MEDIUM.value,
                "verification_method": "health_check",
                "mitigation": "rollback",
            },
            {
                "action_pattern": "deploy",
                "consequence_type": ConsequenceType.FAILURE.value,
                "description": "Deployment fails; service may be partially updated",
                "probability": 0.15,
                "severity": Severity.HIGH.value,
                "verification_method": "deployment_status",
                "mitigation": "automatic_rollback",
            },
            {
                "action_pattern": "deploy",
                "consequence_type": ConsequenceType.SECOND_ORDER.value,
                "description": "Dependent services may experience changes in behavior",
                "probability": 0.3,
                "severity": Severity.MEDIUM.value,
                "verification_method": "dependent_service_health",
                "mitigation": "canary_rollout",
            },
            {
                "action_pattern": "delete",
                "consequence_type": ConsequenceType.IMMEDIATE.value,
                "description": "Entity is removed from system",
                "probability": 1.0,
                "severity": Severity.MEDIUM.value,
                "verification_method": "entity_removed",
                "mitigation": "restore_from_backup",
            },
            {
                "action_pattern": "delete",
                "consequence_type": ConsequenceType.SECOND_ORDER.value,
                "description": "Entities referencing this entity may break",
                "probability": 0.4,
                "severity": Severity.HIGH.value,
                "verification_method": "referential_integrity",
                "mitigation": "cascade_delete_or_reassign",
            },
            {
                "action_pattern": "send",
                "consequence_type": ConsequenceType.IMMEDIATE.value,
                "description": "Message/email is sent to recipient",
                "probability": 1.0,
                "severity": Severity.LOW.value,
                "verification_method": "ack_received",
                "mitigation": "correction_message",
            },
            {
                "action_pattern": "update",
                "consequence_type": ConsequenceType.IMMEDIATE.value,
                "description": "Entity state changes",
                "probability": 1.0,
                "severity": Severity.LOW.value,
                "verification_method": "state_match",
                "mitigation": "undo_update",
            },
            {
                "action_pattern": "update",
                "consequence_type": ConsequenceType.FAILURE.value,
                "description": "Update conflicts with concurrent modification",
                "probability": 0.1,
                "severity": Severity.MEDIUM.value,
                "verification_method": "version_check",
                "mitigation": "merge_conflict_resolution",
            },
            {
                "action_pattern": "execute",
                "consequence_type": ConsequenceType.IMMEDIATE.value,
                "description": "Code/command executes",
                "probability": 1.0,
                "severity": Severity.LOW.value,
                "verification_method": "exit_code",
                "mitigation": "manual_intervention",
            },
            {
                "action_pattern": "execute",
                "consequence_type": ConsequenceType.SIDE_EFFECT.value,
                "description": "Unintended side effects on system state",
                "probability": 0.2,
                "severity": Severity.MEDIUM.value,
                "verification_method": "state_diff",
                "mitigation": "sandbox_execution",
            },
        ]
        for rule in defaults:
            self._rules.append({**rule, "id": str(uuid.uuid4())})

    # ── Simulation ─────────────────────────────────────────────────────────

    def simulate(self, action: str, target: str,
                 context: dict[str, Any] | None = None) -> SimulationResult:
        """Run consequence simulation for an action."""
        self._simulation_count += 1
        predictions: list[ConsequencePrediction] = []

        # Match action against rules
        for rule in self._rules:
            if self._matches(action, rule["action_pattern"]):
                predictions.append(ConsequencePrediction(
                    type=ConsequenceType(rule["consequence_type"]),
                    description=rule["description"],
                    probability=rule["probability"],
                    severity=Severity(rule["severity"]),
                    affected_entities=[target],
                    verification_method=rule.get("verification_method", ""),
                    mitigation=rule.get("mitigation", ""),
                ))

        # Add context-based predictions
        if context:
            predictions.extend(self._context_predictions(action, target, context))

        # Calculate overall risk
        overall_risk = self._calculate_overall_risk(predictions)

        # Determine if execution should proceed
        should_execute = overall_risk < 0.7
        requires_approval = overall_risk >= 0.4

        return SimulationResult(
            action=action,
            target=target,
            predictions=predictions,
            overall_risk=overall_risk,
            should_execute=should_execute,
            requires_approval=requires_approval,
            timestamp=__import__("time").time(),
            confidence=0.6 if predictions else 0.2,
        )

    def _matches(self, action: str, pattern: str) -> bool:
        """Check if an action matches a pattern."""
        return pattern in action.lower() or action.lower() in pattern

    def _context_predictions(self, action: str, target: str,
                             context: dict[str, Any]) -> list[ConsequencePrediction]:
        """Generate predictions from context."""
        preds = []
        if context.get("is_production"):
            preds.append(ConsequencePrediction(
                type=ConsequenceType.SIDE_EFFECT,
                description="Production environment: change affects real users",
                probability=0.5,
                severity=Severity.HIGH,
                affected_entities=[target],
                mitigation="use_staging_first",
            ))
        if context.get("has_dependents"):
            preds.append(ConsequencePrediction(
                type=ConsequenceType.SECOND_ORDER,
                description=f"Target has {context['has_dependents']} dependents",
                probability=0.4,
                severity=Severity.MEDIUM,
                affected_entities=[],
                mitigation="check_dependents",
            ))
        return preds

    def _calculate_overall_risk(self, predictions: list[ConsequencePrediction]) -> float:
        """Calculate overall risk score from predictions."""
        if not predictions:
            return 0.5

        severity_map = {
            Severity.NONE: 0.0,
            Severity.LOW: 0.2,
            Severity.MEDIUM: 0.5,
            Severity.HIGH: 0.8,
            Severity.CRITICAL: 1.0,
        }

        risk_scores = []
        for pred in predictions:
            base = severity_map.get(pred.severity, 0.5)
            risk_scores.append(base * pred.probability)

        return min(1.0, sum(risk_scores) / max(1, len(risk_scores)))

    # ── Historical Learning ────────────────────────────────────────────────

    def record_outcome(self, action: str, target: str, predicted_risk: float,
                       actual_failure: bool, notes: str = ""):
        """Record actual outcome for learning."""
        self._historical.append({
            "action": action,
            "target": target,
            "predicted_risk": predicted_risk,
            "actual_failure": actual_failure,
            "notes": notes,
            "timestamp": __import__("time").time(),
        })

    def get_calibration(self) -> float:
        """How well do predicted risks match actual outcomes?"""
        if not self._historical:
            return 0.5
        # Simple: average of (1 - |predicted - actual|) for binary actual
        calibration_scores = []
        for h in self._historical:
            actual = 1.0 if h["actual_failure"] else 0.0
            calibration_scores.append(1.0 - abs(h["predicted_risk"] - actual))
        return sum(calibration_scores) / len(calibration_scores)

    # ── Query & Summary ────────────────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        return {
            "rules_count": len(self._rules),
            "simulations_run": self._simulation_count,
            "historical_outcomes": len(self._historical),
            "calibration": self.get_calibration(),
        }
