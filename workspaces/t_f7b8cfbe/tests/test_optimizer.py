"""
Tests for AutoOptimizer module.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.harness.improvement.analyzer import CodeQualityMetrics
from src.harness.improvement.optimizer import (
    AutoOptimizer,
    OptimizationPlan,
    OptimizationResult,
)


@pytest.fixture
def optimizer(tmp_path: Path) -> AutoOptimizer:
    return AutoOptimizer(project_root=tmp_path, dry_run=True)


@pytest.fixture
def optimizer_live(tmp_path: Path) -> AutoOptimizer:
    return AutoOptimizer(project_root=tmp_path, dry_run=False)


@pytest.fixture
def file_with_unused_import(tmp_path: Path) -> Path:
    f = tmp_path / "module.py"
    f.write_text("import os\nimport json\n\ndef hello():\n    return 'world'\n")
    return f


@pytest.fixture
def file_with_long_function(tmp_path: Path) -> Path:
    f = tmp_path / "long.py"
    lines = ["def big_function():\n"]
    for i in range(60):
        lines.append(f"    x_{i} = {i}\n")
    lines.append("    return x_0\n")
    f.write_text("".join(lines))
    return f


@pytest.fixture
def file_with_trailing_whitespace(tmp_path: Path) -> Path:
    f = tmp_path / "whitespace.py"
    f.write_text("def clean():\n    return 42   \n\n")
    return f


class TestOptimizationResult:
    def test_lines_saved(self) -> None:
        r = OptimizationResult(file_path="test.py", lines_before=100, lines_after=80)
        assert r.lines_saved == 20

    def test_lines_saved_negative(self) -> None:
        r = OptimizationResult(file_path="test.py", lines_before=80, lines_after=100)
        assert r.lines_saved == -20

    def test_default_success(self) -> None:
        r = OptimizationResult(file_path="test.py")
        assert r.success is True


class TestOptimizationPlan:
    def test_plan_creation(self) -> None:
        plan = OptimizationPlan(file_path="test.py", estimated_impact="high")
        assert plan.file_path == "test.py"
        assert plan.estimated_impact == "high"
        assert plan.auto_applicable is True

    def test_plan_with_issues(self) -> None:
        plan = OptimizationPlan(
            file_path="test.py",
            target_issues=[{"severity": "high", "message": "test"}],
        )
        assert len(plan.target_issues) == 1


class TestAutoOptimizer:
    def test_plan_optimizations(self, optimizer: AutoOptimizer) -> None:
        metrics = CodeQualityMetrics(issues=[
            {"file": "test.py", "severity": "high", "message": "Function too complex"},
            {"file": "test2.py", "severity": "low", "message": "Unused import"},
        ])
        plans = optimizer.plan_optimizations(metrics)
        assert len(plans) == 2

    def test_plan_optimizations_complexity_not_auto(self, optimizer: AutoOptimizer) -> None:
        metrics = CodeQualityMetrics(issues=[
            {"file": "test.py", "severity": "high", "message": "Refactor functions with complexity > 15"},
        ])
        plans = optimizer.plan_optimizations(metrics)
        assert plans[0].auto_applicable is False

    def test_plan_optimizations_critical_impact(self, optimizer: AutoOptimizer) -> None:
        metrics = CodeQualityMetrics(issues=[
            {"file": "test.py", "severity": "critical", "message": "Syntax error"},
        ])
        plans = optimizer.plan_optimizations(metrics)
        assert plans[0].estimated_impact == "high"
        assert plans[0].auto_applicable is False

    def test_apply_optimizations_empty(self, optimizer: AutoOptimizer) -> None:
        results = optimizer.apply_optimizations([])
        assert results == []

    def test_apply_optimizations_non_auto_skipped(self, optimizer: AutoOptimizer) -> None:
        plans = [OptimizationPlan(file_path="test.py", auto_applicable=False)]
        results = optimizer.apply_optimizations(plans)
        assert results == []

    def test_apply_optimizations_missing_file(self, optimizer: AutoOptimizer) -> None:
        plans = [OptimizationPlan(file_path="/nonexistent/file.py", auto_applicable=True)]
        results = optimizer.apply_optimizations(plans)
        assert len(results) == 1
        assert results[0].success is False

    def test_remove_unused_imports(self, optimizer_live: AutoOptimizer, file_with_unused_import: Path) -> None:
        plans = [OptimizationPlan(
            file_path=str(file_with_unused_import),
            target_issues=[{"message": "Unused import"}],
            auto_applicable=True,
        )]
        results = optimizer_live.apply_optimizations(plans)
        assert len(results) == 1
        assert results[0].success is True
        content = file_with_unused_import.read_text()
        assert "import json" not in content
        assert "import os" not in content

    def test_fix_whitespace(self, optimizer_live: AutoOptimizer, file_with_trailing_whitespace: Path) -> None:
        plans = [OptimizationPlan(
            file_path=str(file_with_trailing_whitespace),
            target_issues=[{"message": "Trailing whitespace"}],
            auto_applicable=True,
        )]
        results = optimizer_live.apply_optimizations(plans)
        assert len(results) == 1
        content = file_with_trailing_whitespace.read_text()
        for line in content.splitlines():
            assert line == line.rstrip()

    def test_optimize_test_suite(self, optimizer: AutoOptimizer) -> None:
        test_results = [
            {"name": "test_fast", "duration_ms": 50},
            {"name": "test_slow", "duration_ms": 8000},
            {"name": "test_medium", "duration_ms": 500},
        ]
        optimization = optimizer.optimize_test_suite(test_results)
        assert len(optimization["slow_tests"]) == 1
        assert optimization["slow_tests"][0]["name"] == "test_slow"
        assert "test_fast" in optimization["parallel_candidates"]

    def test_optimize_test_suite_reorder(self, optimizer: AutoOptimizer) -> None:
        test_results = [
            {"name": "test_a", "duration_ms": 100},
            {"name": "test_b", "duration_ms": 5000},
            {"name": "test_c", "duration_ms": 200},
        ]
        optimization = optimizer.optimize_test_suite(test_results)
        assert optimization["reorder_suggestions"][0] == "test_b"

    def test_get_optimization_summary(self, optimizer_live: AutoOptimizer, file_with_unused_import: Path) -> None:
        plans = [OptimizationPlan(
            file_path=str(file_with_unused_import),
            target_issues=[{"message": "Unused import"}],
            auto_applicable=True,
        )]
        optimizer_live.apply_optimizations(plans)
        summary = optimizer_live.get_optimization_summary()
        assert summary["files_optimized"] >= 1
        assert summary["optimizations_applied"] >= 1

    def test_get_optimization_summary_empty(self, optimizer: AutoOptimizer) -> None:
        summary = optimizer.get_optimization_summary()
        assert summary["files_optimized"] == 0
        assert summary["lines_saved"] == 0

    def test_add_docstring_placeholders(self, optimizer_live: AutoOptimizer, tmp_path: Path) -> None:
        f = tmp_path / "nodoc.py"
        f.write_text("def undocumented():\n    return 42\n")
        plans = [OptimizationPlan(
            file_path=str(f),
            target_issues=[{"message": "Missing docstring"}],
            auto_applicable=True,
        )]
        optimizer_live.apply_optimizations(plans)
        content = f.read_text()
        assert '"""' in content

    def test_applied_optimizations_property(self, optimizer: AutoOptimizer) -> None:
        assert optimizer.applied_optimizations == []
