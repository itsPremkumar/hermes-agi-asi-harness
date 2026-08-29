"""Static analysis engine for test gap detection."""
from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Iterable

from testpilot.models import GapSeverity, TestGap


class StaticAnalyzer:
    """Analyzes Python source code to detect untested functions and branches."""

    def __init__(self, root_dir: str, exclude_patterns: list[str] | None = None) -> None:
        self.root_dir = Path(root_dir)
        self.exclude_patterns = exclude_patterns or [
            "*/tests/*",
            "*/test/*",
            "*/__pycache__/*",
            "*/.venv/*",
            "*/venv/*",
        ]

    def analyze(self) -> list[TestGap]:
        """Run full static analysis and return detected gaps."""
        gaps: list[TestGap] = []
        for py_file in self._iter_python_files():
            gaps.extend(self._analyze_file(py_file))
        return gaps

    def _iter_python_files(self) -> Iterable[Path]:
        """Yield Python files under root_dir, respecting exclude patterns."""
        for path in self.root_dir.rglob("*.py"):
            if self._is_excluded(path):
                continue
            yield path

    def _is_excluded(self, path: Path) -> bool:
        """Check if a path matches any exclude pattern."""
        rel = str(path.relative_to(self.root_dir))
        for pattern in self.exclude_patterns:
            if self._match_pattern(rel, pattern):
                return True
        return False

    @staticmethod
    def _match_pattern(rel_path: str, pattern: str) -> bool:
        """Simple glob-like pattern matching."""
        import fnmatch
        # Normalize path separators for cross-platform matching
        normalized = rel_path.replace("\\", "/")
        # Try exact match, then parent-match (for patterns like */tests/* which
        # won't match top-level dirs like tests/foo.py)
        if fnmatch.fnmatch(normalized, pattern):
            return True
        # Also match if the path starts with the pattern's suffix after */
        # e.g. "tests/*" pattern matches "tests/foo.py"
        if pattern.startswith("*/"):
            suffix = pattern[2:]
            if fnmatch.fnmatch(normalized, suffix):
                return True
        return False

    def _analyze_file(self, file_path: Path) -> list[TestGap]:
        """Analyze a single Python file for test gaps."""
        gaps: list[TestGap] = []
        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError):
            return gaps

        rel_path = str(file_path.relative_to(self.root_dir))
        defined_funcs: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_") and not node.name.startswith("__"):
                    continue
                if node.name.startswith("__") and node.name.endswith("__"):
                    continue
                defined_funcs.add(node.name)
                gap = self._check_function(node, rel_path)
                if gap:
                    gaps.append(gap)

        return gaps

    def _check_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: str
    ) -> TestGap | None:
        """Check a function for test gap indicators."""
        # Functions with complex logic (branches, loops, try/except) are higher severity
        complexity = self._compute_complexity(node)
        has_error_handling = self._has_error_handling(node)
        has_external_calls = self._has_external_calls(node)

        if complexity < 2 and not has_error_handling and not has_external_calls:
            return None

        severity = GapSeverity.LOW
        if complexity >= 5 or has_error_handling:
            severity = GapSeverity.HIGH
        elif complexity >= 3 or has_external_calls:
            severity = GapSeverity.MEDIUM

        reason_parts: list[str] = []
        if complexity >= 3:
            reason_parts.append(f"cyclomatic complexity {complexity}")
        if has_error_handling:
            reason_parts.append("error handling present")
        if has_external_calls:
            reason_parts.append("external I/O calls detected")

        return TestGap(
            file_path=file_path,
            function_name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            severity=severity,
            reason=f"Untested function with {'; '.join(reason_parts)}",
            suggested_test_name=f"test_{node.name}",
        )

    @staticmethod
    def _compute_complexity(node: ast.AST) -> int:
        """Compute a simple cyclomatic complexity estimate."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(
                child,
                (
                    ast.If,
                    ast.For,
                    ast.While,
                    ast.ExceptHandler,
                    ast.With,
                    ast.Assert,
                ),
            ):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    @staticmethod
    def _has_error_handling(node: ast.AST) -> bool:
        """Check if the node contains try/except blocks."""
        for child in ast.walk(node):
            if isinstance(child, ast.Try):
                return True
        return False

    @staticmethod
    def _has_external_calls(node: ast.AST) -> bool:
        """Check if the node makes external I/O calls (requests, db, file)."""
        external_modules = {"requests", "httpx", "urllib", "aiohttp", "sqlite3", "os", "shutil"}
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func = child.func
                if isinstance(func, ast.Attribute):
                    if isinstance(func.value, ast.Name) and func.value.id in external_modules:
                        return True
                elif isinstance(func, ast.Name) and func.id in {
                    "open", "print", "input", "exec", "eval"
                }:
                    return True
        return False


def analyze_directory(
    root_dir: str, exclude_patterns: list[str] | None = None
) -> list[TestGap]:
    """Convenience function to analyze a directory."""
    analyzer = StaticAnalyzer(root_dir, exclude_patterns)
    return analyzer.analyze()
