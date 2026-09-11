"""
ImprovementAnalyzer — Analyze test results, code quality metrics, and agent performance.
"""

from __future__ import annotations

import ast
import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TestResult:
    """Result from a single test execution."""

    name: str
    passed: bool
    duration_ms: float = 0.0
    error_message: str = ""
    file_path: str = ""


@dataclass
class TestSuite:
    """Collection of test results."""

    results: list[TestResult] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total > 0 else 0.0

    @property
    def avg_duration_ms(self) -> float:
        durations = [r.duration_ms for r in self.results if r.duration_ms > 0]
        return statistics.mean(durations) if durations else 0.0

    @property
    def slowest_tests(self) -> list[TestResult]:
        failed = [r for r in self.results if not r.passed]
        return sorted(failed, key=lambda r: r.duration_ms, reverse=True)


@dataclass
class CodeQualityMetrics:
    """Aggregated code quality metrics for a codebase."""

    total_lines: int = 0
    total_files: int = 0
    avg_cyclomatic_complexity: float = 0.0
    max_cyclomatic_complexity: int = 0
    total_functions: int = 0
    total_classes: int = 0
    avg_function_length: float = 0.0
    max_function_length: int = 0
    duplication_score: float = 0.0
    maintainability_index: float = 0.0
    issues: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class AgentPerformanceMetrics:
    """Performance metrics for a single agent."""

    agent_name: str
    tasks_completed: int = 0
    tasks_failed: int = 0
    avg_task_duration_ms: float = 0.0
    avg_quality_score: float = 0.0
    avg_rework_count: float = 0.0
    success_rate: float = 0.0
    last_active: datetime | None = None


@dataclass
class AnalysisReport:
    """Complete analysis report combining all metrics."""

    timestamp: datetime = field(default_factory=datetime.utcnow)
    test_suite: TestSuite | None = None
    code_quality: CodeQualityMetrics | None = None
    agent_performance: list[AgentPerformanceMetrics] = field(default_factory=list)
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    overall_health_score: float = 0.0


class ImprovementAnalyzer:
    """Analyzes test results, code quality metrics, and agent performance to produce actionable insights."""

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self._test_history: list[TestSuite] = []
        self._quality_history: list[CodeQualityMetrics] = []
        self._agent_history: list[list[AgentPerformanceMetrics]] = []

    @property
    def test_history(self) -> list[TestSuite]:
        return list(self._test_history)

    @property
    def quality_history(self) -> list[CodeQualityMetrics]:
        return list(self._quality_history)

    @property
    def agent_history(self) -> list[list[AgentPerformanceMetrics]]:
        return [list(a) for a in self._agent_history]

    def record_test_suite(self, suite: TestSuite) -> None:
        """Record a test suite result for trend analysis."""
        self._test_history.append(suite)

    def record_code_quality(self, metrics: CodeQualityMetrics) -> None:
        """Record code quality metrics for trend analysis."""
        self._quality_history.append(metrics)

    def record_agent_performance(self, agents: list[AgentPerformanceMetrics]) -> None:
        """Record agent performance for trend analysis."""
        self._agent_history.append(agents)

    def analyze_tests(self, suite: TestSuite) -> dict[str, Any]:
        """Analyze test results and return structured findings."""
        analysis: dict[str, Any] = {
            "total": suite.total,
            "passed": suite.passed,
            "failed": suite.failed,
            "pass_rate": suite.pass_rate,
            "avg_duration_ms": suite.avg_duration_ms,
            "failures": [],
            "slow_tests": [],
            "flaky_candidates": [],
        }

        for result in suite.results:
            if not result.passed:
                analysis["failures"].append({
                    "name": result.name,
                    "error": result.error_message,
                    "file": result.file_path,
                })
            if result.duration_ms > suite.avg_duration_ms * 2 and result.duration_ms > 1000:
                analysis["slow_tests"].append({
                    "name": result.name,
                    "duration_ms": result.duration_ms,
                })

        # Detect flaky candidates: tests that failed with timing-related errors
        for result in suite.results:
            if not result.passed:
                err_lower = result.error_message.lower()
                if any(kw in err_lower for kw in ("timeout", "flaky", "race", "deadlock", "concurrent")):
                    analysis["flaky_candidates"].append(result.name)

        # Compare with previous suite if available
        if self._test_history:
            prev = self._test_history[-1]
            analysis["delta_pass_rate"] = suite.pass_rate - prev.pass_rate
            analysis["delta_failed"] = suite.failed - prev.failed
            analysis["regression"] = suite.failed > prev.failed

        return analysis

    def analyze_code_quality(self, file_paths: list[str] | list[Path] | None = None) -> CodeQualityMetrics:
        """Analyze code quality metrics from source files."""
        if file_paths is None:
            file_paths = [
                str(p) for p in self.project_root.rglob("*.py")
                if "test" not in p.name and "__pycache__" not in str(p)
            ]
        else:
            file_paths = [str(p) for p in file_paths]

        metrics = CodeQualityMetrics()
        all_function_lengths: list[int] = []
        all_complexities: list[int] = []

        for fp in file_paths:
            try:
                source = Path(fp).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            lines = source.splitlines()
            metrics.total_lines += len(lines)
            metrics.total_files += 1

            try:
                tree = ast.parse(source)
            except SyntaxError:
                metrics.issues.append({
                    "file": fp,
                    "severity": Severity.HIGH.value,
                    "message": "Syntax error — file cannot be parsed",
                })
                continue

            self._analyze_ast(tree, fp, metrics, all_function_lengths, all_complexities)

        if all_function_lengths:
            metrics.avg_function_length = statistics.mean(all_function_lengths)
            metrics.max_function_length = max(all_function_lengths)

        if all_complexities:
            metrics.avg_cyclomatic_complexity = statistics.mean(all_complexities)
            metrics.max_cyclomatic_complexity = max(all_complexities)

        metrics.maintainability_index = self._compute_maintainability(metrics)
        metrics.duplication_score = self._estimate_duplication(file_paths)

        return metrics

    def _analyze_ast(
        self,
        tree: ast.AST,
        file_path: str,
        metrics: CodeQualityMetrics,
        fn_lengths: list[int],
        complexities: list[int],
    ) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                metrics.total_functions += 1
                length = (node.end_lineno or node.lineno) - node.lineno
                fn_lengths.append(length)

                if length > 50:
                    metrics.issues.append({
                        "file": file_path,
                        "function": node.name,
                        "line": node.lineno,
                        "severity": Severity.MEDIUM.value,
                        "message": f"Function '{node.name}' is {length} lines (threshold: 50)",
                    })

                complexity = self._cyclomatic_complexity(node)
                complexities.append(complexity)
                if complexity > 10:
                    metrics.issues.append({
                        "file": file_path,
                        "function": node.name,
                        "line": node.lineno,
                        "severity": Severity.HIGH.value,
                        "message": f"Function '{node.name}' has cyclomatic complexity {complexity} (threshold: 10)",
                    })

            elif isinstance(node, ast.ClassDef):
                metrics.total_classes += 1
                method_count = sum(
                    1 for item in node.body
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                )
                if method_count > 20:
                    metrics.issues.append({
                        "file": file_path,
                        "class": node.name,
                        "line": node.lineno,
                        "severity": Severity.MEDIUM.value,
                        "message": f"Class '{node.name}' has {method_count} methods (threshold: 20)",
                    })

    @staticmethod
    def _cyclomatic_complexity(node: ast.AST) -> int:
        """Compute cyclomatic complexity for a function node."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.With):
                complexity += len(child.items) - 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    @staticmethod
    def _compute_maintainability(metrics: CodeQualityMetrics) -> float:
        """Estimate maintainability index (0-100, higher is better)."""
        score = 100.0
        if metrics.avg_cyclomatic_complexity > 0:
            score -= min(30.0, metrics.avg_cyclomatic_complexity * 1.5)
        if metrics.max_function_length > 0:
            score -= min(20.0, metrics.max_function_length / 5.0)
        if metrics.duplication_score > 0:
            score -= min(20.0, metrics.duplication_score * 2.0)
        return max(0.0, min(100.0, score))

    @staticmethod
    def _estimate_duplication(file_paths: list[str]) -> float:
        """Estimate code duplication ratio (0.0 = none, 1.0 = fully duplicated)."""
        line_sets: list[set[str]] = []
        for fp in file_paths:
            try:
                source = Path(fp).read_text(encoding="utf-8")
                lines = {line.strip() for line in source.splitlines() if line.strip() and not line.strip().startswith("#")}
                if lines:
                    line_sets.append(lines)
            except (OSError, UnicodeDecodeError):
                continue

        if len(line_sets) < 2:
            return 0.0

        total_unique: set[str] = set()
        duplicated: set[str] = set()
        for ls in line_sets:
            duplicated |= total_unique & ls
            total_unique |= ls

        return len(duplicated) / len(total_unique) if total_unique else 0.0

    def analyze_agent_performance(self, agents: list[AgentPerformanceMetrics]) -> dict[str, Any]:
        """Analyze agent performance metrics and identify underperformers."""
        analysis: dict[str, Any] = {
            "agents": [],
            "total_tasks": 0,
            "total_failures": 0,
            "overall_success_rate": 0.0,
            "slowest_agent": None,
            "worst_agent": None,
            "best_agent": None,
            "improving": [],
            "declining": [],
        }

        if not agents:
            return analysis

        for agent in agents:
            agent_entry = {
                "name": agent.agent_name,
                "success_rate": agent.success_rate,
                "avg_duration_ms": agent.avg_task_duration_ms,
                "avg_quality": agent.avg_quality_score,
                "tasks_completed": agent.tasks_completed,
                "tasks_failed": agent.tasks_failed,
            }
            analysis["agents"].append(agent_entry)
            analysis["total_tasks"] += agent.tasks_completed + agent.tasks_failed
            analysis["total_failures"] += agent.tasks_failed

        total_success = sum(a.success_rate for a in agents)
        analysis["overall_success_rate"] = total_success / len(agents)

        slowest = max(agents, key=lambda a: a.avg_task_duration_ms)
        analysis["slowest_agent"] = {
            "name": slowest.agent_name,
            "avg_duration_ms": slowest.avg_task_duration_ms,
        }

        worst = min(agents, key=lambda a: a.success_rate)
        analysis["worst_agent"] = {
            "name": worst.agent_name,
            "success_rate": worst.success_rate,
        }

        best = max(agents, key=lambda a: a.success_rate)
        analysis["best_agent"] = {
            "name": best.agent_name,
            "success_rate": best.success_rate,
        }

        # Compare with historical data
        if self._agent_history:
            prev_agents = {a.agent_name: a for a in self._agent_history[-1]}
            for agent in agents:
                if agent.agent_name in prev_agents:
                    delta = agent.success_rate - prev_agents[agent.agent_name].success_rate
                    if delta > 0.05:
                        analysis["improving"].append({"name": agent.agent_name, "delta": delta})
                    elif delta < -0.05:
                        analysis["declining"].append({"name": agent.agent_name, "delta": delta})

        return analysis

    def generate_recommendations(self, suite: TestSuite | None = None) -> list[dict[str, Any]]:
        """Generate actionable recommendations based on all available data."""
        recommendations: list[dict[str, Any]] = []

        if suite and suite.failed > 0:
            recommendations.append({
                "priority": 1,
                "category": "tests",
                "severity": Severity.CRITICAL.value,
                "message": f"Fix {suite.failed} failing test(s) immediately",
                "action": "investigate_failures",
            })

        if self._quality_history:
            latest = self._quality_history[-1]
            if latest.max_cyclomatic_complexity > 15:
                recommendations.append({
                    "priority": 2,
                    "category": "complexity",
                    "severity": Severity.HIGH.value,
                    "message": f"Refactor functions with complexity > 15 (max found: {latest.max_cyclomatic_complexity})",
                    "action": "reduce_complexity",
                })
            if latest.max_function_length > 80:
                recommendations.append({
                    "priority": 3,
                    "category": "readability",
                    "severity": Severity.MEDIUM.value,
                    "message": f"Split functions longer than 80 lines (max: {latest.max_function_length})",
                    "action": "split_functions",
                })
            if latest.duplication_score > 0.1:
                recommendations.append({
                    "priority": 4,
                    "category": "duplication",
                    "severity": Severity.MEDIUM.value,
                    "message": f"Reduce code duplication (score: {latest.duplication_score:.2f})",
                    "action": "deduplicate",
                })
            if latest.maintainability_index < 60:
                recommendations.append({
                    "priority": 5,
                    "category": "maintainability",
                    "severity": Severity.HIGH.value,
                    "message": f"Improve maintainability index (current: {latest.maintainability_index:.1f}/100)",
                    "action": "improve_maintainability",
                })

        if self._agent_history:
            latest_agents = self._agent_history[-1]
            for agent in latest_agents:
                if agent.success_rate < 0.7:
                    recommendations.append({
                        "priority": 6,
                        "category": "agent",
                        "severity": Severity.HIGH.value,
                        "message": f"Investigate agent '{agent.agent_name}' with low success rate ({agent.success_rate:.1%})",
                        "action": "review_agent",
                    })
                if agent.avg_rework_count > 2:
                    recommendations.append({
                        "priority": 7,
                        "category": "quality",
                        "severity": Severity.MEDIUM.value,
                        "message": f"Agent '{agent.agent_name}' has high rework count ({agent.avg_rework_count:.1f})",
                        "action": "improve_agent_quality",
                    })

        if self._test_history and len(self._test_history) >= 2:
            recent = self._test_history[-2:]
            if recent[1].pass_rate < recent[0].pass_rate:
                recommendations.append({
                    "priority": 8,
                    "category": "regression",
                    "severity": Severity.CRITICAL.value,
                    "message": f"Pass rate declined from {recent[0].pass_rate:.1%} to {recent[1].pass_rate:.1%}",
                    "action": "halt_and_fix",
                })

        return sorted(recommendations, key=lambda r: r["priority"])

    def compute_health_score(self, suite: TestSuite | None = None) -> float:
        """Compute overall health score (0.0 to 1.0)."""
        scores: list[float] = []

        if suite is not None:
            scores.append(suite.pass_rate)

        if self._quality_history:
            mi = self._quality_history[-1].maintainability_index
            scores.append(mi / 100.0)

        if self._agent_history:
            latest = self._agent_history[-1]
            if latest:
                avg_success = statistics.mean(a.success_rate for a in latest)
                scores.append(avg_success)

        return statistics.mean(scores) if scores else 0.5

    def generate_report(self, suite: TestSuite | None = None) -> AnalysisReport:
        """Generate a comprehensive analysis report."""
        test_analysis = self.analyze_tests(suite) if suite else {}
        recommendations = self.generate_recommendations(suite)
        health = self.compute_health_score(suite)

        report = AnalysisReport(
            test_suite=suite,
            recommendations=recommendations,
            overall_health_score=health,
        )

        if self._quality_history:
            report.code_quality = self._quality_history[-1]

        if self._agent_history:
            report.agent_performance = self._agent_history[-1]

        return report
