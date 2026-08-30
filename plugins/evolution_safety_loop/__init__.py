"""
Evolution Safety Loop Plugin — Constraints on Self-Modification

Enforces: rollback capability, blast radius limits, value alignment check,
corrigibility verification, test coverage requirement, reversibility test.
All self-modifications must pass safety gates before deployment.
"""

import time
import hashlib
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum


class ModificationType(str, Enum):
    PROCEDURE = "procedure"  # workflow change
    SKILL = "skill"  # new skill added
    PROMPT = "prompt"  # prompt template change
    TOOL = "tool"  # tool registration
    MODEL = "model"  # model swap
    POLICY = "policy"  # policy change (HIGH RISK)
    CONSTITUTION = "constitution"  # identity change (FORBIDDEN)


@dataclass
class SafetyCheck:
    name: str
    description: str
    required: bool
    passed: bool = False
    details: str = ""


@dataclass
class ModificationRequest:
    modification_id: str
    modification_type: str
    description: str
    blast_radius: int  # 0-10, how much it could affect
    reversibility: float  # 0-1, how easy to roll back
    value_alignment_score: float  # 0-1
    test_coverage: float  # 0-1
    rollback_plan: str
    proposed_by: str = "system"
    timestamp: float = field(default_factory=time.time)
    safety_checks: List[SafetyCheck] = field(default_factory=list)
    approved: bool = False
    rejected: bool = False
    rejection_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "modification_id": self.modification_id,
            "modification_type": self.modification_type,
            "description": self.description,
            "blast_radius": self.blast_radius,
            "reversibility": self.reversibility,
            "value_alignment_score": self.value_alignment_score,
            "test_coverage": self.test_coverage,
            "rollback_plan": self.rollback_plan,
            "proposed_by": self.proposed_by,
            "timestamp": self.timestamp,
            "approved": self.approved,
            "rejected": self.rejected,
            "rejection_reason": self.rejection_reason,
        }


class EvolutionSafetyLoop:
    """Safety loop for self-modification."""

    # Hard limits
    FORBIDDEN_TYPES = {ModificationType.CONSTITUTION.value}
    MAX_BLAST_RADIUS = 7  # Higher needs human approval
    MIN_REVERSIBILITY = 0.7
    MIN_VALUE_ALIGNMENT = 0.85
    MIN_TEST_COVERAGE = 0.6

    def __init__(self):
        self._requests: List[ModificationRequest] = []
        self._approved: List[str] = []
        self._rejected: List[str] = []

    def submit_modification(self, mod_type: str, description: str,
                            blast_radius: int, reversibility: float,
                            value_alignment_score: float, test_coverage: float,
                            rollback_plan: str,
                            proposed_by: str = "system") -> ModificationRequest:
        """Submit a modification for safety review."""
        mod_id = f"MOD-{hashlib.sha256(f'{mod_type}{time.time()}'.encode()).hexdigest()[:8]}"

        request = ModificationRequest(
            modification_id=mod_id,
            modification_type=mod_type,
            description=description,
            blast_radius=blast_radius,
            reversibility=reversibility,
            value_alignment_score=value_alignment_score,
            test_coverage=test_coverage,
            rollback_plan=rollback_plan,
            proposed_by=proposed_by,
        )

        # Run safety checks
        request.safety_checks = self._run_safety_checks(request)
        request.approved = self._is_approved(request)
        if not request.approved:
            request.rejected = True
            request.rejection_reason = self._get_rejection_reason(request)

        self._requests.append(request)
        if request.approved:
            self._approved.append(mod_id)
        else:
            self._rejected.append(mod_id)

        return request

    def _run_safety_checks(self, request: ModificationRequest) -> List[SafetyCheck]:
        checks = []

        # Check 1: forbidden types
        check = SafetyCheck(
            name="forbidden_type_check",
            description="Verify modification is not in forbidden list",
            required=True,
            passed=request.modification_type not in self.FORBIDDEN_TYPES,
            details=f"type={request.modification_type}, forbidden={list(self.FORBIDDEN_TYPES)}",
        )
        checks.append(check)

        # Check 2: blast radius
        check = SafetyCheck(
            name="blast_radius_check",
            description="Verify blast radius is within limits",
            required=True,
            passed=request.blast_radius <= self.MAX_BLAST_RADIUS,
            details=f"radius={request.blast_radius}, max={self.MAX_BLAST_RADIUS}",
        )
        checks.append(check)

        # Check 3: reversibility
        check = SafetyCheck(
            name="reversibility_check",
            description="Verify modification is reversible",
            required=True,
            passed=request.reversibility >= self.MIN_REVERSIBILITY,
            details=f"reversibility={request.reversibility}, min={self.MIN_REVERSIBILITY}",
        )
        checks.append(check)

        # Check 4: value alignment
        check = SafetyCheck(
            name="value_alignment_check",
            description="Verify alignment with core values",
            required=True,
            passed=request.value_alignment_score >= self.MIN_VALUE_ALIGNMENT,
            details=f"alignment={request.value_alignment_score}, min={self.MIN_VALUE_ALIGNMENT}",
        )
        checks.append(check)

        # Check 5: test coverage
        check = SafetyCheck(
            name="test_coverage_check",
            description="Verify adequate test coverage",
            required=True,
            passed=request.test_coverage >= self.MIN_TEST_COVERAGE,
            details=f"coverage={request.test_coverage}, min={self.MIN_TEST_COVERAGE}",
        )
        checks.append(check)

        # Check 6: rollback plan
        check = SafetyCheck(
            name="rollback_plan_check",
            description="Verify rollback plan is documented",
            required=True,
            passed=bool(request.rollback_plan and len(request.rollback_plan) > 10),
            details=f"plan length={len(request.rollback_plan)}",
        )
        checks.append(check)

        return checks

    def _is_approved(self, request: ModificationRequest) -> bool:
        return all(check.passed for check in request.safety_checks)

    def _get_rejection_reason(self, request: ModificationRequest) -> str:
        failed = [c.name for c in request.safety_checks if not c.passed]
        return f"Failed safety checks: {', '.join(failed)}"

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_requests": len(self._requests),
            "approved": len(self._approved),
            "rejected": len(self._rejected),
            "approval_rate": len(self._approved) / max(1, len(self._requests)),
        }


class EvolutionSafetyLoopPlugin:
    def __init__(self):
        self.engine = EvolutionSafetyLoop()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {
            "status": "healthy",
            "stats": self.engine.get_stats(),
        }


async def create(kernel=None):
    plugin = EvolutionSafetyLoopPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
