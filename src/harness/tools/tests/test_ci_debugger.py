"""Tests for CI Debugger."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src"))

from harness.tools.ci_debugger import (
    CIDebugger,
    TestResult,
    CIDebugResult,
)


class TestTestResult:
    def test_create(self):
        tr = TestResult("test1", True, 1.5, "output")
        assert tr.test_name == "test1"
        assert tr.passed is True


class TestCIDebugger:
    def test_create(self):
        debugger = CIDebugger()
        assert debugger is not None

    def test_add_local_result(self):
        debugger = CIDebugger()
        debugger.add_local_result(TestResult("t1", True, 1.0, ""))
        assert "t1" in debugger._local_results

    def test_add_ci_result(self):
        debugger = CIDebugger()
        debugger.add_ci_result(TestResult("t1", False, 1.0, ""))
        assert "t1" in debugger._ci_results

    def test_diagnose_env_difference(self):
        debugger = CIDebugger()
        debugger.add_local_result(TestResult("t1", True, 1.0, ""))
        debugger.add_ci_result(TestResult("t1", False, 1.0, ""))
        result = debugger.diagnose("t1")
        assert result.root_cause == "Environment difference"
        assert result.confidence == 0.7

    def test_diagnose_local_issue(self):
        debugger = CIDebugger()
        debugger.add_local_result(TestResult("t1", False, 1.0, ""))
        debugger.add_ci_result(TestResult("t1", True, 1.0, ""))
        result = debugger.diagnose("t1")
        assert result.root_cause == "Local environment issue"

    def test_diagnose_genuine_failure(self):
        debugger = CIDebugger()
        debugger.add_local_result(TestResult("t1", False, 1.0, ""))
        debugger.add_ci_result(TestResult("t1", False, 1.0, ""))
        result = debugger.diagnose("t1")
        assert result.root_cause == "Genuine test failure"
        assert result.confidence == 0.9

    def test_diagnose_flaky(self):
        debugger = CIDebugger()
        debugger.add_local_result(TestResult("t1", True, 1.0, ""))
        debugger.add_ci_result(TestResult("t1", True, 1.0, ""))
        result = debugger.diagnose("t1")
        assert result.root_cause == "Flaky test"

    def test_diagnose_no_data(self):
        debugger = CIDebugger()
        result = debugger.diagnose("nonexistent")
        assert result.root_cause == "No data"
        assert result.confidence == 0.0

    def test_diagnose_all(self):
        debugger = CIDebugger()
        debugger.add_local_result(TestResult("t1", True, 1.0, ""))
        debugger.add_ci_result(TestResult("t1", False, 1.0, ""))
        debugger.add_local_result(TestResult("t2", True, 1.0, ""))
        debugger.add_ci_result(TestResult("t2", True, 1.0, ""))
        results = debugger.diagnose_all()
        assert len(results) == 2

    def test_get_flaky_tests(self):
        debugger = CIDebugger()
        debugger.add_local_result(TestResult("t1", True, 1.0, ""))
        debugger.add_ci_result(TestResult("t1", False, 1.0, ""))
        debugger.add_local_result(TestResult("t2", True, 1.0, ""))
        debugger.add_ci_result(TestResult("t2", True, 1.0, ""))
        flaky = debugger.get_flaky_tests()
        assert "t1" in flaky
        assert "t2" not in flaky


class TestCIDebugResult:
    def test_create(self):
        result = CIDebugResult("t1", None, None, "cause", "rec", 0.5)
        assert result.test_name == "t1"
        assert result.confidence == 0.5
