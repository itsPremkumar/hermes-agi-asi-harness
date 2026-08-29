"""CI/CD integration with quality gates."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from testpilot.models import (
    ContractDefinition,
    FlakyTestReport,
    GateStatus,
    PerformanceResult,
    QualityGateResult,
    TestGap,
    VisualTestResult,
)
from testpilot.contract_testing import ContractResult, ContractVerifier
from testpilot.flaky_detect import FlakyDetector
from testpilot.perf_integration import PerfIntegration, PerfThreshold
from testpilot.visual_regression import VisualRegressionRunner


@dataclass
class CoverageResult:
    """Code coverage result."""
    total_lines: int = 0
    covered_lines: int = 0
    coverage_percent: float = 0.0
    missing_lines: dict[str, list[int]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.missing_lines is None:
            self.missing_lines = {}


class QualityGateRunner:
    """Runs a suite of quality gates and aggregates results."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.results: list[QualityGateResult] = []

    def run_coverage_gate(
        self,
        coverage_result: CoverageResult | None = None,
        min_percent: float = 80.0,
    ) -> QualityGateResult:
        """Gate: minimum code coverage percentage."""
        if coverage_result is None:
            coverage_result = self._run_coverage()

        passed = coverage_result.coverage_percent >= min_percent
        result = QualityGateResult(
            name="coverage",
            status=GateStatus.PASS if passed else GateStatus.FAIL,
            message=(
                f"Coverage: {coverage_result.coverage_percent:.1f}% "
                f"(minimum {min_percent}%)"
            ),
            details={
                "total_lines": coverage_result.total_lines,
                "covered_lines": coverage_result.covered_lines,
                "coverage_percent": coverage_result.coverage_percent,
            },
        )
        self.results.append(result)
        return result

    def _run_coverage(self) -> CoverageResult:
        """Run pytest-cov and parse results."""
        try:
            import subprocess
            result = subprocess.run(
                ["pytest", "--cov=.", "--cov-report=json", "-q"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            cov_file = Path("coverage.json")
            if cov_file.exists():
                data = json.loads(cov_file.read_text(encoding="utf-8"))
                totals = data.get("totals", {})
                return CoverageResult(
                    total_lines=totals.get("num_statements", 0),
                    covered_lines=totals.get("covered_lines", 0),
                    coverage_percent=totals.get("percent_covered", 0.0),
                )
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass
        return CoverageResult()

    def run_test_gap_gate(
        self,
        gaps: list[TestGap],
        max_high_severity: int = 0,
    ) -> QualityGateResult:
        """Gate: limit on high-severity test gaps."""
        from testpilot.models import GapSeverity

        high_gaps = [g for g in gaps if g.severity in (GapSeverity.HIGH, GapSeverity.CRITICAL)]
        passed = len(high_gaps) <= max_high_severity

        result = QualityGateResult(
            name="test_gaps",
            status=GateStatus.PASS if passed else GateStatus.FAIL,
            message=f"{len(high_gaps)} high-severity test gaps found (max {max_high_severity})",
            details={
                "total_gaps": len(gaps),
                "high_severity": len(high_gaps),
                "gaps": [
                    {
                        "file": g.file_path,
                        "function": g.function_name,
                        "severity": g.severity.value,
                        "reason": g.reason,
                    }
                    for g in high_gaps[:10]  # Limit details
                ],
            },
        )
        self.results.append(result)
        return result

    def run_visual_gate(
        self,
        results: list[VisualTestResult],
    ) -> QualityGateResult:
        """Gate: visual regression tests must all pass."""
        runner = VisualRegressionRunner(
            baseline_dir=".",
            current_dir=".",
            output_dir="./testpilot-output/visual",
        )
        result = runner.to_quality_gate(results)
        self.results.append(result)
        return result

    def run_contract_gate(
        self,
        contract_results: list[ContractResult],
        provider_url: str,
    ) -> QualityGateResult:
        """Gate: contract tests must all pass."""
        verifier = ContractVerifier(provider_url)
        result = verifier.to_quality_gate(contract_results)
        self.results.append(result)
        return result

    def run_performance_gate(
        self,
        perf_result: PerformanceResult,
        thresholds: PerfThreshold | None = None,
    ) -> QualityGateResult:
        """Gate: performance thresholds must be met."""
        integration = PerfIntegration(tool="locust")
        result = integration.check_thresholds(perf_result, thresholds)
        self.results.append(result)
        return result

    def run_flaky_gate(
        self,
        flaky_reports: list[FlakyTestReport],
    ) -> QualityGateResult:
        """Gate: non-quarantined flaky tests must be minimal."""
        detector = FlakyDetector()
        result = detector.to_quality_gate(flaky_reports)
        self.results.append(result)
        return result

    def overall_status(self) -> GateStatus:
        """Get the overall status across all gates."""
        if not self.results:
            return GateStatus.SKIP
        if any(r.status == GateStatus.FAIL for r in self.results):
            return GateStatus.FAIL
        if all(r.status == GateStatus.PASS for r in self.results):
            return GateStatus.PASS
        return GateStatus.SKIP

    def generate_report(self) -> dict[str, Any]:
        """Generate a comprehensive quality gate report."""
        return {
            "overall_status": self.overall_status().value,
            "gates": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "message": r.message,
                    "details": r.details,
                }
                for r in self.results
            ],
        }

    def save_report(self, path: str | Path = "./testpilot-output/quality-gate-report.json") -> Path:
        """Save the quality gate report to JSON."""
        report_path = Path(path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report = self.generate_report()
        report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        return report_path

    def print_summary(self) -> str:
        """Generate a human-readable summary string."""
        lines = [
            "=" * 60,
            "TESTPILOT QUALITY GATE REPORT",
            "=" * 60,
            f"Overall Status: {self.overall_status().value.upper()}",
            "-" * 60,
        ]

        for result in self.results:
            icon = "PASS" if result.status == GateStatus.PASS else "FAIL" if result.status == GateStatus.FAIL else "SKIP"
            lines.append(f"  [{icon}] {result.name}: {result.message}")

        lines.append("=" * 60)
        return "\n".join(lines)


def load_gates_from_config(config_path: str | Path) -> QualityGateRunner:
    """Load quality gate configuration from a YAML file."""
    import yaml

    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    return QualityGateRunner(config)
