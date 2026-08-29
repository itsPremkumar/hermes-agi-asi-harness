"""Test coverage impact analysis."""

from __future__ import annotations

import re
from typing import Any

from .models import Issue, Severity


class CoverageAnalyzer:
    """Analyzes test coverage impact of a pull request."""

    def __init__(self, coverage_threshold: float = 80.0):
        self.coverage_threshold = coverage_threshold

    def analyze_diff(self, diff: str, existing_coverage: float | None = None) -> dict[str, Any]:
        """Analyze the coverage impact of a diff."""
        added_lines = 0
        removed_lines = 0
        modified_files: list[str] = []
        test_files: list[str] = []
        source_files: list[str] = []

        current_file = ""
        for line in diff.split("\n"):
            if line.startswith("+++ b/"):
                current_file = line[6:]
                modified_files.append(current_file)
                if self._is_test_file(current_file):
                    test_files.append(current_file)
                else:
                    source_files.append(current_file)
            elif line.startswith("+") and not line.startswith("+++"):
                added_lines += 1
            elif line.startswith("-") and not line.startswith("---"):
                removed_lines += 1

        # Calculate coverage impact
        coverage_impact = self._estimate_coverage_impact(
            added_lines, removed_lines, len(test_files), len(source_files)
        )

        notes = []
        if source_files and not test_files:
            notes.append("Source files modified without corresponding test changes")
        if added_lines > 100 and not test_files:
            notes.append(f"Large addition ({added_lines} lines) without test coverage")

        return {
            "added_lines": added_lines,
            "removed_lines": removed_lines,
            "modified_files": modified_files,
            "test_files": test_files,
            "source_files": source_files,
            "coverage_impact": coverage_impact,
            "notes": notes,
        }

    def _is_test_file(self, path: str) -> bool:
        """Check if a file path is a test file."""
        test_patterns = [
            r"test_.*\.py$",
            r".*_test\.py$",
            r".*\.test\.(js|ts|jsx|tsx)$",
            r".*\.spec\.(js|ts|jsx|tsx)$",
            r"tests?/",
            r"__tests__/",
        ]
        return any(re.search(p, path) for p in test_patterns)

    def _estimate_coverage_impact(
        self,
        added_lines: int,
        removed_lines: int,
        test_file_count: int,
        source_file_count: int,
    ) -> float:
        """Estimate the impact on test coverage (percentage change)."""
        if source_file_count == 0:
            return 0.0

        # Rough estimate: each test file covers ~50 lines of source
        test_coverage_added = test_file_count * 50
        net_change = test_coverage_added - added_lines

        # Convert to percentage impact (assuming ~1000 lines of source)
        impact = net_change / 1000 * 100
        return round(impact, 2)

    def check_coverage_regression(
        self,
        diff: str,
        baseline_coverage: float,
    ) -> list[Issue]:
        """Check if the PR might cause coverage regression."""
        issues = []
        analysis = self.analyze_diff(diff)

        projected_coverage = baseline_coverage + analysis["coverage_impact"]

        if projected_coverage < self.coverage_threshold:
            issues.append(Issue(
                file="",
                line=0,
                severity=Severity.WARNING,
                message=(
                    f"Projected coverage ({projected_coverage:.1f}%) is below "
                    f"threshold ({self.coverage_threshold:.1f}%)"
                ),
                rule_id="COV001",
                source="coverage",
                suggestion="Add tests for new code or increase test coverage",
            ))

        return issues
