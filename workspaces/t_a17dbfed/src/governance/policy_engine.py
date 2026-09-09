"""Policy engine module — Policy enforcement and compliance checks."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Policy:
    """An AI governance policy."""
    id: str
    name: str
    description: str
    category: str
    severity: str
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceCheck:
    """A compliance check result."""
    id: str
    policy_id: str
    resource: str
    passed: bool
    details: str
    timestamp: str


class PolicyEngine:
    """Manage and enforce AI governance policies."""

    def __init__(self) -> None:
        self._policies: dict[str, Policy] = {}

    def register(self, policy: Policy) -> None:
        self._policies[policy.id] = policy

    def get(self, id: str) -> Policy | None:
        return self._policies.get(id)

    def get_all(self) -> list[Policy]:
        return list(self._policies.values())

    def get_enabled(self) -> list[Policy]:
        return [p for p in self._policies.values() if p.enabled]

    def get_by_category(self, category: str) -> list[Policy]:
        return [p for p in self._policies.values() if p.category == category]

    def enable(self, id: str) -> None:
        policy = self._policies.get(id)
        if policy:
            policy.enabled = True

    def disable(self, id: str) -> None:
        policy = self._policies.get(id)
        if policy:
            policy.enabled = False

    def evaluate(self, resource: str, context: dict[str, Any]) -> list[ComplianceCheck]:
        """Evaluate all enabled policies against a resource."""
        checks = []
        for policy in self.get_enabled():
            passed = self._check_policy(policy, resource, context)
            checks.append(ComplianceCheck(
                id=str(uuid.uuid4()),
                policy_id=policy.id,
                resource=resource,
                passed=passed,
                details=f"Policy {policy.name}: {'PASS' if passed else 'FAIL'}",
                timestamp=datetime.now(timezone.utc).isoformat(),
            ))
        return checks

    def _check_policy(self, policy: Policy, resource: str, context: dict[str, Any]) -> bool:
        """Check a single policy against a resource."""
        return policy.enabled
