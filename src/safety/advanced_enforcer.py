"""Advanced Safety Enforcer.

Dynamic safety rules, threat modeling, risk assessment,
and automatic incident response.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


@dataclass
class SafetyRule:
    rule_id: str
    name: str
    description: str
    risk_level: RiskLevel
    enabled: bool = True
    action: str = "block"  # block, warn, log
    condition: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class Incident:
    incident_id: str
    title: str
    description: str
    risk_level: RiskLevel
    status: IncidentStatus = IncidentStatus.OPEN
    created_at: float = field(default_factory=time.time)
    resolved_at: float | None = None
    resolution: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ThreatModel:
    model_id: str
    name: str
    threats: list[dict[str, Any]] = field(default_factory=list)
    mitigations: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


class AdvancedSafetyEnforcer:
    """Advanced safety enforcer with dynamic rules."""

    def __init__(self):
        self._rules: dict[str, SafetyRule] = {}
        self._incidents: dict[str, Incident] = {}
        self._threat_models: dict[str, ThreatModel] = {}
        self._lock = threading.RLock()
        self._action_log: list[dict[str, Any]] = []

    def add_rule(self, rule: SafetyRule) -> None:
        """Add a safety rule."""
        with self._lock:
            self._rules[rule.rule_id] = rule

    def remove_rule(self, rule_id: str) -> None:
        """Remove a safety rule."""
        with self._lock:
            self._rules.pop(rule_id, None)

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a safety rule."""
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule:
                rule.enabled = True
                return True
            return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a safety rule."""
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule:
                rule.enabled = False
                return True
            return False

    def check_action(self, action_type: str, context: dict[str, Any]) -> dict[str, Any]:
        """Check if an action is safe."""
        with self._lock:
            violations = []
            for rule in self._rules.values():
                if not rule.enabled:
                    continue
                if self._evaluate_rule(rule, action_type, context):
                    violations.append({
                        "rule_id": rule.rule_id,
                        "rule_name": rule.name,
                        "risk_level": rule.risk_level.value,
                        "action": rule.action,
                    })
                    self._action_log.append({
                        "timestamp": time.time(),
                        "action_type": action_type,
                        "rule_id": rule.rule_id,
                        "result": rule.action,
                    })

            if violations:
                max_risk = max(
                    (RiskLevel(v["risk_level"]) for v in violations),
                    key=lambda r: ["low", "medium", "high", "critical"].index(r.value),
                )
                return {
                    "allowed": False,
                    "violations": violations,
                    "max_risk": max_risk.value,
                    "action": "block",
                }

            return {"allowed": True, "violations": [], "max_risk": "low", "action": "allow"}

    def report_incident(self, incident: Incident) -> None:
        """Report a safety incident."""
        with self._lock:
            self._incidents[incident.incident_id] = incident

    def resolve_incident(self, incident_id: str, resolution: str) -> bool:
        """Resolve an incident."""
        with self._lock:
            incident = self._incidents.get(incident_id)
            if not incident:
                return False
            incident.status = IncidentStatus.RESOLVED
            incident.resolved_at = time.time()
            incident.resolution = resolution
            return True

    def escalate_incident(self, incident_id: str) -> bool:
        """Escalate an incident."""
        with self._lock:
            incident = self._incidents.get(incident_id)
            if not incident:
                return False
            incident.status = IncidentStatus.ESCALATED
            return True

    def create_threat_model(self, model: ThreatModel) -> None:
        """Create a threat model."""
        with self._lock:
            self._threat_models[model.model_id] = model

    def assess_risk(self, action_type: str, context: dict[str, Any]) -> dict[str, Any]:
        """Assess risk of an action."""
        with self._lock:
            risk_scores = {"low": 0, "medium": 1, "high": 2, "critical": 3}
            max_score = 0
            risks = []
            has_block = False

            for rule in self._rules.values():
                if not rule.enabled:
                    continue
                if self._evaluate_rule(rule, action_type, context):
                    score = risk_scores.get(rule.risk_level.value, 0)
                    if score > max_score:
                        max_score = score
                    if rule.action == "block":
                        has_block = True
                    risks.append({
                        "rule": rule.name,
                        "level": rule.risk_level.value,
                    })

            levels = {v: k for k, v in risk_scores.items()}
            if has_block:
                recommendation = "block"
            elif max_score == 0:
                recommendation = "allow"
            else:
                recommendation = "warn"
            return {
                "risk_level": levels.get(max_score, "low"),
                "risks": risks,
                "recommendation": recommendation,
            }

    def get_incidents(self, status: IncidentStatus | None = None) -> list[Incident]:
        """Get incidents."""
        with self._lock:
            incidents = list(self._incidents.values())
            if status:
                incidents = [i for i in incidents if i.status == status]
            return incidents

    def get_rules(self) -> list[SafetyRule]:
        """Get all rules."""
        with self._lock:
            return list(self._rules.values())

    def get_action_log(self) -> list[dict[str, Any]]:
        """Get action log."""
        with self._lock:
            return list(self._action_log)

    def get_stats(self) -> dict[str, Any]:
        """Get safety stats."""
        with self._lock:
            return {
                "total_rules": len(self._rules),
                "enabled_rules": sum(1 for r in self._rules.values() if r.enabled),
                "total_incidents": len(self._incidents),
                "open_incidents": sum(1 for i in self._incidents.values() if i.status == IncidentStatus.OPEN),
                "escalated_incidents": sum(1 for i in self._incidents.values() if i.status == IncidentStatus.ESCALATED),
                "action_log_count": len(self._action_log),
            }

    def _evaluate_rule(self, rule: SafetyRule, action_type: str, context: dict[str, Any]) -> bool:
        """Evaluate a rule against an action."""
        # Simple evaluation: check if action_type matches condition
        if not rule.condition:
            return False
        return rule.condition in action_type
