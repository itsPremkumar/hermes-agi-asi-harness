"""
Safety Envelope — Define safe operating boundaries for all actions.

For physical/IoT systems and computer systems alike:
  SAFE OPERATING ENVELOPE

Any action outside the envelope automatically escalates.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EnvelopeViolation(str, Enum):
    TARGET_NOT_ALLOWED = "target_not_allowed"
    OPERATION_NOT_ALLOWED = "operation_not_allowed"
    FREQUENCY_EXCEEDED = "frequency_exceeded"
    COST_EXCEEDED = "cost_exceeded"
    DATA_VOLUME_EXCEEDED = "data_volume_exceeded"
    TIME_WINDOW_VIOLATED = "time_window_violated"
    PERMISSION_DENIED = "permission_denied"
    RISK_TOO_HIGH = "risk_too_high"


@dataclass
class SafetyEnvelope:
    id: str
    name: str
    allowed_targets: List[str] = field(default_factory=list)
    allowed_operations: List[str] = field(default_factory=list)
    max_frequency_per_minute: int = 60
    max_cost_per_action: float = 0.0
    max_data_volume_mb: float = 100.0
    allowed_time_window: Optional[tuple] = None  # (start_hour, end_hour) UTC
    max_risk_score: float = 0.7
    emergency_stop: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EnvelopeCheck:
    action_id: str
    envelope_id: str
    passed: bool
    violations: List[EnvelopeViolation]
    timestamp: float
    escalated: bool = False


class SafetyEnvelopeManager:
    """
    Manage safety envelopes for different operational contexts.
    
    Any action outside the envelope automatically escalates to human approval.
    """

    def __init__(self):
        self.envelopes: Dict[str, SafetyEnvelope] = {}
        self.checks: List[EnvelopeCheck] = []
        self._action_counts: Dict[str, List[float]] = {}  # target → timestamps

    def create_envelope(
        self,
        name: str,
        allowed_targets: List[str] = None,
        allowed_operations: List[str] = None,
        max_frequency_per_minute: int = 60,
        max_cost_per_action: float = 0.0,
        max_data_volume_mb: float = 100.0,
        allowed_time_window: tuple = None,
        max_risk_score: float = 0.7,
    ) -> SafetyEnvelope:
        env = SafetyEnvelope(
            id=str(uuid.uuid4()),
            name=name,
            allowed_targets=allowed_targets or [],
            allowed_operations=allowed_operations or [],
            max_frequency_per_minute=max_frequency_per_minute,
            max_cost_per_action=max_cost_per_action,
            max_data_volume_mb=max_data_volume_mb,
            allowed_time_window=allowed_time_window,
            max_risk_score=max_risk_score,
        )
        self.envelopes[env.id] = env
        return env

    def check_action(
        self,
        action_id: str,
        envelope_id: str,
        target: str,
        operation: str,
        cost: float = 0.0,
        data_volume_mb: float = 0.0,
        risk_score: float = 0.0,
    ) -> EnvelopeCheck:
        """Check if an action is within the safety envelope."""
        env = self.envelopes.get(envelope_id)
        if not env:
            return EnvelopeCheck(
                action_id=action_id,
                envelope_id=envelope_id,
                passed=False,
                violations=[],
                timestamp=time.time(),
                escalated=True,
            )

        violations: List[EnvelopeViolation] = []

        # Check emergency stop
        if env.emergency_stop:
            violations.append(EnvelopeViolation.OPERATION_NOT_ALLOWED)

        # Check target
        if env.allowed_targets and target not in env.allowed_targets:
            violations.append(EnvelopeViolation.TARGET_NOT_ALLOWED)

        # Check operation
        if env.allowed_operations and operation not in env.allowed_operations:
            violations.append(EnvelopeViolation.OPERATION_NOT_ALLOWED)

        # Check frequency
        if not self._check_frequency(target, env.max_frequency_per_minute):
            violations.append(EnvelopeViolation.FREQUENCY_EXCEEDED)

        # Check cost
        if env.max_cost_per_action > 0 and cost > env.max_cost_per_action:
            violations.append(EnvelopeViolation.COST_EXCEEDED)

        # Check data volume
        if env.max_data_volume_mb > 0 and data_volume_mb > env.max_data_volume_mb:
            violations.append(EnvelopeViolation.DATA_VOLUME_EXCEEDED)

        # Check time window
        if env.allowed_time_window:
            current_hour = time.gmtime().tm_hour
            start, end = env.allowed_time_window
            if not (start <= current_hour < end):
                violations.append(EnvelopeViolation.TIME_WINDOW_VIOLATED)

        # Check risk
        if risk_score > env.max_risk_score:
            violations.append(EnvelopeViolation.RISK_TOO_HIGH)

        check = EnvelopeCheck(
            action_id=action_id,
            envelope_id=envelope_id,
            passed=len(violations) == 0,
            violations=violations,
            timestamp=time.time(),
            escalated=len(violations) > 0,
        )
        self.checks.append(check)
        return check

    def _check_frequency(self, target: str, max_per_minute: int) -> bool:
        now = time.time()
        if target not in self._action_counts:
            self._action_counts[target] = []
        # Remove old entries
        self._action_counts[target] = [
            t for t in self._action_counts[target] if now - t < 60
        ]
        if len(self._action_counts[target]) >= max_per_minute:
            return False
        self._action_counts[target].append(now)
        return True

    def trigger_emergency_stop(self, envelope_id: str):
        env = self.envelopes.get(envelope_id)
        if env:
            env.emergency_stop = True

    def reset_emergency_stop(self, envelope_id: str):
        env = self.envelopes.get(envelope_id)
        if env:
            env.emergency_stop = False

    def get_state(self) -> Dict[str, Any]:
        return {
            "envelopes": len(self.envelopes),
            "total_checks": len(self.checks),
            "passed": sum(1 for c in self.checks if c.passed),
            "violations": sum(1 for c in self.checks if not c.passed),
            "escalated": sum(1 for c in self.checks if c.escalated),
        }
