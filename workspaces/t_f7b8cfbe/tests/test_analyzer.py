"""
Tests for ImprovementAnalyzer module.
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.harness.improvement.analyzer import (
    AgentPerformanceMetrics,
    AnalysisReport,
    CodeQualityMetrics,
    ImprovementAnalyzer,
    Severity,
    TestResult,
    TestSuite,
)


@pytest.fixture
def analyzer() -> ImprovementAnalyzer:
    return ImprovementAnalyzer()


@pytest.fixture
def passing_suite() -> TestSuite:
    return TestSuite(results=[
        TestResult(name="test_one", passed=True, duration_ms=50.0),
        TestResult(name="test_two", passed=True, duration_ms=30.0),
        TestResult(name="test_three", passed=True, duration_ms=20.0),
    ])


@pytest.fixture
def mixed_suite() -> TestSuite:
    return TestSuite(results=[
        TestResult(name="test_pass", passed=True, duration_ms=50.0),
        TestResult(name="test_fail", passed=False, duration_ms=100.0, error_message="AssertionError"),
        TestResult(name="test_timeout", passed=False, duration_ms=5000.0, error_message="TimeoutError: operation timed out"),
        TestResult(name="test_flaky", passed=False, duration_ms=200.0, error_message="Flaky test: race condition detected"),
    ])


@pytest.fixture
def sample_python_file() -> str:
    """Create a temporary Python file for code quality analysis."""
    content = """
def simple_function(x):
    return x * 2

def complex_function(n):
    if n > 0:
        if n % 2 == 0:
            return n // 2
        else:
            return n * 3 + 1
    elif n < 0:
        return -n
    else:
        return 0

class MyClass:
    def method_one(self):
        pass

    def method_two(self):
        pass

    def method_three(self):
        pass
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(content)
        return f.name


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Create a temporary project with Python files."""
    (src_dir := tmp_path / "src").mkdir()
    (src_dir / "module.py").write_text("""
def hello():
    return "world"

def add(a, b):
    return a + b

x = 1
y = 2
unused_var = 42
""")
    (src_dir / "utils.py").write_text("""
import os
import json

def helper():
    return os.path.exists("/tmp")
""")
    return tmp_path


class TestTestResult:
    def test_test_result_creation(self) -> None:
        r = TestResult(name="test_x", passed=True, duration_ms=100.0)
        assert r.name == "test_x"
        assert r.passed is True
        assert r.duration_ms == 100.0

    def test_test_result_defaults(self) -> None:
        r = TestResult(name="test_y", passed=False)
        assert r.duration_ms == 0.0
        assert r.error_message == ""
        assert r.file_path == ""


class TestTestSuite:
    def test_total(self, passing_suite: TestSuite) -> None:
        assert passing_suite.total == 3

    def test_passed_count(self, passing_suite: TestSuite) -> None:
        assert passing_suite.passed == 3

    def test_failed_count(self, mixed_suite: TestSuite) -> None:
        assert mixed_suite.failed == 3

    def test_pass_rate_all_pass(self, passing_suite: TestSuite) -> None:
        assert passing_suite.pass_rate == 1.0

    def test_pass_rate_mixed(self, mixed_suite: TestSuite) -> None:
        assert mixed_suite.pass_rate == 0.25

    def test_pass_rate_empty(self) -> None:
        suite = TestSuite()
        assert suite.pass_rate == 0.0

    def test_avg_duration(self, passing_suite: TestSuite) -> None:
        assert passing_suite.avg_duration_ms == pytest.approx(33.33, rel=0.01)

    def test_slowest_tests(self, mixed_suite: TestSuite) -> None:
        slowest = mixed_suite.slowest_tests
        assert len(slowest) == 3
        assert slowest[0].name == "test_timeout"


class TestImprovementAnalyzer:
    def test_record_test_suite(self, analyzer: ImprovementAnalyzer, passing_suite: TestSuite) -> None:
        analyzer.record_test_suite(passing_suite)
        assert len(analyzer.test_history) == 1

    def test_record_code_quality(self, analyzer: ImprovementAnalyzer) -> None:
        metrics = CodeQualityMetrics(total_lines=100, total_files=5)
        analyzer.record_code_quality(metrics)
        assert len(analyzer.quality_history) == 1

    def test_record_agent_performance(self, analyzer: ImprovementAnalyzer) -> None:
        agents = [AgentPerformanceMetrics(agent_name="agent1", success_rate=0.9)]
        analyzer.record_agent_performance(agents)
        assert len(analyzer.agent_history) == 1

    def test_analyze_tests_all_pass(self, analyzer: ImprovementAnalyzer, passing_suite: TestSuite) -> None:
        analysis = analyzer.analyze_tests(passing_suite)
        assert analysis["total"] == 3
        assert analysis["passed"] == 3
        assert analysis["failed"] == 0
        assert analysis["pass_rate"] == 1.0
        assert len(analysis["failures"]) == 0

    def test_analyze_tests_with_failures(self, analyzer: ImprovementAnalyzer, mixed_suite: TestSuite) -> None:
        analysis = analyzer.analyze_tests(mixed_suite)
        assert analysis["failed"] == 3
        assert len(analysis["failures"]) == 3

    def test_analyze_tests_flaky_detection(self, analyzer: ImprovementAnalyzer, mixed_suite: TestSuite) -> None:
        analysis = analyzer.analyze_tests(mixed_suite)
        assert "test_timeout" in analysis["flaky_candidates"]
        assert "test_flaky" in analysis["flaky_candidates"]

    def test_analyze_tests_slow_detection(self, analyzer: ImprovementAnalyzer, mixed_suite: TestSuite) -> None:
        analysis = analyzer.analyze_tests(mixed_suite)
        slow_names = [t["name"] for t in analysis["slow_tests"]]
        assert "test_timeout" in slow_names

    def test_analyze_tests_regression_detection(self, analyzer: ImprovementAnalyzer) -> None:
        suite1 = TestSuite(results=[
            TestResult(name="t1", passed=True),
            TestResult(name="t2", passed=True),
        ])
        suite2 = TestSuite(results=[
            TestResult(name="t1", passed=True),
            TestResult(name="t2", passed=False),
        ])
        analyzer.record_test_suite(suite1)
        analysis = analyzer.analyze_tests(suite2)
        assert analysis["regression"] is True
        assert analysis["delta_pass_rate"] == -0.5

    def test_analyze_code_quality(self, analyzer: ImprovementAnalyzer, temp_project: Path) -> None:
        metrics = analyzer.analyze_code_quality()
        assert metrics.total_files >= 2
        assert metrics.total_lines > 0
        assert metrics.total_functions >= 4

    def test_analyze_code_quality_with_specific_files(self, analyzer: ImprovementAnalyzer, sample_python_file: str) -> None:
        metrics = analyzer.analyze_code_quality([sample_python_file])
        assert metrics.total_files == 1
        assert metrics.total_functions == 5
        assert metrics.total_classes == 1

    def test_analyze_code_quality_syntax_error(self, analyzer: ImprovementAnalyzer, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.py"
        bad_file.write_text("def broken(\n  pass\n")
        metrics = analyzer.analyze_code_quality([str(bad_file)])
        assert any("Syntax error" in i["message"] for i in metrics.issues)

    def test_analyze_agent_performance(self, analyzer: ImprovementAnalyzer) -> None:
        agents = [
            AgentPerformanceMetrics(agent_name="agent1", success_rate=0.9, tasks_completed=90, tasks_failed=10),
            AgentPerformanceMetrics(agent_name="agent2", success_rate=0.5, tasks_completed=50, tasks_failed=50),
        ]
        analysis = analyzer.analyze_agent_performance(agents)
        assert analysis["total_tasks"] == 200
        assert analysis["total_failures"] == 60
        assert analysis["worst_agent"]["name"] == "agent2"
        assert analysis["best_agent"]["name"] == "agent1"

    def test_analyze_agent_performance_empty(self, analyzer: ImprovementAnalyzer) -> None:
        analysis = analyzer.analyze_agent_performance([])
        assert analysis["total_tasks"] == 0

    def test_analyze_agent_performance_improving(self, analyzer: ImprovementAnalyzer) -> None:
        agents1 = [AgentPerformanceMetrics(agent_name="a1", success_rate=0.5)]
        agents2 = [AgentPerformanceMetrics(agent_name="a1", success_rate=0.9)]
        analyzer.record_agent_performance(agents1)
        analysis = analyzer.analyze_agent_performance(agents2)
        assert len(analysis["improving"]) == 1

    def test_generate_recommendations_critical_tests(self, analyzer: ImprovementAnalyzer, mixed_suite: TestSuite) -> None:
        recs = analyzer.generate_recommendations(mixed_suite)
        assert any(r["category"] == "tests" for r in recs)

    def test_generate_recommendations_complexity(self, analyzer: ImprovementAnalyzer) -> None:
        metrics = CodeQualityMetrics(max_cyclomatic_complexity=20)
        analyzer.record_code_quality(metrics)
        recs = analyzer.generate_recommendations()
        assert any(r["action"] == "reduce_complexity" for r in recs)

    def test_generate_recommendations_regression(self, analyzer: ImprovementAnalyzer) -> None:
        suite1 = TestSuite(results=[TestResult(name="t1", passed=True)])
        suite2 = TestSuite(results=[TestResult(name="t1", passed=False)])
        analyzer.record_test_suite(suite1)
        analyzer.record_test_suite(suite2)
        recs = analyzer.generate_recommendations()
        assert any(r["action"] == "halt_and_fix" for r in recs)

    def test_compute_health_score_with_suite(self, analyzer: ImprovementAnalyzer, passing_suite: TestSuite) -> None:
        score = analyzer.compute_health_score(passing_suite)
        assert score == 1.0

    def test_compute_health_score_empty(self, analyzer: ImprovementAnalyzer) -> None:
        score = analyzer.compute_health_score()
        assert score == 0.5

    def test_generate_report(self, analyzer: ImprovementAnalyzer, passing_suite: TestSuite) -> None:
        report = analyzer.generate_report(passing_suite)
        assert isinstance(report, AnalysisReport)
        assert report.test_suite is not None
        assert report.overall_health_score > 0

    def test_cyclomatic_complexity(self, analyzer: ImprovementAnalyzer) -> None:
        source = """
def simple():
    pass

def complex_func(x):
    if x > 0:
        if x % 2 == 0:
            return 1
        elif x % 3 == 0:
            return 2
    else:
        return 3
"""
        tree = __import__("ast").parse(source)
        for node in __import__("ast").walk(tree):
            if isinstance(node, __import__("ast").FunctionDef) and node.name == "simple":
                assert analyzer._cyclomatic_complexity(node) == 1
            if isinstance(node, __import__("ast").FunctionDef) and node.name == "complex_func":
                assert analyzer._cyclomatic_complexity(node) > 1

    def test_maintainability_index(self, analyzer: ImprovementAnalyzer) -> None:
        metrics = CodeQualityMetrics(avg_cyclomatic_complexity=5.0, max_function_length=30, duplication_score=0.05)
        mi = analyzer._compute_maintainability(metrics)
        assert 0 <= mi <= 100

    def test_duplication_score(self, analyzer: ImprovementAnalyzer, tmp_path: Path) -> None:
        (f1 := tmp_path / "a.py").write_text("x = 1\ny = 2\nz = 3\n")
        (f2 := tmp_path / "b.py").write_text("x = 1\ny = 2\nz = 3\n")
        score = analyzer._estimate_duplication([str(f1), str(f2)])
        assert score > 0.5
