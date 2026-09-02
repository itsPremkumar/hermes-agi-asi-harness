"""Tests for flaky test detection."""
from datetime import datetime

from testpilot.flaky_detect import FlakyDetector, TestRunRecord, parse_pytest_results


def test_detect_flaky_test() -> None:
    """Should detect a test with intermittent failures."""
    detector = FlakyDetector(max_failure_rate=0.5, min_runs_for_analysis=3)
    for i in range(10):
        detector.add_result(
            TestRunRecord(
                test_id="test_login",
                file_path="tests/test_auth.py",
                test_name="test_login",
                passed=(i != 3 and i != 7),  # 2 failures out of 10
                duration_ms=100.0,
            )
        )

    reports = detector.detect()
    assert len(reports) == 1
    assert reports[0].test_id == "test_login"
    assert reports[0].failure_rate == 0.2


def test_no_flaky_for_always_passing() -> None:
    """Always-passing tests should not be flagged as flaky."""
    detector = FlakyDetector(min_runs_for_analysis=3)
    for _ in range(10):
        detector.add_result(
            TestRunRecord(
                test_id="test_always_pass",
                file_path="tests/test_stable.py",
                test_name="test_stable",
                passed=True,
            )
        )

    reports = detector.detect()
    assert len(reports) == 0


def test_quarantine() -> None:
    """Quarantined tests should be tracked."""
    detector = FlakyDetector()
    detector.quarantine("test_login")
    assert detector.is_quarantined("test_login")
    detector.unquarantine("test_login")
    assert not detector.is_quarantined("test_login")


def test_auto_quarantine() -> None:
    """Tests above threshold should be auto-quarantined."""
    detector = FlakyDetector(
        quarantine_threshold=0.2,
        min_runs_for_analysis=3,
    )
    for i in range(10):
        # 30% failure rate
        detector.add_result(
            TestRunRecord(
                test_id="test_flaky",
                file_path="tests/test_api.py",
                test_name="test_api",
                passed=(i % 3 != 0),
            )
        )

    quarantined = detector.auto_quarantine()
    assert "test_flaky" in quarantined


def test_min_runs_not_met() -> None:
    """Tests with too few runs should not be analyzed."""
    detector = FlakyDetector(min_runs_for_analysis=10)
    for i in range(3):
        detector.add_result(
            TestRunRecord(
                test_id="test_few_runs",
                file_path="tests/test_new.py",
                test_name="test_new",
                passed=(i == 0),  # Only 1 pass out of 3
            )
        )

    reports = detector.detect()
    assert len(reports) == 0  # Not enough runs


def test_parse_pytest_results(tmp_path) -> None:
    """Should parse pytest JSON report."""
    import json

    pytest_data = {
        "tests": [
            {
                "nodeid": "tests/test_example.py::test_one",
                "outcome": "passed",
                "call": {"duration": 0.05},
            },
            {
                "nodeid": "tests/test_example.py::test_two",
                "outcome": "failed",
                "call": {"duration": 0.1, "longrepr": "AssertionError"},
            },
        ]
    }

    results_file = tmp_path / "results.json"
    results_file.write_text(json.dumps(pytest_data), encoding="utf-8")

    records = parse_pytest_results(results_file)
    assert len(records) == 2
    assert records[0].passed is True
    assert records[1].passed is False
    assert records[1].error_message == "AssertionError"
