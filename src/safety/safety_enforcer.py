"""Safety Enforcer — Enforce safety policies and guardrails. Supports both old and new APIs."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class PolicyAction(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    ESCALATE = "escalate"
    DENY = "deny"
    WARN = "warn"
    LOG = "log"


@dataclass
class PolicyRule:
    rule_id: str
    name: str
    pattern: str
    action: PolicyAction
    description: str = ""
    enabled: bool = True


@dataclass
class SafetyPolicy:
    name: str
    level_actions: dict = field(default_factory=dict)
    block_threshold: float = 1.0
    max_risk_score: float = 1.0
    enabled: bool = True
    rules: list = field(default_factory=list)

    def add_rule(self, rule_fn: Callable) -> None:
        self.rules.append(rule_fn)


@dataclass
class EnforcementResult:
    allowed: bool = True
    action: PolicyAction = PolicyAction.ALLOW
    risk_level: Any = None
    reason: str = ""
    violations: list[str] = field(default_factory=list)
    rule_id: str = ""
    timestamp: float = field(default_factory=time.time)

    @property
    def success(self) -> bool:
        return self.allowed

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "action": self.action.value,
            "risk_level": self.risk_level.value if self.risk_level else None,
            "reason": self.reason,
            "violations": self.violations,
            "rule_id": self.rule_id,
            "timestamp": self.timestamp,
        }


class SafetyEnforcer:
    def __init__(self):
        self._rules: list[PolicyRule] = []
        self._policies: dict[str, SafetyPolicy] = {}
        self._blocked_log: list[EnforcementResult] = []
        self._allowed_log: list[EnforcementResult] = []
        # Add default policy
        default = SafetyPolicy(
            name="default-safety-policy",
            level_actions={
                "critical": PolicyAction.BLOCK,
                "high": PolicyAction.ESCALATE,
                "medium": PolicyAction.ALLOW,
                "low": PolicyAction.ALLOW,
                "none": PolicyAction.ALLOW,
            },
            block_threshold=0.8,
        )
        self._policies[default.name] = default

    def add_rule(self, rule: PolicyRule) -> None:
        """Add a rule (old API)."""
        self._rules.append(rule)

    def add_policy(self, policy: SafetyPolicy) -> None:
        """Add a policy (new API)."""
        self._policies[policy.name] = policy

    def get_policy(self, name: str) -> Optional[SafetyPolicy]:
        """Get a policy by name."""
        return self._policies.get(name)

    def enforce(self, profile: Any, risk: Any = None) -> EnforcementResult:
        """Enforce safety policies against a risk profile (new API)."""
        level = profile.overall_level.value if hasattr(profile, 'overall_level') else "none"
        score = profile.overall_score if hasattr(profile, 'overall_score') else 0.0

        # Check each policy
        for policy in self._policies.values():
            if not policy.enabled:
                continue

            # Check max risk score
            if score > policy.max_risk_score:
                result = EnforcementResult(
                    allowed=False,
                    action=PolicyAction.BLOCK,
                    risk_level=profile.overall_level,
                    reason=f"Risk score {score} exceeds max {policy.max_risk_score}",
                    violations=[f"max-risk-score-exceeded"],
                )
                self._blocked_log.append(result)
                return result

            # Check block threshold
            if score >= policy.block_threshold:
                result = EnforcementResult(
                    allowed=False,
                    action=PolicyAction.BLOCK,
                    risk_level=profile.overall_level,
                    reason=f"Risk score {score} exceeds threshold {policy.block_threshold}",
                    violations=[f"block-threshold-exceeded"],
                )
                self._blocked_log.append(result)
                return result

            # Check custom rules
            for rule_fn in policy.rules:
                if risk:
                    action = rule_fn(profile, risk)
                    if action:
                        allowed = action != PolicyAction.BLOCK
                        result = EnforcementResult(
                            allowed=allowed,
                            action=action,
                            risk_level=profile.overall_level,
                            reason=f"Custom rule triggered: {action.value}",
                        )
                        if allowed:
                            self._allowed_log.append(result)
                        else:
                            self._blocked_log.append(result)
                        return result

            # Check level actions
            level_action = policy.level_actions.get(level, PolicyAction.ALLOW)
            if level_action == PolicyAction.BLOCK:
                result = EnforcementResult(
                    allowed=False,
                    action=PolicyAction.BLOCK,
                    risk_level=profile.overall_level,
                    reason=f"Level {level} blocked by policy {policy.name}",
                    violations=[f"level-{level}-blocked"],
                )
                self._blocked_log.append(result)
                return result
            elif level_action == PolicyAction.ESCALATE:
                result = EnforcementResult(
                    allowed=True,
                    action=PolicyAction.ESCALATE,
                    risk_level=profile.overall_level,
                    reason=f"Level {level} escalated by policy {policy.name}",
                )
                self._allowed_log.append(result)
                return result

        # Default allow
        result = EnforcementResult(
            allowed=True,
            action=PolicyAction.ALLOW,
            risk_level=profile.overall_level,
            reason="default-safety-policy=allow",
        )
        self._allowed_log.append(result)
        return result

    def is_operation_safe(self, profile: Any) -> bool:
        """Check if an operation is safe."""
        level = profile.overall_level.value if hasattr(profile, 'overall_level') else "none"
        return level not in ("critical",)

    @property
    def blocked_log(self) -> list[EnforcementResult]:
        return self._blocked_log

    @property
    def allowed_log(self) -> list[EnforcementResult]:
        return self._allowed_log

    def clear_logs(self) -> None:
        self._blocked_log.clear()
        self._allowed_log.clear()

    def check(self, input_text: str) -> EnforcementResult | None:
        """Check input against rules (old API)."""
        import re
        for rule in self._rules:
            if not rule.enabled:
                continue
            if re.search(rule.pattern, input_text, re.IGNORECASE):
                return EnforcementResult(
                    allowed=(rule.action != PolicyAction.DENY),
                    action=rule.action,
                    reason=f"Matched rule: {rule.name}",
                )
        return None

    def check_all(self, input_text: str) -> list[EnforcementResult]:
        """Check input against all rules (old API)."""
        import re
        results = []
        for rule in self._rules:
            if not rule.enabled:
                continue
            if re.search(rule.pattern, input_text, re.IGNORECASE):
                results.append(EnforcementResult(
                    allowed=(rule.action != PolicyAction.DENY),
                    action=rule.action,
                    reason=f"Matched rule: {rule.name}",
                ))
        return results
