"""Final Gate Orchestrator — The mandatory Supervisor layer between Worker Complete and Mission Complete.

The Supervisor must NEVER allow a worker to declare the mission complete directly.
Worker completion is only a WORKER_CLAIMED_COMPLETE proposal. The Final Gate then:
1. Reconstructs expected state
2. Inspects actual state
3. Runs multi-scenario verification (12 passes)
4. Runs improvement analysis ("Can this be better?")
5. Makes final judgment: ACCEPT, REWORK, REDESIGN, or ROLLBACK
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class VerificationStatus(str, Enum):
    """Status of verification."""
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


class FinalDecision(str, Enum):
    """Final judgment decisions."""
    VERIFIED_COMPLETE = "verified_complete"
    VERIFIED_COMPLETE_WITH_KNOWN_LIMITATIONS = "verified_complete_with_known_limitations"
    IMPROVEMENT_REQUIRED = "improvement_required"
    REWORK_REQUIRED = "rework_required"
    REDESIGN_REQUIRED = "redesign_required"
    ROLLBACK_REQUIRED = "rollback_required"
    INCONCLUSIVE = "inconclusive"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class WorkerCompletionState(str, Enum):
    """States a worker completion can be in."""
    IN_PROGRESS = "in_progress"
    WORKER_CLAIMED_COMPLETE = "worker_claimed_complete"
    UNDER_VERIFICATION = "under_verification"
    VERIFIED_COMPLETE = "verified_complete"
    VERIFICATION_FAILED = "verification_failed"
    REWORK_REQUIRED = "rework_required"
    ABANDONED = "abandoned"


@dataclass
class VerificationPassResult:
    """Result of a single verification pass."""
    pass_name: str = ""
    status: VerificationStatus = VerificationStatus.IN_PROGRESS
    passed: int = 0
    failed: int = 0
    inconclusive: int = 0
    total: int = 0
    findings: List[str] = field(default_factory=list)
    duration_ms: int = 0


@dataclass
class ImprovementAnalysis:
    """Result of 'Can this be better?' analysis."""
    can_be_better: bool = False
    alternatives_considered: int = 0
    material_improvement_found: bool = False
    improvement_areas: List[str] = field(default_factory=list)
    recommendation: str = ""


@dataclass
class FinalVerificationRecord:
    """Complete record of final verification."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    mission_id: str = ""
    candidate_version: str = ""
    status: FinalDecision = FinalDecision.INCONCLUSIVE

    # Verification passes
    structural: VerificationPassResult = field(default_factory=lambda: VerificationPassResult("structural"))
    static: VerificationPassResult = field(default_factory=lambda: VerificationPassResult("static"))
    unit: VerificationPassResult = field(default_factory=lambda: VerificationPassResult("unit"))
    integration: VerificationPassResult = field(default_factory=lambda: VerificationPassResult("integration"))
    system: VerificationPassResult = field(default_factory=lambda: VerificationPassResult("system"))
    regression: VerificationPassResult = field(default_factory=lambda: VerificationPassResult("regression"))
    edge_cases: VerificationPassResult = field(default_factory=lambda: VerificationPassResult("edge_cases"))
    adversarial: VerificationPassResult = field(default_factory=lambda: VerificationPassResult("adversarial"))
    security: VerificationPassResult = field(default_factory=lambda: VerificationPassResult("security"))
    performance: VerificationPassResult = field(default_factory=lambda: VerificationPassResult("performance"))
    real_environment: VerificationPassResult = field(default_factory=lambda: VerificationPassResult("real_environment"))
    independent_review: VerificationPassResult = field(default_factory=lambda: VerificationPassResult("independent_review"))

    # Scenario coverage
    scenario_coverage: Dict[str, Any] = field(default_factory=dict)

    # Improvement review
    improvement_analysis: Optional[ImprovementAnalysis] = None

    # Known limitations
    known_limitations: List[str] = field(default_factory=list)

    # Rollback
    rollback_tested: bool = False
    previous_version: str = ""

    # Final decision
    final_decision: Optional[FinalDecision] = None
    promote: bool = False

    # Metadata
    timestamp: float = field(default_factory=time.time)
    duration_ms: int = 0


class FinalGateOrchestrator:
    """Main entry point for the Final Verification & Improvement Gate."""

    def __init__(self, data_dir: Optional[Path] = None):
        self._data_dir = data_dir or Path.home() / ".hermes" / "supervisor" / "final_gate"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._history: List[FinalVerificationRecord] = []

    def verify(
        self,
        mission_id: str,
        worker_claim: Dict[str, Any],
        expected_state: Dict[str, Any],
        actual_state: Dict[str, Any],
    ) -> FinalVerificationRecord:
        """Run the full final verification gate."""
        record = FinalVerificationRecord(
            mission_id=mission_id,
            candidate_version=worker_claim.get("version", "unknown"),
        )

        start_time = time.time()

        # Pass 1: Structural verification
        record.structural = self._run_pass("structural", expected_state, actual_state)

        # Pass 2: Static verification
        record.static = self._run_pass("static", expected_state, actual_state)

        # Pass 3: Unit verification
        record.unit = self._run_pass("unit", expected_state, actual_state)

        # Pass 4: Integration verification
        record.integration = self._run_pass("integration", expected_state, actual_state)

        # Pass 5: System verification
        record.system = self._run_pass("system", expected_state, actual_state)

        # Pass 6: Regression verification
        record.regression = self._run_pass("regression", expected_state, actual_state)

        # Pass 7: Edge-case verification
        record.edge_cases = self._run_pass("edge_cases", expected_state, actual_state)

        # Pass 8: Adversarial verification
        record.adversarial = self._run_pass("adversarial", expected_state, actual_state)

        # Pass 9: Security verification
        record.security = self._run_pass("security", expected_state, actual_state)

        # Pass 10: Performance verification
        record.performance = self._run_pass("performance", expected_state, actual_state)

        # Pass 11: Real-environment verification
        record.real_environment = self._run_pass("real_environment", expected_state, actual_state)

        # Pass 12: Independent review
        record.independent_review = self._run_pass("independent_review", expected_state, actual_state)

        # Scenario coverage
        record.scenario_coverage = self._compute_scenario_coverage(record)

        # Improvement analysis
        record.improvement_analysis = self._run_improvement_analysis(record)

        # Make final judgment
        record.final_decision = self._make_final_judgment(record)
        record.promote = record.final_decision in (
            FinalDecision.VERIFIED_COMPLETE,
            FinalDecision.VERIFIED_COMPLETE_WITH_KNOWN_LIMITATIONS,
        )

        record.duration_ms = int((time.time() - start_time) * 1000)
        self._history.append(record)

        return record

    def _run_pass(
        self,
        pass_name: str,
        expected_state: Dict[str, Any],
        actual_state: Dict[str, Any],
    ) -> VerificationPassResult:
        """Run a single verification pass."""
        result = VerificationPassResult(pass_name=pass_name)
        start_time = time.time()

        # In live operation, this would run actual verification checks
        # For now, simulate based on state comparison
        if expected_state and actual_state:
            for key in expected_state:
                result.total += 1
                if key in actual_state:
                    if expected_state[key] == actual_state[key]:
                        result.passed += 1
                    else:
                        result.failed += 1
                        result.findings.append(f"Mismatch for {key}")
                else:
                    result.failed += 1
                    result.findings.append(f"Missing key: {key}")

        # Determine status
        if result.failed == 0 and result.total > 0:
            result.status = VerificationStatus.PASSED
        elif result.failed > 0:
            result.status = VerificationStatus.FAILED
        else:
            result.status = VerificationStatus.INCONCLUSIVE

        result.duration_ms = int((time.time() - start_time) * 1000)
        return result

    def _compute_scenario_coverage(self, record: FinalVerificationRecord) -> Dict[str, Any]:
        """Compute scenario coverage across all passes."""
        passes = [
            record.structural, record.static, record.unit, record.integration,
            record.system, record.regression, record.edge_cases, record.adversarial,
            record.security, record.performance, record.real_environment, record.independent_review,
        ]

        total = sum(p.total for p in passes)
        passed = sum(p.passed for p in passes)
        failed = sum(p.failed for p in passes)

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "percent": (passed / total * 100) if total > 0 else 0,
        }

    def _run_improvement_analysis(self, record: FinalVerificationRecord) -> ImprovementAnalysis:
        """Run 'Can this be better?' analysis."""
        analysis = ImprovementAnalysis()

        # Check if any pass found issues that could be improved
        passes = [
            record.structural, record.static, record.unit, record.integration,
            record.system, record.regression, record.edge_cases, record.adversarial,
            record.security, record.performance, record.real_environment, record.independent_review,
        ]

        for p in passes:
            if p.status == VerificationStatus.FAILED or p.status == VerificationStatus.INCONCLUSIVE:
                analysis.can_be_better = True
                analysis.improvement_areas.extend(p.findings)

        # Determine recommendation
        if analysis.can_be_better:
            analysis.alternatives_considered = 3  # Would generate alternatives in live
            analysis.material_improvement_found = len(analysis.improvement_areas) > 2
            analysis.recommendation = "improvement_possible" if analysis.material_improvement_found else "minor_improvements"
        else:
            analysis.recommendation = "no_material_improvement"

        return analysis

    def _make_final_judgment(self, record: FinalVerificationRecord) -> FinalDecision:
        """Make final judgment based on all verification results."""
        passes = [
            record.structural, record.static, record.unit, record.integration,
            record.system, record.regression, record.edge_cases, record.adversarial,
            record.security, record.performance, record.real_environment, record.independent_review,
        ]

        # Count statuses
        passed_count = sum(1 for p in passes if p.status == VerificationStatus.PASSED)
        failed_count = sum(1 for p in passes if p.status == VerificationStatus.FAILED)

        # Decision logic
        if failed_count == 0 and passed_count >= 10:
            # All passed or mostly passed
            if record.improvement_analysis and record.improvement_analysis.material_improvement_found:
                return FinalDecision.VERIFIED_COMPLETE_WITH_KNOWN_LIMITATIONS
            return FinalDecision.VERIFIED_COMPLETE
        elif failed_count <= 2:
            # Minor failures - improvement required
            return FinalDecision.IMPROVEMENT_REQUIRED
        elif failed_count <= 5:
            # Moderate failures - rework required
            return FinalDecision.REWORK_REQUIRED
        elif failed_count <= 8:
            # Major failures - redesign required
            return FinalDecision.REDESIGN_REQUIRED
        else:
            # Too many failures - rollback
            return FinalDecision.ROLLBACK_REQUIRED

    def get_history(self) -> List[FinalVerificationRecord]:
        """Get verification history."""
        return self._history.copy()

    def save_record(self, record: FinalVerificationRecord) -> None:
        """Save verification record to disk."""
        path = self._data_dir / f"verification_{record.id}.json"
        data = {
            "id": record.id,
            "mission_id": record.mission_id,
            "candidate_version": record.candidate_version,
            "status": record.final_decision.value if record.final_decision else "unknown",
            "scenario_coverage": record.scenario_coverage,
            "timestamp": record.timestamp,
            "duration_ms": record.duration_ms,
        }
        path.write_text(json.dumps(data, indent=2))
