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

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root
        self._blocked_commands = [
            # POSIX destruction
            r"rm\s+-rf\s+/",
            r"rm\s+-rf\s+~",
            r"mkfs",
            r":\(\)\s*\{\s*:\|:&\s*\};:",
            r"dd\s+if=/dev/zero",
            r"chmod\s+-R\s+777\s+/",
            r">\s*/dev/sda",
            r">\s*/dev/sd[a-z]",
            r"shutdown\s+-[hr]\s+now",
            # Windows PowerShell & CMD destruction
            r"Remove-Item\s+.*-(?:Recurse|Force).*(?:[Cc]:[\\/]|SystemRoot|windir)",
            r"del\s+/[sSfFqQ]\s+[cC]:\\",
            r"Format-Volume",
            r"Initialize-Disk",
            r"Clear-Disk",
            r"diskpart\s+/s",
            # In-memory execution cradles & downloaders
            r"iex\s*\(?(?:iwr|irm|Invoke-WebRequest|Invoke-RestMethod)",
            r"Invoke-Expression.*(?:Invoke-WebRequest|iwr|curl|wget)",
            r"powershell(?:\.exe)?\s+-[eE](?:nc|ncodedCommand)\s+[A-Za-z0-9+/=]{10,}",
            # Persistence & registry tampering
            r"(?:reg\s+add|Set-ItemProperty).*\\(?:CurrentVersion\\Run|Services)",
            # Sensitive file exfiltration & path traversal
            r"(?:\.\.[\\/]){2,}.*(?:etc[\\/](?:passwd|shadow)|Windows[\\/]System32[\\/]config[\\/]SAM|id_rsa|\.env)",
            r"(?:curl|wget)\s+.*(?:@|--data).*(?:id_rsa|\.env|passwd|shadow|SAM)",
            r"nc\s+.*-e\s+(?:/bin/sh|/bin/bash|cmd\.exe|powershell\.exe)",
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

        # 5. Executable 22-invariant gate (replaces dead strings)
        try:
            from .invariants import verify_invariants
            from pathlib import Path as _P
            kill = (_P(self.workspace_root) / ".hermes" / "KILL").exists()
            inv_state = {
                "action_type": action_type, "action_args": dict(action_args or {}),
                "principal": caller_identity, "taint_present": taint_present,
                "kill_switch": kill,
                "human_approved": bool((action_args or {}).get("human_approved")),
                "risk_level": str((action_args or {}).get("risk_level", "medium")),
                "goal_violations": [],
            }
            inv_res = verify_invariants(inv_state)
            if not inv_res.get("passed"):
                first = (inv_res.get("failures") or [{}])[0]
                reasons.append(f"Invariant {first.get('invariant')}: {first.get('reason')}")
                risk_score = 1.0
                self._record_audit(action_type, SafetyVerdict.BLOCK, risk_score, reasons, taint_present)
                return SafetyVerdict.BLOCK, "; ".join(reasons), risk_score
        except Exception as e:
            logger.debug("Invariant gate error (non-blocking): %s", e)

        # 6. Passed all checks
        self._record_audit(action_type, SafetyVerdict.ALLOW, risk_score, ["Action conforms to safety policies"], taint_present)
        return SafetyVerdict.ALLOW, "Authorized and safe", risk_score

    def verify_invariants(self, state: dict[str, Any]) -> dict[str, Any]:
        """Public entry: run all 22 executable invariants, return detailed report."""
        try:
            from .invariants import INVARIANTS, verify_invariants
            res = verify_invariants(state)
            res["invariant_names"] = [n for n, _ in INVARIANTS]
            return res
        except Exception as e:
            return {"passed": False, "failures": [{"invariant": "gate", "reason": str(e)}], "checked": 0}

    def engage_kill_switch(self, reason: str = "") -> str:
        from pathlib import Path as _P
        p = _P(self.workspace_root) / ".hermes" / "KILL"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(reason or "engaged", encoding="utf-8")
        return str(p)

    def release_kill_switch(self) -> bool:
        from pathlib import Path as _P
        p = _P(self.workspace_root) / ".hermes" / "KILL"
        try:
            if p.exists():
                p.unlink()
                return True
        except Exception:
            pass
        return False

    def kill_engaged(self) -> bool:
        from pathlib import Path as _P
        return (_P(self.workspace_root) / ".hermes" / "KILL").exists()

    def _record_audit(self, action_type: str, verdict: SafetyVerdict, risk: float, reasons: list[str], taint: bool):
        log = SafetyAuditLog(
            action_type=action_type,
            verdict=verdict,
            risk_score=risk,
            reasons=reasons,
            taint_present=taint,
        )
        self._audit_logs.append(log)

    def is_command_safe(self, cmd_str: str) -> tuple[bool, list[str]]:
        """Audit a shell/CLI command string directly against safety patterns."""
        reasons = []
        for pattern in self._blocked_commands:
            if re.search(pattern, cmd_str, re.IGNORECASE):
                reasons.append(f"Dangerous system command pattern detected: '{pattern}'")
        return len(reasons) == 0, reasons

    def get_audit_logs(self, limit: int = 50) -> list[SafetyAuditLog]:
        return self._audit_logs[-limit:]
