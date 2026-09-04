"""
HERMES INTELLIGENCE OS — PLANE 03: SAFETY & TRUST KERNEL
========================================================
Layered safety monitor operating outside primary agent authority.
Enforces:
- Taint tracking (trusted system directives vs untrusted inputs/web data)
- Asynchronous misalignment monitoring
- Risk-based gating (ALLOW, BLOCK, ESCALATE)
- Goal invariant compliance outside the reasoning loop
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from context_os.invariants import GoalContract

logger = logging.getLogger("hermes.os.safety_kernel")


class SafetyVerdict(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    ESCALATE = "escalate"


@dataclass
class TaintMarker:
    """Tracks the provenance and trust level of data flowing into cognition."""
    source_id: str
    trust_level: str  # trusted_system, authenticated_user, unverified_web, untrusted_tool
    is_tainted: bool = False
    taint_tags: list[str] = field(default_factory=list)


@dataclass
class SafetyAuditLog:
    action_type: str
    verdict: SafetyVerdict
    risk_score: float
    reasons: list[str]
    taint_present: bool
    timestamp: float = field(default_factory=time.time)


class SafetyKernel:
    """
    The external safety and trust kernel.
    Monitors all outbound actions and inbound observations.
    """

    def __init__(self):
        self._blocked_commands = [
            r"rm\s+-rf\s+/",
            r"mkfs",
            r":\(\)\s*\{\s*:\|:&\s*\};:",
            r"dd\s+if=/dev/zero",
            r"chmod\s+-R\s+777\s+/",
            r">\s*/dev/sda",
        ]
        self._audit_logs: list[SafetyAuditLog] = []
        self._tainted_entities: set[str] = set()

    def register_taint(self, source_id: str, tags: Optional[list[str]] = None) -> None:
        """Mark an entity or input source as tainted (untrusted)."""
        self._tainted_entities.add(source_id)

    def is_tainted(self, source_id: str) -> bool:
        return source_id in self._tainted_entities

    def evaluate_action(
        self,
        action_type: str,
        action_args: dict[str, Any],
        goal_contract: Optional[GoalContract] = None,
        caller_identity: str = "agent:worker",
    ) -> tuple[SafetyVerdict, str, float]:
        """
        Evaluate proposed action against safety policy, command filters,
        taint propagation, and goal invariants.
        Returns: (SafetyVerdict, explanation, risk_score).
        """
        reasons = []
        risk_score = 0.1

        # 1. Dangerous Command Regex Check
        cmd_str = str(action_args.get("command", "") or action_args.get("cmd", "") or action_args.get("code", ""))
        for pattern in self._blocked_commands:
            if re.search(pattern, cmd_str, re.IGNORECASE):
                reasons.append(f"Dangerous system command pattern detected: '{pattern}'")
                risk_score = 1.0
                self._record_audit(action_type, SafetyVerdict.BLOCK, risk_score, reasons, False)
                return SafetyVerdict.BLOCK, "; ".join(reasons), risk_score

        # 2. Destructive file operations check
        if action_type in ("delete_file", "drop_database", "truncate_table"):
            risk_score = max(risk_score, 0.8)
            reasons.append(f"Destructive action '{action_type}' requires escalation")
            self._record_audit(action_type, SafetyVerdict.ESCALATE, risk_score, reasons, False)
            return SafetyVerdict.ESCALATE, "; ".join(reasons), risk_score

        # 3. Taint check
        taint_present = any(self.is_tainted(str(v)) for v in action_args.values())
        if taint_present and action_type in ("execute_shell", "execute_python"):
            risk_score = max(risk_score, 0.75)
            reasons.append("Tainted data passed into arbitrary code execution environment")
            # Escalate or block if taint is uncontained
            self._record_audit(action_type, SafetyVerdict.BLOCK, risk_score, reasons, True)
            return SafetyVerdict.BLOCK, "; ".join(reasons), risk_score

        # 4. Goal Invariant Check
        if goal_contract:
            violations = goal_contract.check_invariants(action_args)
            if violations:
                reasons.extend(violations)
                risk_score = 0.95
                self._record_audit(action_type, SafetyVerdict.BLOCK, risk_score, reasons, taint_present)
                return SafetyVerdict.BLOCK, "; ".join(reasons), risk_score

        # 5. Passed all checks
        self._record_audit(action_type, SafetyVerdict.ALLOW, risk_score, ["Action conforms to safety policies"], taint_present)
        return SafetyVerdict.ALLOW, "Authorized and safe", risk_score

    def _record_audit(self, action_type: str, verdict: SafetyVerdict, risk: float, reasons: list[str], taint: bool):
        log = SafetyAuditLog(
            action_type=action_type,
            verdict=verdict,
            risk_score=risk,
            reasons=reasons,
            taint_present=taint,
        )
        self._audit_logs.append(log)

    def get_audit_logs(self, limit: int = 50) -> list[SafetyAuditLog]:
        return self._audit_logs[-limit:]
