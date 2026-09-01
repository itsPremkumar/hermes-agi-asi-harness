"""Safety Enforcer — Enforce safety policies and guardrails."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class PolicyAction(Enum):
    ALLOW = "allow"
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
class EnforcementResult:
    rule_id: str
    action: PolicyAction
    reason: str
    timestamp: float = field(default_factory=time.time)


class SafetyEnforcer:
    def __init__(self):
        self._rules: list[PolicyRule] = []

    def add_rule(self, rule: PolicyRule) -> None:
        self._rules.append(rule)

    def check(self, input_text: str) -> EnforcementResult | None:
        import re
        for rule in self._rules:
            if not rule.enabled:
                continue
            if re.search(rule.pattern, input_text, re.IGNORECASE):
                return EnforcementResult(
                    rule_id=rule.rule_id,
                    action=rule.action,
                    reason=f"Matched rule: {rule.name}",
                )
        return None

    def check_all(self, input_text: str) -> list[EnforcementResult]:
        import re
        results = []
        for rule in self._rules:
            if not rule.enabled:
                continue
            if re.search(rule.pattern, input_text, re.IGNORECASE):
                results.append(EnforcementResult(
                    rule_id=rule.rule_id,
                    action=rule.action,
                    reason=f"Matched rule: {rule.name}",
                ))
        return results
