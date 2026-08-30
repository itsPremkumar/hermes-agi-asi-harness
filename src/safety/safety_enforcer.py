"""Safety Enforcer — enforce safety policies and block dangerous operations.

Part of the Advanced Safety Module. A :class:`SafetyEnforcer` evaluates a
:class:`SafetyPolicy` against an operation (or a list of detected threats) and
returns an :class:`EnforcementResult` describing whether the operation is
allowed, blocked, or requires escalation.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from safety.risk_assessor import Risk, RiskLevel, RiskProfile

logger = logging.getLogger(__name__)

__all__ = [
    "PolicyAction",
    "EnforcementResult",
    "SafetyPolicy",
    "SafetyEnforcer",
]


class PolicyAction(Enum):
    """Outcome of applying a safety policy."""

    ALLOW = "allow"
    BLOCK = "block"
    ESCALATE = "escalate"


@dataclass
class EnforcementResult:
    """Result of enforcing a policy on a request."""

    allowed: bool
    action: PolicyAction
    risk_level: RiskLevel
    reason: str = ""
    violations: list[str] = field(default_factory=list)
    blocked_rules: list[str] = field(default_factory=list)
    risk_score: float = 0.0
    evaluated_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.allowed and self.action in (PolicyAction.ALLOW, PolicyAction.ESCALATE)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "action": self.action.value,
            "risk_level": self.risk_level.value,
            "reason": self.reason,
            "violations": list(self.violations),
            "blocked_rules": list(self.blocked_rules),
            "evaluated_at": self.evaluated_at,
        }


@dataclass
class SafetyPolicy:
    """Declarative safety policy.

    A policy maps a :class:`RiskLevel` to a :class:`PolicyAction` and an
    ordered list of predicate rules.  The most-specific applicable rule
    (highest risk level whose threshold is met) wins.
    """

    name: str
    description: str = ""
    # risk level -> action (None means "inherit default")
    level_actions: dict[RiskLevel, PolicyAction] = field(default_factory=lambda: {
        RiskLevel.NONE: PolicyAction.ALLOW,
        RiskLevel.LOW: PolicyAction.ALLOW,
        RiskLevel.MEDIUM: PolicyAction.ALLOW,
        RiskLevel.HIGH: PolicyAction.ESCALATE,
        RiskLevel.CRITICAL: PolicyAction.BLOCK,
    })
    # Ordered list of explicit predicate rules.
    rules: list[Callable[[RiskProfile, Risk], PolicyAction | None]] = field(default_factory=list)
    default_action: PolicyAction = PolicyAction.ALLOW
    max_risk_score: float = 1.0  # hard ceiling; anything above is BLOCK regardless.
    escalate_threshold: float = 0.6  # scores above this escalate unless blocked.
    block_threshold: float = 0.85  # scores above this are blocked.
    human_approval_required: bool = True
    enabled: bool = True

    def add_rule(self, rule: Callable[[RiskProfile, Risk], PolicyAction | None]) -> None:
        self.rules.append(rule)

    def evaluate_risk(self, profile: RiskProfile, risk: Risk) -> PolicyAction:
        """Evaluate a single *risk* against this policy."""
        # Explicit rules take priority.
        for rule in self.rules:
            result = rule(profile, risk)
            if result is not None:
                return result

        # Hard ceiling.
        if risk.score > self.max_risk_score or risk.score >= self.block_threshold:
            return PolicyAction.BLOCK

        # Level-based mapping.
        action = self.level_actions.get(risk.level)
        if action is not None:
            return action

        # Score thresholds.
        if risk.score >= self.block_threshold:
            return PolicyAction.BLOCK
        if risk.score >= self.escalate_threshold:
            return PolicyAction.ESCALATE
        return PolicyAction.ALLOW

    def evaluate_profile(self, profile: RiskProfile) -> PolicyAction:
        """Evaluate the *overall* profile risk, returning the strictest action."""
        if not profile.risks:
            return PolicyAction.ALLOW
        actions = [self.evaluate_risk(profile, r) for r in profile.risks]
        # BLOCK dominates, then ESCALATE, then ALLOW.
        if PolicyAction.BLOCK in actions:
            return PolicyAction.BLOCK
        if PolicyAction.ESCALATE in actions:
            return PolicyAction.ESCALATE
        return PolicyAction.ALLOW


class SafetyEnforcer:
    """Enforces a set of safety policies against risk profiles."""

    def __init__(self, policies: list[SafetyPolicy] | None = None) -> None:
        self._policies: list[SafetyPolicy] = list(policies or [])
        self._blocked_log: list[EnforcementResult] = []
        self._allowed_log: list[EnforcementResult] = []

        if not self._policies:
            self._policies.append(self.default_policy())

    @staticmethod
    def default_policy() -> SafetyPolicy:
        policy = SafetyPolicy(
            name="default-safety-policy",
            description="Default allow-escalate-block policy for AGI/ASI operations.",
        )
        # Rule: any CRITICAL-severity threat is blocked immediately.
        def block_critical(_profile: RiskProfile, risk: Risk) -> PolicyAction | None:
            if risk.level == RiskLevel.CRITICAL:
                return PolicyAction.BLOCK
            return None

        policy.add_rule(block_critical)
        return policy

    def add_policy(self, policy: SafetyPolicy) -> None:
        self._policies.append(policy)

    def get_policy(self, name: str) -> SafetyPolicy | None:
        for p in self._policies:
            if p.name == name:
                return p
        return None

    def enforce(self, profile: RiskProfile, risk: Risk | None = None) -> EnforcementResult:
        """Enforce all policies against *profile* (and optionally a single *risk*).

        When *risk* is provided the action is computed for that risk; otherwise
        the strictest action across the whole profile is used.
        """
        enabled = [p for p in self._policies if p.enabled]
        if not enabled:
            result = EnforcementResult(
                allowed=True,
                action=PolicyAction.ALLOW,
                risk_level=profile.overall_level,
                reason="No enabled policies",
            )
            self._allowed_log.append(result)
            return result

        if risk is not None:
            actions = [p.evaluate_risk(profile, risk) for p in enabled]
            target_risk = risk
        else:
            actions = [p.evaluate_profile(profile) for p in enabled]
            target_risk = Risk(
                risk_id="profile",
                threat_id="aggregate",
                category="aggregate",
                description=profile.target_system,
                score=profile.overall_score,
                level=profile.overall_level,
                likelihood=1.0,
                impact="",
            )

        # Aggregate: BLOCK wins, then ESCALATE, then ALLOW.
        if PolicyAction.BLOCK in actions:
            action = PolicyAction.BLOCK
        elif PolicyAction.ESCALATE in actions:
            action = PolicyAction.ESCALATE
        else:
            action = PolicyAction.ALLOW

        allowed = action in (PolicyAction.ALLOW, PolicyAction.ESCALATE)
        violations: list[str] = []
        blocked_rules: list[str] = []
        reason_parts: list[str] = []
        for p, a in zip(enabled, actions):
            if a == PolicyAction.BLOCK:
                blocked_rules.append(p.name)
            if not allowed:
                violations.append(f"{p.name}: {a.value}")
            reason_parts.append(f"{p.name}={a.value}")

        reason = "; ".join(reason_parts) if reason_parts else "policy satisfied"

        result = EnforcementResult(
            allowed=allowed,
            action=action,
            risk_level=target_risk.level,
            reason=reason,
            violations=violations,
            blocked_rules=blocked_rules,
            risk_score=target_risk.score,
            metadata={"policy_count": len(enabled)},
        )

        if allowed:
            self._allowed_log.append(result)
        else:
            self._blocked_log.append(result)

        logger.info(
            "Enforced policy: action=%s allowed=%s risk_level=%s",
            action.value, allowed, target_risk.level.value,
        )
        return result

    def is_operation_safe(self, profile: RiskProfile) -> bool:
        """Convenience: True if the overall profile is allowed by policy."""
        return self.enforce(profile).allowed

    @property
    def blocked_log(self) -> list[EnforcementResult]:
        return list(self._blocked_log)

    @property
    def allowed_log(self) -> list[EnforcementResult]:
        return list(self._allowed_log)

    def clear_logs(self) -> None:
        self._blocked_log.clear()
        self._allowed_log.clear()
