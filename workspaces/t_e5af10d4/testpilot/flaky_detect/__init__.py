"""Flaky test detection and quarantine."""
from __future__ import annotations

import json
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from testpilot.models import FlakyTestReport, GateStatus, QualityGateResult


@dataclass
class TestRunRecord:
    """Record of a single test execution."""
    test_id: str
    file_path: str
    test_name: str
    passed: bool
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error_message: str = ""


class FlakyDetector:
    """Detects flaky tests by analyzing historical test results."""

    def __init__(
        self,
        max_failure_rate: float = 0.05,
        min_runs_for_analysis: int = 5,
        quarantine_threshold: float = 0.15,
    ) -> None:
        self.max_failure_rate = max_failure_rate
        self.min_runs_for_analysis = min_runs_for_analysis
        self.quarantine_threshold = quarantine_threshold
        self._history: dict[str, list[TestRunRecord]] = defaultdict(list)
        self._quarantined: set[str] = set()

    def add_result(self, result: TestRunRecord) -> None:
        """Add a test run result to the history."""
        self._history[result.test_id].append(result)

    def add_results(self, results: list[TestRunRecord]) -> None:
        """Add multiple test run results."""
        for result in results:
            self.add_result(result)

    def detect(self) -> list[FlakyTestReport]:
        """Analyze history and return flaky test reports."""
        reports: list[FlakyTestReport] = []

        for test_id, records in self._history.items():
            if len(records) < self.min_runs_for_analysis:
                continue

            failures = sum(1 for r in records if not r.passed)
            failure_rate = failures / len(records)

            if failure_rate > 0 and failure_rate <= self.max_failure_rate:
                # Flaky: some passes, some failures, but failure rate is low
                last_failure = next(
                    (r for r in reversed(records) if not r.passed), None
                )
                reports.append(
                    FlakyTestReport(
                        test_id=test_id,
                        file_path=records[0].file_path,
                        test_name=records[0].test_name,
                        total_runs=len(records),
                        failures=failures,
                        failure_rate=round(failure_rate, 4),
                        is_quarantined=test_id in self._quarantined,
                        last_failure_message=(
                            last_failure.error_message if last_failure else ""
                        ),
                    )
                )

        return sorted(reports, key=lambda r: r.failure_rate, reverse=True)

    def quarantine(self, test_id: str) -> None:
        """Add a test to the quarantine list."""
        self._quarantined.add(test_id)

    def unquarantine(self, test_id: str) -> None:
        """Remove a test from the quarantine list."""
        self._quarantined.discard(test_id)

    def is_quarantined(self, test_id: str) -> bool:
        """Check if a test is quarantined."""
        return test_id in self._quarantined

    def auto_quarantine(self) -> list[str]:
        """Automatically quarantine tests exceeding the quarantine threshold."""
        quarantined: list[str] = []
        for test_id, records in self._history.items():
            if len(records) < self.min_runs_for_analysis:
                continue
            failures = sum(1 for r in records if not r.passed)
            rate = failures / len(records)
            if rate >= self.quarantine_threshold and test_id not in self._quarantined:
                self._quarantined.add(test_id)
                quarantined.append(test_id)
        return quarantined

    def to_quality_gate(self, reports: list[FlakyTestReport]) -> QualityGateResult:
        """Convert flaky test reports to a quality gate result."""
        active_flaky = [r for r in reports if not r.is_quarantined]
        quarantined = [r for r in reports if r.is_quarantined]

        details: dict[str, Any] = {
            "total_flaky_detected": len(reports),
            "active_flaky": len(active_flaky),
            "quarantined": len(quarantined),
            "flaky_tests": [
                {
                    "test_id": r.test_id,
                    "failure_rate": r.failure_rate,
                    "total_runs": r.total_runs,
                    "quarantined": r.is_quarantined,
                }
                for r in reports
            ],
        }

        # Gate fails if there are non-quarantined flaky tests
        status = GateStatus.PASS if not active_flaky else GateStatus.FAIL
        return QualityGateResult(
            name="flaky_test_detection",
            status=status,
            message=(
                f"{len(active_flaky)} active flaky test(s), "
                f"{len(quarantined)} quarantined"
            ),
            details=details,
        )


def parse_pytest_results(json_path: str | Path) -> list[TestRunRecord]:
    """Parse pytest JSON results into TestRunRecords."""
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    records: list[TestRunRecord] = []

    for test in data.get("tests", []):
        nodeid = test.get("nodeid", "")
        # Parse nodeid to extract file path and test name
        if "::" in nodeid:
            file_path, test_name = nodeid.split("::", 1)
        else:
            file_path, test_name = "", nodeid

        outcome = test.get("outcome", "passed")
        call = test.get("call", {})

        records.append(
            TestRunRecord(
                test_id=nodeid,
                file_path=file_path,
                test_name=test_name,
                passed=outcome == "passed",
                duration_ms=call.get("duration", 0) * 1000,
                error_message=call.get("longrepr", "") if outcome != "passed" else "",
            )
        )

    return records


def run_pytest_and_detect(
    test_paths: list[str],
    reruns: int = 3,
    output_dir: str = "./testpilot-output/flaky",
) -> tuple[list[FlakyTestReport], Path]:
    """Run pytest with reruns and analyze results for flakiness."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results_file = output_path / "pytest-results.json"

    cmd = [
        "pytest",
        *test_paths,
        "--json-report",
        f"--json-report-file={results_file}",
        f"--reruns={reruns}",
        "--reruns-delay=1",
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    if results_file.exists():
        records = parse_pytest_results(results_file)
        detector = FlakyDetector()
        detector.add_results(records)
        reports = detector.detect()
    else:
        reports = []

    return reports, results_file
