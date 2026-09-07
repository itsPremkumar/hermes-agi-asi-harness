"""QualityChecker — code quality analysis.

Analyzes code for complexity, duplication, style, and structural quality issues.
"""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class QualityIssue:
    """A single quality issue."""

    file: str
    line: int
    severity: str
    message: str
    rule: str
    column: int = 0


@dataclass
class QualityReport:
    """Aggregated quality report."""

    issues: list[QualityIssue] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    overall_score: float | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


class QualityChecker:
    """Checks code quality across multiple dimensions.

    Analyzes complexity, duplication, naming, docstrings, type hints, and line length.
    """

    # Thresholds
    MAX_LINE_LENGTH = 120
    MAX_FUNCTION_LENGTH = 50
    MAX_CYCLOMATIC_COMPLEXITY = 10
    MAX_PARAMETERS = 7
    DUPLICATE_LINE_THRESHOLD = 4

    def check_files(self, files: dict[str, str]) -> QualityReport:
        """Check quality of multiple files.

        Args:
            files: Mapping of filename to source code.

        Returns:
            QualityReport with findings.
        """
        all_issues: list[QualityIssue] = []
        all_suggestions: list[str] = []
        total_metrics: dict[str, Any] = {
            "total_lines": 0,
            "total_functions": 0,
            "total_classes": 0,
            "files_checked": len(files),
        }

        for filename, source in files.items():
            if not filename.endswith(".py"):
                continue

            issues, suggestions, metrics = self._check_file(filename, source)
            all_issues.extend(issues)
            all_suggestions.extend(suggestions)
            total_metrics["total_lines"] += metrics.get("total_lines", 0)
            total_metrics["total_functions"] += metrics.get("total_functions", 0)
            total_metrics["total_classes"] += metrics.get("total_classes", 0)

        # Cross-file duplication check
        dup_issues = self._check_duplication(files)
        all_issues.extend(dup_issues)

        # Compute overall score
        score = self._compute_score(all_issues, total_metrics)

        return QualityReport(
            issues=all_issues,
            suggestions=all_suggestions,
            overall_score=score,
            metrics=total_metrics,
        )

    def _check_file(
        self, filename: str, source: str
    ) -> tuple[list[QualityIssue], list[str], dict[str, Any]]:
        """Check a single file's quality."""
        issues: list[QualityIssue] = []
        suggestions: list[str] = []
        metrics: dict[str, Any] = {
            "total_lines": 0,
            "total_functions": 0,
            "total_classes": 0,
        }

        lines = source.splitlines()
        metrics["total_lines"] = len(lines)

        # Line-by-line checks
        for i, line in enumerate(lines, 1):
            # Line length
            if len(line) > self.MAX_LINE_LENGTH:
                issues.append(
                    QualityIssue(
                        file=filename,
                        line=i,
                        severity="low",
                        message=f"Line too long ({len(line)} > {self.MAX_LINE_LENGTH} chars)",
                        rule="line-too-long",
                    )
                )

            # Trailing whitespace
            if line != line.rstrip():
                issues.append(
                    QualityIssue(
                        file=filename,
                        line=i,
                        severity="info",
                        message="Trailing whitespace",
                        rule="trailing-whitespace",
                    )
                )

            # TODO/FIXME comments
            if re.search(r"#\s*(TODO|FIXME|HACK|XXX)\b", line, re.IGNORECASE):
                issues.append(
                    QualityIssue(
                        file=filename,
                        line=i,
                        severity="info",
                        message="TODO/FIXME comment found",
                        rule="todo-comment",
                    )
                )

            # Bare except
            if re.search(r"^\s*except\s*:", line):
                issues.append(
                    QualityIssue(
                        file=filename,
                        line=i,
                        severity="medium",
                        message="Bare except clause — catches SystemExit and KeyboardInterrupt",
                        rule="bare-except",
                    )
                )

            # Use of eval()
            if re.search(r"\beval\s*\(", line) and not line.strip().startswith("#"):
                issues.append(
                    QualityIssue(
                        file=filename,
                        line=i,
                        severity="high",
                        message="Use of eval() — potential code injection",
                        rule="dangerous-eval",
                    )
                )

            # Use of exec()
            if re.search(r"\bexec\s*\(", line) and not line.strip().startswith("#"):
                issues.append(
                    QualityIssue(
                        file=filename,
                        line=i,
                        severity="high",
                        message="Use of exec() — potential code injection",
                        rule="dangerous-exec",
                    )
                )

        # AST-based checks
        try:
            tree = ast.parse(source)
            ast_issues, ast_suggestions, ast_metrics = self._check_ast(filename, tree, lines)
            issues.extend(ast_issues)
            suggestions.extend(ast_suggestions)
            metrics["total_functions"] = ast_metrics.get("functions", 0)
            metrics["total_classes"] = ast_metrics.get("classes", 0)
        except SyntaxError as e:
            issues.append(
                QualityIssue(
                    file=filename,
                    line=e.lineno or 1,
                    severity="critical",
                    message=f"Syntax error: {e.msg}",
                    rule="syntax-error",
                )
            )

        return issues, suggestions, metrics

    def _check_ast(
        self, filename: str, tree: ast.Module, source_lines: list[str]
    ) -> tuple[list[QualityIssue], list[str], dict[str, int]]:
        """AST-based quality checks."""
        issues: list[QualityIssue] = []
        suggestions: list[str] = []
        metrics: dict[str, int] = {"functions": 0, "classes": 0}

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                metrics["functions"] += 1

                # Function length
                func_lines = node.end_lineno - node.lineno if node.end_lineno else 0
                if func_lines > self.MAX_FUNCTION_LENGTH:
                    issues.append(
                        QualityIssue(
                            file=filename,
                            line=node.lineno,
                            severity="medium",
                            message=(
                                f"Function '{node.name}' too long "
                                f"({func_lines} > {self.MAX_FUNCTION_LENGTH} lines)"
                            ),
                            rule="function-too-long",
                        )
                    )

                # Parameter count
                param_count = len(node.args.args) + len(node.args.kwonlyargs)
                if node.args.vararg:
                    param_count += 1
                if node.args.kwarg:
                    param_count += 1
                if param_count > self.MAX_PARAMETERS:
                    issues.append(
                        QualityIssue(
                            file=filename,
                            line=node.lineno,
                            severity="medium",
                            message=(
                                f"Function '{node.name}' has too many parameters "
                                f"({param_count} > {self.MAX_PARAMETERS})"
                            ),
                            rule="too-many-parameters",
                        )
                    )

                # Missing docstring
                if not (node.body and isinstance(node.body[0], ast.Expr) and
                        isinstance(node.body[0].value, (ast.Constant, ast.Str))):
                    issues.append(
                        QualityIssue(
                            file=filename,
                            line=node.lineno,
                            severity="low",
                            message=f"Function '{node.name}' missing docstring",
                            rule="missing-docstring",
                        )
                    )

                # Cyclomatic complexity
                complexity = self._compute_complexity(node)
                if complexity > self.MAX_CYCLOMATIC_COMPLEXITY:
                    issues.append(
                        QualityIssue(
                            file=filename,
                            line=node.lineno,
                            severity="medium",
                            message=(
                                f"Function '{node.name}' cyclomatic complexity "
                                f"({complexity}) exceeds threshold "
                                f"({self.MAX_CYCLOMATIC_COMPLEXITY})"
                            ),
                            rule="high-complexity",
                        )
                    )

            elif isinstance(node, ast.ClassDef):
                metrics["classes"] += 1

                # Missing docstring
                if not (node.body and isinstance(node.body[0], ast.Expr) and
                        isinstance(node.body[0].value, (ast.Constant, ast.Str))):
                    issues.append(
                        QualityIssue(
                            file=filename,
                            line=node.lineno,
                            severity="low",
                            message=f"Class '{node.name}' missing docstring",
                            rule="missing-docstring",
                        )
                    )

        # Suggestions based on overall structure
        if metrics["functions"] == 0 and metrics["classes"] == 0:
            suggestions.append(f"{filename}: No functions or classes found — consider adding structure")

        return issues, suggestions, metrics

    def _compute_complexity(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        """Compute cyclomatic complexity of a function.

        Starts at 1 and increments for each decision point.
        """
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.With) and not isinstance(child, ast.AsyncWith):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def _check_duplication(self, files: dict[str, str]) -> list[QualityIssue]:
        """Check for duplicate code blocks across files."""
        issues: list[QualityIssue] = []

        # Build a map of line hashes to file locations
        line_map: dict[tuple[str, ...], list[tuple[str, int]]] = {}

        for filename, source in files.items():
            if not filename.endswith(".py"):
                continue
            lines = source.splitlines()
            for i in range(len(lines) - self.DUPLICATE_LINE_THRESHOLD + 1):
                block = tuple(
                    lines[i + j].strip()
                    for j in range(self.DUPLICATE_LINE_THRESHOLD)
                    if lines[i + j].strip() and not lines[i + j].strip().startswith("#")
                )
                if len(block) >= self.DUPLICATE_LINE_THRESHOLD:
                    line_map.setdefault(block, []).append((filename, i + 1))

        # Check for duplicates across different files
        for block, locations in line_map.items():
            unique_files = {loc[0] for loc in locations}
            if len(unique_files) >= 2:
                for filename, line in locations:
                    issues.append(
                        QualityIssue(
                            file=filename,
                            line=line,
                            severity="medium",
                            message=(
                                f"Duplicate code block found in {len(unique_files)} files"
                            ),
                            rule="duplicate-code",
                        )
                    )

        return issues

    def _compute_score(self, issues: list[QualityIssue], metrics: dict[str, Any]) -> float:
        """Compute quality score (0-100) from issues."""
        score = 100.0
        severity_weights = {"info": 0.5, "low": 1.0, "medium": 3.0, "high": 7.0, "critical": 20.0}

        for issue in issues:
            weight = severity_weights.get(issue.severity, 2.0)
            score -= weight

        # Normalize based on lines of code
        total_lines = metrics.get("total_lines", 1)
        if total_lines > 0:
            # Per-100-lines density bonus
            issue_density = len(issues) / max(total_lines / 100, 1)
            score -= issue_density * 0.5

        return max(0.0, min(100.0, score))
