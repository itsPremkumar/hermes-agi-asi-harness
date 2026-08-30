"""
Affordance Model — What can Hermes do with each resource, and what happens next.

For every resource, Hermes constructs:
  WHAT CAN I DO WITH IT?
  WHAT HAPPENS IF I DO IT?
  WHAT CAN VERIFY THE RESULT?
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Reversibility(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    IMPOSSIBLE = "impossible"


class BlastRadius(str, Enum):
    LOW = "low"       # single file, single user
    MEDIUM = "medium"  # multi-file, single system
    HIGH = "high"      # multi-system
    CRITICAL = "critical"  # production, many users


@dataclass
class Consequence:
    type: str  # immediate, second_order, third_order, failure
    description: str
    probability: float = 0.5
    severity: float = 0.5
    entities_affected: List[str] = field(default_factory=list)


@dataclass
class Affordance:
    """What Hermes can do with a resource and what follows."""
    id: str
    resource_id: str
    action: str
    reversibility: Reversibility = Reversibility.HIGH
    blast_radius: BlastRadius = BlastRadius.LOW
    preconditions: List[str] = field(default_factory=list)
    consequences: List[Consequence] = field(default_factory=list)
    verification_methods: List[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    estimated_time_ms: int = 0
    required_permissions: List[str] = field(default_factory=list)
    compensation_action: Optional[str] = None  # for non-reversible actions


@dataclass
class AffordanceRule:
    """A pattern-based rule for generating affordances."""
    id: str
    resource_type: str
    action: str
    reversibility: Reversibility
    blast_radius: BlastRadius
    preconditions: List[str] = field(default_factory=list)
    verification_methods: List[str] = field(default_factory=list)
    compensation_action: Optional[str] = None


class AffordanceModel:
    """
    Model of what actions are possible and their likely consequences.
    
    This gives Hermes an explicit model of action possibilities
    instead of merely a list of tools.
    """

    # Default rules for common action types
    DEFAULT_RULES: List[AffordanceRule] = [
        AffordanceRule(
            id="rule-read", resource_type="*", action="read",
            reversibility=Reversibility.HIGH, blast_radius=BlastRadius.LOW,
            verification_methods=["checksum", "content_match"],
        ),
        AffordanceRule(
            id="rule-create", resource_type="*", action="create",
            reversibility=Reversibility.HIGH, blast_radius=BlastRadius.LOW,
            preconditions=["target_directory_exists"],
            verification_methods=["file_exists", "content_match"],
        ),
        AffordanceRule(
            id="rule-update", resource_type="*", action="update",
            reversibility=Reversibility.MEDIUM, blast_radius=BlastRadius.MEDIUM,
            preconditions=["entity_exists", "has_write_permission"],
            verification_methods=["content_match", "state_match", "no_error"],
        ),
        AffordanceRule(
            id="rule-delete", resource_type="*", action="delete",
            reversibility=Reversibility.LOW, blast_radius=BlastRadius.MEDIUM,
            preconditions=["entity_exists", "has_delete_permission"],
            verification_methods=["entity_removed", "no_longer_queryable"],
        ),
        AffordanceRule(
            id="rule-send", resource_type="*", action="send",
            reversibility=Reversibility.IMPOSSIBLE, blast_radius=BlastRadius.HIGH,
            preconditions=["has_network", "valid_target"],
            verification_methods=["ack_received"],
            compensation_action="send_correction_message",
        ),
        AffordanceRule(
            id="rule-deploy", resource_type="*", action="deploy",
            reversibility=Reversibility.LOW, blast_radius=BlastRadius.CRITICAL,
            preconditions=["tests_pass", "approval_received", "has_rollback_plan"],
            verification_methods=["health_check", "smoke_test", "no_regression"],
            compensation_action="rollback_deployment",
        ),
        AffordanceRule(
            id="rule-execute", resource_type="*", action="execute",
            reversibility=Reversibility.MEDIUM, blast_radius=BlastRadius.MEDIUM,
            preconditions=["has_execute_permission", "sandbox_available"],
            verification_methods=["exit_code_0", "expected_output", "no_side_effects"],
        ),
        AffordanceRule(
            id="rule-approve", resource_type="*", action="approve",
            reversibility=Reversibility.LOW, blast_radius=BlastRadius.HIGH,
            preconditions=["has_approval_permission", "within_delegated_scope"],
            verification_methods=["state_is_approved", "notification_sent"],
        ),
    ]

    def __init__(self):
        self.affordances: Dict[str, Affordance] = {}
        self.rules: Dict[str, AffordanceRule] = {r.id: r for r in self.DEFAULT_RULES}

    # ── Affordance Management ──────────────────────────────────────────────

    def add_affordance(self, resource_id: str, action: str,
                       reversibility: Reversibility = Reversibility.HIGH,
                       blast_radius: BlastRadius = BlastRadius.LOW,
                       preconditions: List[str] = None,
                       consequences: List[Consequence] = None,
                       verification_methods: List[str] = None,
                       required_permissions: List[str] = None,
                       compensation_action: str = None) -> Affordance:
        aff = Affordance(
            id=str(uuid.uuid4()),
            resource_id=resource_id,
            action=action,
            reversibility=reversibility,
            blast_radius=blast_radius,
            preconditions=preconditions or [],
            consequences=consequences or [],
            verification_methods=verification_methods or [],
            required_permissions=required_permissions or [],
            compensation_action=compensation_action,
        )
        self.affordances[aff.id] = aff
        return aff

    def get_affordances_for_resource(self, resource_id: str) -> List[Affordance]:
        return [a for a in self.affordances.values() if a.resource_id == resource_id]

    def get_affordances_for_action(self, action: str) -> List[Affordance]:
        return [a for a in self.affordances.values() if a.action == action]

    # ── Rule-Based Affordance Generation ───────────────────────────────────

    def add_rule(self, resource_type: str, action: str,
                 reversibility: Reversibility, blast_radius: BlastRadius,
                 preconditions: List[str] = None,
                 verification_methods: List[str] = None,
                 compensation_action: str = None) -> AffordanceRule:
        rule = AffordanceRule(
            id=f"rule-{action}-{resource_type}",
            resource_type=resource_type,
            action=action,
            reversibility=reversibility,
            blast_radius=blast_radius,
            preconditions=preconditions or [],
            verification_methods=verification_methods or [],
            compensation_action=compensation_action,
        )
        self.rules[rule.id] = rule
        return rule

    def generate_affordances_for_resource(
        self, resource_id: str, resource_type: str, capabilities: List[str]
    ) -> List[Affordance]:
        """Generate affordances for a resource based on rules and its capabilities."""
        generated = []
        for rule in self.rules.values():
            if rule.resource_type == "*" or rule.resource_type == resource_type:
                if rule.action in capabilities:
                    aff = self.add_affordance(
                        resource_id=resource_id,
                        action=rule.action,
                        reversibility=rule.reversibility,
                        blast_radius=rule.blast_radius,
                        preconditions=list(rule.preconditions),
                        verification_methods=list(rule.verification_methods),
                        compensation_action=rule.compensation_action,
                    )
                    generated.append(aff)
        return generated

    # ── Consequence Analysis ───────────────────────────────────────────────

    def add_consequence(self, affordance_id: str, type: str, description: str,
                         probability: float = 0.5, severity: float = 0.5,
                         entities_affected: List[str] = None) -> Optional[Consequence]:
        aff = self.affordances.get(affordance_id)
        if not aff:
            return None
        cons = Consequence(
            type=type,
            description=description,
            probability=probability,
            severity=severity,
            entities_affected=entities_affected or [],
        )
        aff.consequences.append(cons)
        return cons

    def get_risk_score(self, affordance_id: str) -> float:
        """Calculate risk score for an affordance."""
        aff = self.affordances.get(affordance_id)
        if not aff:
            return 1.0
        
        # Reversibility risk
        rev_risk = {
            Reversibility.HIGH: 0.1,
            Reversibility.MEDIUM: 0.4,
            Reversibility.LOW: 0.7,
            Reversibility.IMPOSSIBLE: 1.0,
        }
        
        # Blast radius risk
        blast_risk = {
            BlastRadius.LOW: 0.1,
            BlastRadius.MEDIUM: 0.4,
            BlastRadius.HIGH: 0.7,
            BlastRadius.CRITICAL: 1.0,
        }
        
        base_risk = (rev_risk.get(aff.reversibility, 0.5) + blast_risk.get(aff.blast_radius, 0.5)) / 2
        
        # Add consequence risk
        if aff.consequences:
            cons_risk = sum(c.probability * c.severity for c in aff.consequences) / len(aff.consequences)
            base_risk = (base_risk + cons_risk) / 2
        
        return min(1.0, base_risk)

    # ── Compensation ───────────────────────────────────────────────────────

    def get_compensation(self, affordance_id: str) -> Optional[str]:
        aff = self.affordances.get(affordance_id)
        if not aff:
            return None
        return aff.compensation_action

    def is_reversible(self, affordance_id: str) -> bool:
        aff = self.affordances.get(affordance_id)
        if not aff:
            return False
        return aff.reversibility in (Reversibility.HIGH, Reversibility.MEDIUM)

    # ── Query & Summary ────────────────────────────────────────────────────

    def get_state(self) -> Dict[str, Any]:
        return {
            "affordances_count": len(self.affordances),
            "rules_count": len(self.rules),
        }

    def get_irreversible_actions(self) -> List[Affordance]:
        return [a for a in self.affordances.values()
                if a.reversibility == Reversibility.IMPOSSIBLE]

    def get_high_risk_actions(self, threshold: float = 0.7) -> List[Affordance]:
        result = []
        for aff in self.affordances.values():
            if self.get_risk_score(aff.id) >= threshold:
                result.append(aff)
        return result
