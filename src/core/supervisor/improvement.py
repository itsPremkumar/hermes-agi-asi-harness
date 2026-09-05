"""Improvement Analysis + Version Management + Rework Decision Engine + Final Judgment.

Implements the "Can this be better?" gate and version/rework management.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ImprovementArea(str, Enum):
    """Areas where improvement is possible."""
    PERFORMANCE = "performance"
    SIMPLICITY = "simplicity"
    SAFETY = "safety"
    MAINTAINABILITY = "maintainability"
    RESOURCE_USAGE = "resource_usage"
    OBSERVABILITY = "observability"
    TESTABILITY = "testability"
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    EXTENSIBILITY = "extensibility"


class ReworkType(str, Enum):
    """Types of rework."""
    PATCH = "patch"
    TARGETED_REWORK = "targeted_rework"
    REDESIGN = "redesign"
    ROLLBACK = "rollback"


class FailureClassification(str, Enum):
    """Classification of failures."""
    MINOR_DEFECT = "minor_defect"
    LOCALIZED_DEFECT = "localized_defect"
    ARCHITECTURAL_DEFECT = "architectural_defect"
    REQUIREMENT_MISUNDERSTANDING = "requirement_misunderstanding"
    MISSING_CAPABILITY = "missing_capability"
    WRONG_DEPENDENCY = "wrong_dependency"
    FUNDAMENTALLY_BAD = "fundamentally_bad"


@dataclass
class VersionInfo:
    """Information about a version."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    version: str = ""
    status: str = "candidate"  # stable, candidate, best_verified, experiment
    score: float = 0.0
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReworkDecision:
    """A rework decision."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    failure_classification: FailureClassification = FailureClassification.MINOR_DEFECT
    rework_type: ReworkType = ReworkType.PATCH
    reason: str = ""
    target_version: str = ""
    timestamp: float = field(default_factory=time.time)


class ImprovementAnalyzer:
    """Analyzes whether a solution can be better."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {
            "max_alternatives": 3,
            "max_iterations": 2,
            "time_budget_seconds": 1800,
            "minimum_expected_gain": 0.03,
        }

    def analyze(self, verification_record: Any) -> Dict[str, Any]:
        """Run improvement analysis."""
        improvement_areas = self._identify_improvement_areas(verification_record)
        alternatives = self._generate_alternatives(improvement_areas)
        recommendation = self._make_recommendation(improvement_areas, alternatives)

        return {
            "can_be_better": len(improvement_areas) > 0,
            "improvement_areas": [a.value for a in improvement_areas],
            "alternatives_considered": len(alternatives),
            "material_improvement_found": recommendation == "material_improvement",
            "recommendation": recommendation,
        }

    def _identify_improvement_areas(self, record: Any) -> List[ImprovementArea]:
        """Identify areas for improvement."""
        areas = []

        # Check verification passes for improvement opportunities
        if hasattr(record, 'performance'):
            if record.performance.status.value == "failed":
                areas.append(ImprovementArea.PERFORMANCE)

        if hasattr(record, 'security'):
            if record.security.status.value == "failed":
                areas.append(ImprovementArea.SECURITY)

        if hasattr(record, 'edge_cases'):
            if record.edge_cases.status.value == "failed":
                areas.append(ImprovementArea.MAINTAINABILITY)

        return areas

    def _generate_alternatives(self, areas: List[ImprovementArea]) -> List[Dict[str, Any]]:
        """Generate alternative approaches."""
        alternatives = []
        for i, area in enumerate(areas[:self._config["max_alternatives"]]):
            alternatives.append({
                "id": f"alt_{i}",
                "target_area": area.value,
                "description": f"Alternative approach for {area.value}",
            })
        return alternatives

    def _make_recommendation(
        self, areas: List[ImprovementArea], alternatives: List[Dict[str, Any]]
    ) -> str:
        """Make improvement recommendation."""
        if not areas:
            return "no_improvement_needed"
        elif len(areas) <= 2:
            return "minor_improvements"
        else:
            return "material_improvement"


class VersionManager:
    """Manages versions and version selection."""

    def __init__(self):
        self._versions: Dict[str, VersionInfo] = {}
        self._stable_version: str = ""
        self._best_verified_version: str = ""
        self._current_candidate: str = ""

    def register_version(self, version: VersionInfo) -> None:
        """Register a version."""
        self._versions[version.id] = version

    def set_stable(self, version_id: str) -> None:
        """Set the stable version."""
        self._stable_version = version_id

    def set_best_verified(self, version_id: str) -> None:
        """Set the best verified version."""
        self._best_verified_version = version_id

    def set_candidate(self, version_id: str) -> None:
        """Set the current candidate."""
        self._current_candidate = version_id

    def get_stable(self) -> Optional[VersionInfo]:
        """Get the stable version."""
        return self._versions.get(self._stable_version)

    def get_best_verified(self) -> Optional[VersionInfo]:
        """Get the best verified version."""
        return self._versions.get(self._best_verified_version)

    def get_candidate(self) -> Optional[VersionInfo]:
        """Get the current candidate."""
        return self._versions.get(self._current_candidate)

    def rollback(self) -> Optional[VersionInfo]:
        """Rollback to the last known good version."""
        if self._best_verified_version:
            self._current_candidate = self._best_verified_version
            return self.get_best_verified()
        elif self._stable_version:
            self._current_candidate = self._stable_version
            return self.get_stable()
        return None

    def promote_candidate(self) -> None:
        """Promote current candidate to stable."""
        if self._current_candidate:
            self._best_verified_version = self._current_candidate
            self._stable_version = self._current_candidate


class ReworkDecisionEngine:
    """Decides what type of rework is needed."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {
            "max_patch_attempts": 3,
            "architectural_failure_threshold": 2,
            "repeated_failure_threshold": 3,
        }
        self._patch_attempts: Dict[str, int] = {}
        self._failure_counts: Dict[str, int] = {}

    def classify_failure(self, verification_record: Any) -> FailureClassification:
        """Classify the type of failure."""
        failed_passes = 0
        if hasattr(verification_record, 'structural'):
            if verification_record.structural.status.value == "failed":
                failed_passes += 1
        if hasattr(verification_record, 'integration'):
            if verification_record.integration.status.value == "failed":
                failed_passes += 1
        if hasattr(verification_record, 'system'):
            if verification_record.system.status.value == "failed":
                failed_passes += 1
        if hasattr(verification_record, 'regression'):
            if verification_record.regression.status.value == "failed":
                failed_passes += 1
        if hasattr(verification_record, 'security'):
            if verification_record.security.status.value == "failed":
                failed_passes += 1

        if failed_passes == 0:
            return FailureClassification.MINOR_DEFECT
        elif failed_passes == 1:
            return FailureClassification.LOCALIZED_DEFECT
        elif failed_passes <= 3:
            return FailureClassification.ARCHITECTURAL_DEFECT
        else:
            return FailureClassification.FUNDAMENTALLY_BAD

    def decide_rework(
        self, task_id: str, failure_classification: FailureClassification
    ) -> ReworkDecision:
        """Decide what rework is needed."""
        # Track attempts
        self._failure_counts[task_id] = self._failure_counts.get(task_id, 0) + 1

        # Determine rework type
        if failure_classification == FailureClassification.MINOR_DEFECT:
            rework_type = ReworkType.PATCH
        elif failure_classification == FailureClassification.LOCALIZED_DEFECT:
            rework_type = ReworkType.TARGETED_REWORK
        elif failure_classification == FailureClassification.ARCHITECTURAL_DEFECT:
            rework_type = ReworkType.REDESIGN
        else:
            rework_type = ReworkType.ROLLBACK

        # Check if we've exceeded patch attempts
        if rework_type == ReworkType.PATCH:
            self._patch_attempts[task_id] = self._patch_attempts.get(task_id, 0) + 1
            if self._patch_attempts[task_id] >= self._config["max_patch_attempts"]:
                rework_type = ReworkType.REDESIGN

        return ReworkDecision(
            failure_classification=failure_classification,
            rework_type=rework_type,
            reason=f"Failure classified as {failure_classification.value}",
        )

    def should_stop_patching(self, task_id: str) -> bool:
        """Check if patching should stop."""
        return self._patch_attempts.get(task_id, 0) >= self._config["max_patch_attempts"]


class FinalJudgmentSystem:
    """Makes the final judgment on mission completion."""

    def __init__(self):
        self._improvement_analyzer = ImprovementAnalyzer()
        self._version_manager = VersionManager()
        self._rework_engine = ReworkDecisionEngine()

    def judge(
        self,
        verification_record: Any,
        mission_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Make final judgment."""
        # 1. Check if verification passed
        verification_passed = self._check_verification_passed(verification_record)

        if not verification_passed:
            # 2. Classify failure
            failure_class = self._rework_engine.classify_failure(verification_record)

            # 3. Decide rework
            task_id = mission_context.get("task_id", "")
            rework_decision = self._rework_engine.decide_rework(task_id, failure_class)

            return {
                "decision": "rework",
                "failure_classification": failure_class.value,
                "rework_type": rework_decision.rework_type.value,
                "reason": rework_decision.reason,
            }

        # 4. Run improvement analysis
        improvement = self._improvement_analyzer.analyze(verification_record)

        # 5. Make final decision
        if improvement["material_improvement_found"]:
            return {
                "decision": "improve",
                "improvement_areas": improvement["improvement_areas"],
                "alternatives": improvement["alternatives_considered"],
            }
        elif improvement["can_be_better"]:
            return {
                "decision": "accept_with_improvements",
                "improvement_areas": improvement["improvement_areas"],
            }
        else:
            return {
                "decision": "accept",
                "reason": "No material improvement found",
            }

    def _check_verification_passed(self, record: Any) -> bool:
        """Check if verification passed."""
        passes = []
        for pass_name in ["structural", "static", "unit", "integration", "system", "regression"]:
            if hasattr(record, pass_name):
                pass_result = getattr(record, pass_name)
                if hasattr(pass_result, 'status'):
                    passes.append(pass_result.status.value == "passed")

        if not passes:
            return False
        return sum(passes) / len(passes) >= 0.8
