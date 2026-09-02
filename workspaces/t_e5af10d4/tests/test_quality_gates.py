"""Tests for quality gate runner."""
import pytest

from testpilot.models import (
    ContractDefinition,
    FlakyTestReport,
    GateStatus,
    PerformanceResult,
    QualityGateResult,
    TestGap,
    VisualTestResult,
    GapSeverity,
)
from testpilot.quality_gates import QualityGateRunner, CoverageResult


def test_coverage_gate_passes() -> None:
    """Coverage gate should pass when coverage meets threshold."""
    runner = QualityGateRunner()
    result = runner.run_coverage_gate(
        CoverageResult(total_lines=100, covered_lines=85, coverage_percent=85.0),
        min_percent=80.0,
    )
    assert result.status == GateStatus.PASS


def test_coverage_gate_fails() -> None:
    """Coverage gate should fail when coverage is below threshold."""
    runner = QualityGateRunner()
    result = runner.run_coverage_gate(
        CoverageResult(total_lines=100, covered_lines=60, coverage_percent=60.0),
        min_percent=80.0,
    )
    assert result.status == GateStatus.FAIL


def test_test_gap_gate() -> None:
    """Test gap gate should fail when high-severity gaps exceed limit."""
    runner = QualityGateRunner()
    gaps = [
        TestGap(
            file_path="src/app.py",
            function_name="critical_func",
            line_start=10,
            line_end=20,
            severity=GapSeverity.CRITICAL,
            reason="Untested critical function",
        )
    ]
    result = runner.run_test_gap_gate(gaps, max_high_severity=0)
    assert result.status == GateStatus.FAIL


def test_visual_gate_all_pass() -> None:
    """Visual gate should pass when all images match."""
    runner = QualityGateRunner()
    results = [
        VisualTestResult(name="homepage", passed=True),
        VisualTestResult(name="dashboard", passed=True),
    ]
    result = runner.run_visual_gate(results)
    assert result.status == GateStatus.PASS


def test_visual_gate_some_fail() -> None:
    """Visual gate should fail when any image differs."""
    runner = QualityGateRunner()
    results = [
        VisualTestResult(name="homepage", passed=True),
        VisualTestResult(name="dashboard", passed=False),
    ]
    result = runner.run_visual_gate(results)
    assert result.status == GateStatus.FAIL


def test_flaky_gate_passes_with_no_flaky() -> None:
    """Flaky gate should pass when no flaky tests exist."""
    runner = QualityGateRunner()
    result = runner.run_flaky_gate([])
    assert result.status == GateStatus.PASS


def test_flaky_gate_fails_with_active_flaky() -> None:
    """Flaky gate should fail when non-quarantined flaky tests exist."""
    runner = QualityGateRunner()
    reports = [
        FlakyTestReport(
            test_id="test_login",
            file_path="tests/test_auth.py",
            test_name="test_login",
            total_runs=20,
            failures=2,
            failure_rate=0.1,
            is_quarantined=False,
        )
    ]
    result = runner.run_flaky_gate(reports)
    assert result.status == GateStatus.FAIL


def test_flaky_gate_passes_with_quarantined() -> None:
    """Flaky gate should pass when all flaky tests are quarantined."""
    runner = QualityGateRunner()
    reports = [
        FlakyTestReport(
            test_id="test_login",
            file_path="tests/test_auth.py",
            test_name="test_login",
            total_runs=20,
            failures=3,
            failure_rate=0.15,
            is_quarantined=True,
        )
    ]
    result = runner.run_flaky_gate(reports)
    assert result.status == GateStatus.PASS


def test_overall_status_all_pass() -> None:
    """Overall status should be PASS when all gates pass."""
    runner = QualityGateRunner()
    runner.results = [
        QualityGateResult(name="a", status=GateStatus.PASS),
        QualityGateResult(name="b", status=GateStatus.PASS),
    ]
    assert runner.overall_status() == GateStatus.PASS


def test_overall_status_one_fail() -> None:
    """Overall status should be FAIL when any gate fails."""
    runner = QualityGateRunner()
    runner.results = [
        QualityGateResult(name="a", status=GateStatus.PASS),
        QualityGateResult(name="b", status=GateStatus.FAIL),
    ]
    assert runner.overall_status() == GateStatus.FAIL


def test_generate_report() -> None:
    """Report should include all gates."""
    runner = QualityGateRunner()
    runner.results = [
        QualityGateResult(name="coverage", status=GateStatus.PASS, message="ok"),
    ]
    report = runner.generate_report()
    assert report["overall_status"] == "pass"
    assert len(report["gates"]) == 1


def test_print_summary() -> None:
    """Summary should be a string with status."""
    runner = QualityGateRunner()
    runner.results = [
        QualityGateResult(name="coverage", status=GateStatus.PASS, message="ok"),
    ]
    summary = runner.print_summary()
    assert "PASS" in summary
    assert "coverage" in summary
