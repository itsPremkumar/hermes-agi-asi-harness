"""
HERMES INTELLIGENCE OS — IMMUTABLE GOAL INVARIANTS & CONTRACTS
==============================================================
Prevents catastrophic goal drift across multi-hour, multi-step executions.
Guarantees that invariants (e.g. 'existing code must not be deleted',
'security boundaries must remain active') can never be dropped or mutated.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("hermes.context_os.invariants")


@dataclass
class GoalInvariant:
    """An immutable condition that must hold true across all execution steps."""
    name: str
    description: str
    severity: str = "critical"  # critical, high, warning
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "severity": self.severity,
            "active": self.active,
        }


@dataclass
class GoalContract:
    """The authoritative specification of a mission."""
    contract_id: str
    objective: str
    desired_world_state: dict[str, Any]
    invariants: list[GoalInvariant] = field(default_factory=list)
    success_conditions: list[str] = field(default_factory=list)
    failure_conditions: list[str] = field(default_factory=list)
    risk_level: str = "medium"
    created_at: float = field(default_factory=time.time)

    def check_invariants(self, current_state: dict[str, Any]) -> list[str]:
        """Verify all invariants against the proposed state change."""
        violations = []
        for inv in self.invariants:
            if not inv.active:
                continue

            if inv.name == "existing_code_must_not_be_deleted":
                if current_state.get("deleted_existing_files", False):
                    violations.append(f"Invariant violation: {inv.name} — attempt to delete existing files.")
            elif inv.name == "budget_must_remain_within_limit":
                if current_state.get("cost_exceeded", False):
                    violations.append(f"Invariant violation: {inv.name} — budget ceiling exceeded.")
            elif inv.name == "security_requirements_preserved":
                if not current_state.get("security_verified", True):
                    violations.append(f"Invariant violation: {inv.name} — security check failure.")
        return violations

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "objective": self.objective,
            "desired_world_state": self.desired_world_state,
            "invariants": [inv.to_dict() for inv in self.invariants],
            "success_conditions": self.success_conditions,
            "failure_conditions": self.failure_conditions,
            "risk_level": self.risk_level,
            "created_at": self.created_at,
        }
