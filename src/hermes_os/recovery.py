"""
HERMES INTELLIGENCE OS — PLANE 15: RECOVERY OS & STAGNATION DETECTION
======================================================================
AVO-inspired failure recovery and continuous stagnation monitoring:
- Complete failure taxonomy classification
- Counterfactual repair & alternative selection
- Real-time stagnation telemetry (progress/time, repeated tool calls, loop traps)
- External supervisory intervention triggers
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes.os.recovery")


class FailureCategory(str, Enum):
    KNOWLEDGE = "knowledge"
    REASONING = "reasoning"
    PLANNING = "planning"
    TOOL_SELECTION = "tool_selection"
    TOOL_EXECUTION = "tool_execution"
    MEMORY = "memory"
    COORDINATION = "coordination"
    VERIFICATION = "verification"
    ENVIRONMENT = "environment"
    RESOURCE = "resource"
    SECURITY = "security"
    UNKNOWN = "unknown"


class StagnationLevel(str, Enum):
    NOMINAL = "nominal"                    # Steady progress
    SLOW_PROGRESS = "slow_progress"        # Minor latency, but new observations arrive
    PLATEAU = "plateau"                    # Repeated actions without new evidence (needs strategy change)
    CRITICAL_LOOP = "critical_loop"        # Exact duplicate failure loop (requires supervisor intervention)


@dataclass
class FailureDiagnosis:
    failure_id: str
    category: FailureCategory
    root_cause: str
    is_transient: bool
    counterfactual_alternative: str
    recommended_action: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class StagnationTelemetry:
    level: StagnationLevel
    consecutive_duplicate_actions: int
    identical_error_count: int
    elapsed_without_progress_seconds: float
    recommended_intervention: str


class AVOStagnationDetector:
    """
    Monitors long-horizon mission execution trajectories to detect plateaus,
    repetitive loops, and unproductive wandering.
    """

    def __init__(self, loop_threshold: int = 3, plateau_seconds: float = 60.0):
        self.loop_threshold = loop_threshold
        self.plateau_seconds = plateau_seconds
        self._action_history: list[str] = []
        self._error_history: list[str] = []
        self._last_progress_time: float = time.time()

    def record_step(self, action_name: str, success: bool, error: Optional[str] = None) -> None:
        self._action_history.append(action_name)
        if success:
            self._last_progress_time = time.time()
        elif error:
            self._error_history.append(error)

    def evaluate_stagnation(self) -> StagnationTelemetry:
        """Analyze action history and error repetition to detect traps."""
        now = time.time()
        elapsed_stale = now - self._last_progress_time

        # 1. Check duplicate recent actions
        recent_actions = self._action_history[-self.loop_threshold:] if len(self._action_history) >= self.loop_threshold else []
        is_action_loop = len(recent_actions) == self.loop_threshold and len(set(recent_actions)) == 1

        # 2. Check duplicate recent errors
        recent_errors = self._error_history[-self.loop_threshold:] if len(self._error_history) >= self.loop_threshold else []
        is_error_loop = len(recent_errors) == self.loop_threshold and len(set(recent_errors)) == 1

        if is_error_loop or (is_action_loop and elapsed_stale > self.plateau_seconds):
            return StagnationTelemetry(
                level=StagnationLevel.CRITICAL_LOOP,
                consecutive_duplicate_actions=len(recent_actions),
                identical_error_count=len(recent_errors),
                elapsed_without_progress_seconds=elapsed_stale,
                recommended_intervention="supervisor_interrupt_and_reassign",
            )
        elif is_action_loop or elapsed_stale > (self.plateau_seconds / 2):
            return StagnationTelemetry(
                level=StagnationLevel.PLATEAU,
                consecutive_duplicate_actions=len(recent_actions),
                identical_error_count=len(recent_errors),
                elapsed_without_progress_seconds=elapsed_stale,
                recommended_intervention="change_reasoning_strategy_or_model",
            )
        elif elapsed_stale > 10.0:
            return StagnationTelemetry(
                level=StagnationLevel.SLOW_PROGRESS,
                consecutive_duplicate_actions=0,
                identical_error_count=0,
                elapsed_without_progress_seconds=elapsed_stale,
                recommended_intervention="continue_with_monitoring",
            )
        return StagnationTelemetry(
            level=StagnationLevel.NOMINAL,
            consecutive_duplicate_actions=0,
            identical_error_count=0,
            elapsed_without_progress_seconds=elapsed_stale,
            recommended_intervention="nominal_execution",
        )

    def reset(self) -> None:
        self._action_history.clear()
        self._error_history.clear()
        self._last_progress_time = time.time()


class RecoveryEngine:
    """Classifies failures, conducts counterfactual reasoning, and selects alternatives."""

    def __init__(self):
        self.stagnation_detector = AVOStagnationDetector()

    def diagnose(self, error_message: str, component: str) -> FailureDiagnosis:
        err_lower = error_message.lower()
        if "syntax" in err_lower or "ast" in err_lower or "indent" in err_lower:
            cat = FailureCategory.TOOL_EXECUTION
            alt = "Repair code syntax with automated formatter before execution"
            action = "reformat_and_recompile"
            transient = False
        elif "timeout" in err_lower or "deadline" in err_lower:
            cat = FailureCategory.RESOURCE
            alt = "Allocate additional time budget or decompose into smaller subtasks"
            action = "split_subtask"
            transient = True
        elif "permission" in err_lower or "unauthorized" in err_lower:
            cat = FailureCategory.SECURITY
            alt = "Request elevated authority grant or switch to read-only tool"
            action = "escalate_authority"
            transient = False
        elif "not found" in err_lower or "missing" in err_lower:
            cat = FailureCategory.KNOWLEDGE
            alt = "Trigger research engine to locate missing reference"
            action = "conduct_research"
            transient = False
        else:
            cat = FailureCategory.UNKNOWN
            alt = "Retry with fresh context and isolated environment"
            action = "retry_clean_context"
            transient = False

        return FailureDiagnosis(
            failure_id=f"fail-{uuid.uuid4().hex[:8]}",
            category=cat,
            root_cause=error_message,
            is_transient=transient,
            counterfactual_alternative=alt,
            recommended_action=action,
        )
