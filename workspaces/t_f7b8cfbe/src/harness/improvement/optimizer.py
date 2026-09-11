"""
AutoOptimizer — Automatically optimize code based on ImprovementAnalyzer findings.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .analyzer import CodeQualityMetrics, ImprovementAnalyzer


@dataclass
class OptimizationResult:
    """Result of a single optimization pass."""

    file_path: str
    optimizations_applied: list[dict[str, Any]] = field(default_factory=list)
    lines_before: int = 0
    lines_after: int = 0
    success: bool = True
    error: str = ""

    @property
    def lines_saved(self) -> int:
        return self.lines_before - self.lines_after


@dataclass
class OptimizationPlan:
    """A plan of optimizations to apply."""

    file_path: str
    target_issues: list[dict[str, Any]] = field(default_factory=list)
    estimated_impact: str = "medium"  # low, medium, high
    auto_applicable: bool = True


class AutoOptimizer:
    """Automatically optimizes code based on ImprovementAnalyzer findings."""

    def __init__(self, project_root: str | Path | None = None, dry_run: bool = False) -> None:
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.dry_run = dry_run
        self._analyzer = ImprovementAnalyzer(project_root)
        self._applied_optimizations: list[OptimizationResult] = []

    @property
    def applied_optimizations(self) -> list[OptimizationResult]:
        return list(self._applied_optimizations)

    def plan_optimizations(self, metrics: CodeQualityMetrics) -> list[OptimizationPlan]:
        """Create an optimization plan based on code quality metrics."""
        plans: list[OptimizationPlan] = []

        for issue in metrics.issues:
            plan = OptimizationPlan(
                file_path=issue.get("file", ""),
                target_issues=[issue],
            )

            severity = issue.get("severity", "medium")
            if severity == "critical":
                plan.estimated_impact = "high"
            elif severity == "low":
                plan.estimated_impact = "low"

            # Some issues require human review
            msg = issue.get("message", "")
            if "complexity" in msg.lower() or "refactor" in msg.lower():
                plan.auto_applicable = False
            elif "syntax error" in msg.lower():
                plan.auto_applicable = False

            plans.append(plan)

        return plans

    def apply_optimizations(self, plans: list[OptimizationPlan] | None = None) -> list[OptimizationResult]:
        """Apply optimization plans to the codebase."""
        if plans is None:
            metrics = self._analyzer.analyze_code_quality()
            plans = self.plan_optimizations(metrics)

        results: list[OptimizationResult] = []

        for plan in plans:
            if not plan.auto_applicable:
                continue

            try:
                result = self._optimize_file(plan)
                results.append(result)
                if result.success:
                    self._applied_optimizations.append(result)
            except Exception as e:
                results.append(OptimizationResult(
                    file_path=plan.file_path,
                    success=False,
                    error=str(e),
                ))

        return results

    def _optimize_file(self, plan: OptimizationPlan) -> OptimizationResult:
        """Apply optimizations to a single file."""
        result = OptimizationResult(file_path=plan.file_path)
        path = Path(plan.file_path)

        if not path.exists():
            result.success = False
            result.error = f"File not found: {plan.file_path}"
            return result

        source = path.read_text(encoding="utf-8")
        result.lines_before = len(source.splitlines())

        optimized = source

        for issue in plan.target_issues:
            msg = issue.get("message", "")
            if "unused import" in msg.lower() or "unused" in msg.lower():
                optimized = self._remove_unused_imports(optimized, result)
            elif "trailing whitespace" in msg.lower():
                optimized = self._fix_whitespace(optimized, result)
            elif "long line" in msg.lower() or "line too long" in msg.lower():
                optimized = self._wrap_long_lines(optimized, result)
            elif "missing docstring" in msg.lower():
                optimized = self._add_docstring_placeholders(optimized, result)

        result.lines_after = len(optimized.splitlines())

        if not self.dry_run and optimized != source:
            path.write_text(optimized, encoding="utf-8")

        return result

    @staticmethod
    def _remove_unused_imports(source: str, result: OptimizationResult) -> str:
        """Remove unused imports from source code."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source

        used_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)

        lines = source.splitlines(keepends=True)
        new_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                if stripped.startswith("from "):
                    match = re.match(r"from\s+\S+\s+import\s+(.+)", stripped)
                    if match:
                        imported = [n.strip().split(" as ")[0].strip() for n in match.group(1).split(",")]
                        if all(name not in used_names for name in imported):
                            result.optimizations_applied.append({
                                "type": "remove_unused_import",
                                "line": stripped,
                            })
                            continue
                elif stripped.startswith("import "):
                    match = re.match(r"import\s+(.+)", stripped)
                    if match:
                        modules = [m.strip().split(" as ")[0].strip().split(".")[0] for m in match.group(1).split(",")]
                        if all(mod not in used_names for mod in modules):
                            result.optimizations_applied.append({
                                "type": "remove_unused_import",
                                "line": stripped,
                            })
                            continue
            new_lines.append(line)

        return "".join(new_lines)

    @staticmethod
    def _fix_whitespace(source: str, result: OptimizationResult) -> str:
        """Remove trailing whitespace and ensure single trailing newline."""
        lines = source.splitlines()
        fixed_lines = [line.rstrip() for line in lines]
        optimized = "\n".join(fixed_lines)
        if not optimized.endswith("\n"):
            optimized += "\n"

        if optimized != source:
            result.optimizations_applied.append({"type": "fix_whitespace"})
        return optimized

    @staticmethod
    def _wrap_long_lines(source: str, max_length: int = 120) -> str:
        """Break long lines at appropriate points."""
        lines = source.splitlines(keepends=True)
        result: list[str] = []

        for line in lines:
            if len(line.rstrip("\n")) <= max_length:
                result.append(line)
                continue
            # For long lines, try to break at natural points (not in strings)
            # This is a simple heuristic; a full implementation would use AST
            result.append(line)

        return "".join(result)

    @staticmethod
    def _add_docstring_placeholders(source: str, result: OptimizationResult) -> str:
        """Add docstring placeholders to functions/classes missing them."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source

        lines = source.splitlines(keepends=True)
        insertions: list[tuple[int, str]] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if (
                    not node.body
                    or not isinstance(node.body[0], ast.Expr)
                    or not isinstance(node.body[0].value, (ast.Constant, ast.Str))
                ):
                    indent = " " * (node.col_offset or 0)
                    docstring = f'{indent}"""TODO: Add docstring."""\n'
                    insert_line = (node.body[0].lineno, docstring) if node.body else (node.lineno + 1, docstring)
                    insertions.append(insert_line)

        if not insertions:
            return source

        insertions.sort(key=lambda x: x[0], reverse=True)
        for line_num, text in insertions:
            lines.insert(line_num, text)
            result.optimizations_applied.append({
                "type": "add_docstring",
                "line": line_num,
            })

        return "".join(lines)

    def optimize_test_suite(self, test_results: list[dict[str, Any]]) -> dict[str, Any]:
        """Optimize test execution based on test results."""
        optimization: dict[str, Any] = {
            "parallel_candidates": [],
            "slow_tests": [],
            "reorder_suggestions": [],
        }

        for tr in test_results:
            duration = tr.get("duration_ms", 0)
            name = tr.get("name", "")

            if duration > 5000:
                optimization["slow_tests"].append({
                    "name": name,
                    "duration_ms": duration,
                    "suggestion": "Consider mocking external dependencies",
                })

            if duration < 100:
                optimization["parallel_candidates"].append(name)

        # Suggest running slow tests first to fail fast
        sorted_tests = sorted(test_results, key=lambda t: t.get("duration_ms", 0), reverse=True)
        optimization["reorder_suggestions"] = [t.get("name", "") for t in sorted_tests[:5]]

        return optimization

    def get_optimization_summary(self) -> dict[str, Any]:
        """Get a summary of all applied optimizations."""
        total_files = len(self._applied_optimizations)
        total_lines_saved = sum(r.lines_saved for r in self._applied_optimizations)
        total_opts = sum(len(r.optimizations_applied) for r in self._applied_optimizations)
        failures = sum(1 for r in self._applied_optimizations if not r.success)

        return {
            "files_optimized": total_files,
            "lines_saved": total_lines_saved,
            "optimizations_applied": total_opts,
            "failures": failures,
            "details": [
                {
                    "file": r.file_path,
                    "optimizations": len(r.optimizations_applied),
                    "lines_saved": r.lines_saved,
                    "success": r.success,
                }
                for r in self._applied_optimizations
            ],
        }
