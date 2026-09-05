"""Stagnation Detection (AVO-inspired) + Verification System.

Detects when workers are stuck and need intervention.
Verifies results against acceptance criteria.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class StagnationType(str, Enum):
    """Types of stagnation."""
    NO_PROGRESS = "no_progress"
    REPEATED_ERROR = "repeated_error"
    REPEATED_FILE_EDIT = "repeated_file_edit"
    SAME_TEST_FAILURE = "same_test_failure"
    NO_NEW_EVIDENCE = "no_new_evidence"
    NO_SCORE_IMPROVEMENT = "no_score_improvement"
    IDENTICAL_STRATEGY = "identical_strategy"
    HEARTBEAT_STALE = "heartbeat_stale"
    LOW_CONFIDENCE = "low_confidence"


class InterventionType(str, Enum):
    """Types of supervisor interventions."""
    PROVIDE_CONTEXT = "provide_context"
    ASSIGN_NEW_WORKER = "assign_new_worker"
    CHANGE_MODEL = "change_model"
    CHANGE_TOOLS = "change_tools"
    CHANGE_STRATEGY = "change_strategy"
    REDUCE_SCOPE = "reduce_scope"
    SPLIT_TASK = "split_task"
    REQUEST_RESEARCH = "request_research"
    FORCE_REVIEW = "force_review"
    REPLAN = "replan"
    TERMINATE_RESTART = "terminate_restart"


@dataclass
class StagnationSignal:
    """A detected stagnation signal."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    worker_id: str = ""
    stagnation_type: StagnationType = StagnationType.NO_PROGRESS
    severity: float = 0.0  # 0.0 to 1.0
    evidence: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    intervention: Optional[InterventionType] = None


@dataclass
class VerificationResult:
    """Result of verification."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_id: str = ""
    passed: bool = False
    criteria: List[str] = field(default_factory=list)
    results: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class StagnationDetector:
    """Detects worker stagnation (AVO-inspired)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {
            "no_progress_threshold": 10,  # iterations without progress
            "repeated_error_threshold": 3,
            "heartbeat_stale_seconds": 300,
            "low_confidence_threshold": 0.3,
            "score_plateau_threshold": 5,
        }
        self._signals: List[StagnationSignal] = []

    def detect(
        self,
        worker_id: str,
        heartbeats: List[Any],
        history: List[Dict[str, Any]],
    ) -> List[StagnationSignal]:
        """Detect stagnation signals for a worker."""
        signals = []

        # 1. No progress
        no_progress = self._check_no_progress(worker_id, heartbeats)
        if no_progress:
            signals.append(no_progress)

        # 2. Repeated errors
        repeated_error = self._check_repeated_errors(worker_id, heartbeats)
        if repeated_error:
            signals.append(repeated_error)

        # 3. Stale heartbeat
        stale = self._check_stale_heartbeat(worker_id, heartbeats)
        if stale:
            signals.append(stale)

        # 4. No score improvement
        score_plateau = self._check_score_plateau(worker_id, heartbeats)
        if score_plateau:
            signals.append(score_plateau)

        # 5. Repeated same action
        repeated_action = self._check_repeated_actions(worker_id, heartbeats)
        if repeated_action:
            signals.append(repeated_action)

        # 6. Low confidence
        low_confidence = self._check_low_confidence(worker_id, heartbeats)
        if low_confidence:
            signals.append(low_confidence)

        self._signals.extend(signals)
        return signals

    def _check_no_progress(
        self, worker_id: str, heartbeats: List[Any]
    ) -> Optional[StagnationSignal]:
        """Check for no progress."""
        if len(heartbeats) < self._config["no_progress_threshold"]:
            return None

        recent = heartbeats[-self._config["no_progress_threshold"]:]
        progress_values = [h.progress for h in recent]

        # Check if progress is unchanged
        if len(set(progress_values)) <= 1 and progress_values[0] < 1.0:
            return StagnationSignal(
                worker_id=worker_id,
                stagnation_type=StagnationType.NO_PROGRESS,
                severity=0.8,
                evidence=[f"No progress in {len(recent)} heartbeats"],
            )
        return None

    def _check_repeated_errors(
        self, worker_id: str, heartbeats: List[Any]
    ) -> Optional[StagnationSignal]:
        """Check for repeated errors."""
        recent_errors = []
        for hb in reversed(heartbeats[-20:]):
            if hb.blockers:
                recent_errors.extend(hb.blockers)

        # Count occurrences
        error_counts: Dict[str, int] = {}
        for error in recent_errors:
            error_counts[error] = error_counts.get(error, 0) + 1

        for error, count in error_counts.items():
            if count >= self._config["repeated_error_threshold"]:
                return StagnationSignal(
                    worker_id=worker_id,
                    stagnation_type=StagnationType.REPEATED_ERROR,
                    severity=0.7,
                    evidence=[f"Error '{error}' occurred {count} times"],
                )
        return None

    def _check_stale_heartbeat(
        self, worker_id: str, heartbeats: List[Any]
    ) -> Optional[StagnationSignal]:
        """Check for stale heartbeat."""
        if not heartbeats:
            return None

        latest = heartbeats[-1]
        time_since = time.time() - latest.timestamp

        if time_since > self._config["heartbeat_stale_seconds"]:
            return StagnationSignal(
                worker_id=worker_id,
                stagnation_type=StagnationType.HEARTBEAT_STALE,
                severity=0.9,
                evidence=[f"Last heartbeat {time_since:.0f}s ago"],
            )
        return None

    def _check_score_plateau(
        self, worker_id: str, heartbeats: List[Any]
    ) -> Optional[StagnationSignal]:
        """Check for score plateau."""
        if len(heartbeats) < self._config["score_plateau_threshold"]:
            return None

        recent = heartbeats[-self._config["score_plateau_threshold"]:]
        progress_values = [h.progress for h in recent]

        if max(progress_values) - min(progress_values) < 0.05:
            return StagnationSignal(
                worker_id=worker_id,
                stagnation_type=StagnationType.NO_SCORE_IMPROVEMENT,
                severity=0.6,
                evidence=[f"Score plateau for {len(recent)} iterations"],
            )
        return None

    def _check_repeated_actions(
        self, worker_id: str, heartbeats: List[Any]
    ) -> Optional[StagnationSignal]:
        """Check for repeated actions."""
        if len(heartbeats) < 5:
            return None

        recent_actions = [hb.current_action for hb in heartbeats[-5:]]
        if len(set(recent_actions)) == 1 and recent_actions[0]:
            return StagnationSignal(
                worker_id=worker_id,
                stagnation_type=StagnationType.IDENTICAL_STRATEGY,
                severity=0.5,
                evidence=[f"Same action repeated: {recent_actions[0]}"],
            )
        return None

    def _check_low_confidence(
        self, worker_id: str, heartbeats: List[Any]
    ) -> Optional[StagnationSignal]:
        """Check for low confidence."""
        if not heartbeats:
            return None

        latest = heartbeats[-1]
        if latest.confidence < self._config["low_confidence_threshold"]:
            return StagnationSignal(
                worker_id=worker_id,
                stagnation_type=StagnationType.LOW_CONFIDENCE,
                severity=0.4,
                evidence=[f"Low confidence: {latest.confidence:.2f}"],
            )
        return None

    def get_recommended_intervention(
        self, signal: StagnationSignal
    ) -> InterventionType:
        """Get recommended intervention for a stagnation signal."""
        interventions = {
            StagnationType.NO_PROGRESS: InterventionType.PROVIDE_CONTEXT,
            StagnationType.REPEATED_ERROR: InterventionType.CHANGE_STRATEGY,
            StagnationType.REPEATED_FILE_EDIT: InterventionType.REDUCE_SCOPE,
            StagnationType.SAME_TEST_FAILURE: InterventionType.REQUEST_RESEARCH,
            StagnationType.NO_NEW_EVIDENCE: InterventionType.ASSIGN_NEW_WORKER,
            StagnationType.NO_SCORE_IMPROVEMENT: InterventionType.REPLAN,
            StagnationType.IDENTICAL_STRATEGY: InterventionType.FORCE_REVIEW,
            StagnationType.HEARTBEAT_STALE: InterventionType.TERMINATE_RESTART,
            StagnationType.LOW_CONFIDENCE: InterventionType.PROVIDE_CONTEXT,
        }
        return interventions.get(signal.stagnation_type, InterventionType.REPLAN)

    def get_all_signals(self) -> List[StagnationSignal]:
        """Get all detected signals."""
        return self._signals.copy()


class VerificationSystem:
    """Verifies results against acceptance criteria."""

    def __init__(self):
        self._results: List[VerificationResult] = []

    def verify_task(
        self,
        task_id: str,
        acceptance_criteria: List[str],
        evidence: List[Dict[str, Any]],
    ) -> VerificationResult:
        """Verify a task against its acceptance criteria."""
        result = VerificationResult(
            task_id=task_id,
            criteria=acceptance_criteria,
        )

        # Check each criterion
        all_passed = True
        for criterion in acceptance_criteria:
            passed = self._check_criterion(criterion, evidence)
            result.results.append({
                "criterion": criterion,
                "passed": passed,
            })
            if not passed:
                all_passed = False

        result.passed = all_passed
        self._results.append(result)
        return result

    def _check_criterion(
        self, criterion: str, evidence: List[Dict[str, Any]]
    ) -> bool:
        """Check a single criterion against evidence."""
        # In live operation, this would use LLM or deterministic checks
        # For now, simple keyword matching
        criterion_lower = criterion.lower()
        for item in evidence:
            item_str = str(item).lower()
            if criterion_lower in item_str:
                return True
        return False

    def verify_mission(
        self,
        mission_criteria: List[str],
        task_results: List[VerificationResult],
    ) -> VerificationResult:
        """Verify overall mission completion."""
        result = VerificationResult(
            task_id="mission",
            criteria=mission_criteria,
        )

        # All tasks must be verified
        all_tasks_passed = all(r.passed for r in task_results)

        # Check mission-level criteria
        all_criteria_met = True
        for criterion in mission_criteria:
            passed = self._check_criterion(criterion, [])
            result.results.append({
                "criterion": criterion,
                "passed": passed,
            })
            if not passed:
                all_criteria_met = False

        result.passed = all_tasks_passed and all_criteria_met
        self._results.append(result)
        return result

    def get_all_results(self) -> List[VerificationResult]:
        """Get all verification results."""
        return self._results.copy()

    def get_failed_results(self) -> List[VerificationResult]:
        """Get failed verification results."""
        return [r for r in self._results if not r.passed]
