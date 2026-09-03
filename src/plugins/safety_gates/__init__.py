"""
Safety Gates Plugin — R0 through R6 Risk-Based Verification Gates

Every meaningful action passes an appropriate gate:
R0=Parse, R1=Understand, R2=Validate, R3=Safety, R4=Execute, R5=Verify, R6=Commit/Publish
"""

import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GateResult:
    def __init__(self, passed: bool, gate: str, message: str, details: dict[str, Any] | None = None):
        self.passed = passed
        self.gate = gate
        self.message = message
        self.details = details or {}
        self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "gate": self.gate,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class SafetyGatesPlugin:
    """
    R0-R6 Safety and Verification Gates.

    Gate Definitions:
    - R0 (Parse): Input is syntactically valid
    - R1 (Understand): Intent is clear and unambiguous
    - R2 (Validate): Inputs meet schema/business rules
    - R3 (Safety): No unsafe actions detected
    - R4 (Execute): Action is authorized and permitted
    - R5 (Verify): Result meets acceptance criteria
    - R6 (Commit/Publish): Final human approval for high-risk actions
    """

    # Actions mapped to minimum required gate
    ACTION_GATES = {
        "read_file": "R1",
        "write_file": "R3",
        "modify_code": "R3",
        "delete_file": "R4",
        "execute_shell": "R3",
        "http_request": "R3",
        "send_message": "R4",
        "deploy": "R5",
        "spend_money": "R6",
        "publish": "R5",
        "database_write": "R3",
        "database_delete": "R4",
        "modify_safety_rules": "R6",
        "self_modify": "R6",
        "install_package": "R3",
        "access_private_data": "R4",
        "production_change": "R5",
    }

    # Patterns that trigger safety concerns
    DANGEROUS_PATTERNS = [
        r"rm\s+-rf",
        r"DELETE\s+FROM",
        r"DROP\s+TABLE",
        r"sudo\s+rm",
        r"format\s+c:",
        r"dd\s+if=",
        r"mkfs",
        r"shutdown\s+now",
        r":(){ :|:&};:",  # fork bomb
    ]

    def __init__(self):
        self._gate_log: list[GateResult] = []

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {"status": "healthy", "gate_checks": len(self._gate_log)}

    def check_gate(self, gate: str, action: str, context: dict[str, Any] | None = None) -> GateResult:
        """Run a specific gate check."""
        context = context or {}

        if gate == "R0":
            return self._gate_r0(action, context)
        elif gate == "R1":
            return self._gate_r1(action, context)
        elif gate == "R2":
            return self._gate_r2(action, context)
        elif gate == "R3":
            return self._gate_r3(action, context)
        elif gate == "R4":
            return self._gate_r4(action, context)
        elif gate == "R5":
            return self._gate_r5(action, context)
        elif gate == "R6":
            return self._gate_r6(action, context)
        else:
            return GateResult(False, gate, f"Unknown gate: {gate}")

    def _gate_r0(self, action: str, ctx: dict[str, Any]) -> GateResult:
        """R0: Parse — Input is syntactically valid."""
        if not action or not isinstance(action, str):
            return GateResult(False, "R0", "Empty or invalid input")
        return GateResult(True, "R0", "Input parsed successfully")

    def _gate_r1(self, action: str, ctx: dict[str, Any]) -> GateResult:
        """R1: Understand — Intent is clear."""
        if len(action.strip()) < 3:
            return GateResult(False, "R1", "Intent too vague or too short")
        return GateResult(True, "R1", "Intent understood")

    def _gate_r2(self, action: str, ctx: dict[str, Any]) -> GateResult:
        """R2: Validate — Inputs meet requirements."""
        if ctx.get("required_input") and not ctx.get("provided_input"):
            return GateResult(False, "R2", f"Missing required input: {ctx['required_input']}")
        return GateResult(True, "R2", "All inputs validated")

    def _gate_r3(self, action: str, ctx: dict[str, Any]) -> GateResult:
        """R3: Safety — No unsafe actions detected."""
        action_lower = action.lower()
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, action_lower):
                return GateResult(False, "R3", f"Unsafe action detected: {pattern}")
        if "secret" in action_lower or "password" in action_lower or "token" in action_lower:
            return GateResult(False, "R3", "Potential secret exposure detected")
        return GateResult(True, "R3", "No unsafe actions detected")

    def _gate_r4(self, action: str, ctx: dict[str, Any]) -> GateResult:
        """R4: Execute — Action is authorized."""
        permissions = ctx.get("permissions", [])
        required = ctx.get("required_permission")
        if required and required not in permissions:
            return GateResult(False, "R4", f"Missing permission: {required}")
        return GateResult(True, "R4", "Action authorized")

    def _gate_r5(self, action: str, ctx: dict[str, Any]) -> GateResult:
        """R5: Verify — Result meets acceptance criteria."""
        criteria = ctx.get("success_criteria", [])
        results = ctx.get("verification_results", {})
        if criteria and not results:
            return GateResult(False, "R5", "No verification results provided")
        if results and not results.get("passed", False):
            return GateResult(False, "R5", "Verification failed")
        return GateResult(True, "R5", "Result verified")

    def _gate_r6(self, action: str, ctx: dict[str, Any]) -> GateResult:
        """R6: Commit/Publish — Final human approval for high-risk."""
        if not ctx.get("human_approved", False):
            return GateResult(False, "R6", "Human approval required for this action")
        return GateResult(True, "R6", "Human approved")

    def get_minimum_gate(self, action_type: str) -> str:
        """Get the minimum gate required for an action type."""
        return self.ACTION_GATES.get(action_type, "R3")

    def requires_human(self, action_type: str) -> bool:
        """Check if an action type requires human approval."""
        return self.ACTION_GATES.get(action_type, "R3") == "R6"

    def classify_risk(self, action: str, action_type: str = "unknown") -> RiskLevel:
        """Classify the risk level of an action."""
        if self.requires_human(action_type):
            return RiskLevel.CRITICAL
        if action_type in ["write_file", "modify_code", "execute_shell", "database_write"]:
            return RiskLevel.MEDIUM
        if action_type in ["read_file", "search", "list"]:
            return RiskLevel.LOW
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, action.lower()):
                return RiskLevel.CRITICAL
        return RiskLevel.LOW

    def run_all_gates(self, action: str, action_type: str, context: dict[str, Any] | None = None) -> list[GateResult]:
        """Run all gates up to the minimum required for an action type."""
        context = context or {}
        min_gate = self.get_minimum_gate(action_type)
        gate_order = ["R0", "R1", "R2", "R3", "R4", "R5", "R6"]
        target_idx = gate_order.index(min_gate) if min_gate in gate_order else 6

        results = []
        for gate in gate_order[:target_idx + 1]:
            result = self.check_gate(gate, action, context)
            results.append(result)
            self._gate_log.append(result)
            if not result.passed:
                break

        return results

    def get_gate_log(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._gate_log]


async def create(kernel=None):
    return SafetyGatesPlugin()
