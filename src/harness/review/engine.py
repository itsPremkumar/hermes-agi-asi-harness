"""ReviewEngine — main review orchestrator.

Orchestrates all review sub-systems (quality, security, conventions) to produce
a unified ReviewResult with findings, scores, and recommendations.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .autofix import AutoFixer, FixResult
from .convention import ConventionEnforcer, ConventionViolation
from .quality import QualityChecker, QualityIssue, QualityReport
from .reporter import ReviewReporter
from .security import SecurityReport, SecurityScanner, Vulnerability

logger = logging.getLogger(__name__)


class ReviewSeverity(str, Enum):
    """Severity levels for review findings."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ReviewResult:
    """Aggregated review result."""

    passed: bool
    score: float  # 0.0 to 100.0
    issues: list[dict[str, Any]] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    quality_report: QualityReport | None = None
    security_report: SecurityReport | None = None
    convention_violations: list[ConventionViolation] = field(default_factory=list)
    fixed_code: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "passed": self.passed,
            "score": round(self.score, 2),
            "issue_count": len(self.issues),
            "suggestion_count": len(self.suggestions),
            "issues": self.issues,
            "suggestions": self.suggestions,
            "quality_score": self.quality_report.overall_score if self.quality_report else None,
            "security_score": self.security_report.overall_score if self.security_report else None,
            "convention_violations": len(self.convention_violations),
            "fixed_files": list(self.fixed_code.keys()),
            "metadata": self.metadata,
        }


class ReviewEngine:
    """Main code review orchestrator.

    Coordinates QualityChecker, SecurityScanner, ConventionEnforcer, and AutoFixer
    to review code changes against harness standards.
    """

    # Default minimum score to pass review
    DEFAULT_PASS_THRESHOLD = 70.0

    # Severity weights for scoring
    SEVERITY_WEIGHTS = {
        ReviewSeverity.INFO: 1,
        ReviewSeverity.LOW: 3,
        ReviewSeverity.MEDIUM: 5,
        ReviewSeverity.HIGH: 10,
        ReviewSeverity.CRITICAL: 25,
    }

    def __init__(
        self,
        quality_checker: QualityChecker | None = None,
        security_scanner: SecurityScanner | None = None,
        convention_enforcer: ConventionEnforcer | None = None,
        autofixer: AutoFixer | None = None,
        reporter: ReviewReporter | None = None,
        pass_threshold: float = DEFAULT_PASS_THRESHOLD,
    ) -> None:
        self.quality_checker = quality_checker or QualityChecker()
        self.security_scanner = security_scanner or SecurityScanner()
        self.convention_enforcer = convention_enforcer or ConventionEnforcer()
        self.autofixer = autofixer or AutoFixer()
        self.reporter = reporter or ReviewReporter()
        self.pass_threshold = pass_threshold

    def review_files(
        self,
        files: dict[str, str],
        auto_fix: bool = False,
        conventions: list[str] | None = None,
    ) -> ReviewResult:
        """Review a set of files.

        Args:
            files: Mapping of filename to source code content.
            auto_fix: Whether to attempt automatic fixes.
            conventions: Optional list of convention rule names to enforce.

        Returns:
            Aggregated ReviewResult.
        """
        start_time = time.monotonic()
        all_issues: list[dict[str, Any]] = []
        all_suggestions: list[str] = []

        # Run quality checks
        quality_report = self.quality_checker.check_files(files)
        for issue in quality_report.issues:
            all_issues.append(
                {
                    "file": issue.file,
                    "line": issue.line,
                    "severity": issue.severity,
                    "category": "quality",
                    "message": issue.message,
                    "rule": issue.rule,
                }
            )
        all_suggestions.extend(quality_report.suggestions)

        # Run security scan
        security_report = self.security_scanner.scan_files(files)
        for vuln in security_report.vulnerabilities:
            all_issues.append(
                {
                    "file": vuln.file,
                    "line": vuln.line,
                    "severity": vuln.severity,
                    "category": "security",
                    "message": vuln.message,
                    "rule": vuln.cwe_id,
                }
            )
        all_suggestions.extend(security_report.suggestions)

        # Run convention enforcement
        convention_violations = self.convention_enforcer.check_files(files, conventions)
        for violation in convention_violations:
            all_issues.append(
                {
                    "file": violation.file,
                    "line": violation.line,
                    "severity": violation.severity,
                    "category": "convention",
                    "message": violation.message,
                    "rule": violation.rule,
                }
            )

        # Compute score
        score = self._compute_score(all_issues, quality_report, security_report)

        # Auto-fix if requested
        fixed_code: dict[str, str] = {}
        if auto_fix:
            fix_result = self.autofixer.fix_files(files, all_issues)
            fixed_code = fix_result.fixed_files
            all_suggestions.extend(fix_result.suggestions)

        passed = score >= self.pass_threshold

        elapsed = time.monotonic() - start_time
        metadata = {
            "files_reviewed": len(files),
            "elapsed_seconds": round(elapsed, 3),
            "auto_fix_applied": auto_fix,
            "pass_threshold": self.pass_threshold,
        }

        return ReviewResult(
            passed=passed,
            score=score,
            issues=all_issues,
            suggestions=all_suggestions,
            quality_report=quality_report,
            security_report=security_report,
            convention_violations=convention_violations,
            fixed_code=fixed_code,
            metadata=metadata,
        )

    def review_diff(self, diff_text: str, auto_fix: bool = False) -> ReviewResult:
        """Review a unified diff.

        Parses the diff into per-file content and delegates to review_files.
        """
        files = self._parse_diff(diff_text)
        if not files:
            return ReviewResult(
                passed=False,
                score=0.0,
                issues=[
                    {
                        "severity": ReviewSeverity.HIGH.value,
                        "category": "engine",
                        "message": "No parseable file changes in diff",
                    }
                ],
            )
        return self.review_files(files, auto_fix=auto_fix)

    def generate_report(self, result: ReviewResult, format: str = "markdown") -> str:
        """Generate a formatted report from a review result."""
        return self.reporter.generate(result, format=format)

    def _compute_score(
        self,
        issues: list[dict[str, Any]],
        quality_report: QualityReport,
        security_report: SecurityReport,
    ) -> float:
        """Compute overall score from 0 to 100.

        Starts at 100 and deducts weighted points for each issue.
        """
        score = 100.0

        for issue in issues:
            severity_str = issue.get("severity", ReviewSeverity.MEDIUM.value)
            try:
                severity = ReviewSeverity(severity_str)
            except ValueError:
                severity = ReviewSeverity.MEDIUM
            score -= self.SEVERITY_WEIGHTS.get(severity, 5)

        # Blend with quality and security sub-scores
        if quality_report.overall_score is not None:
            score = score * 0.7 + quality_report.overall_score * 0.15
        if security_report.overall_score is not None:
            score = score * 0.85 + security_report.overall_score * 0.15

        return max(0.0, min(100.0, score))

    @staticmethod
    def _parse_diff(diff_text: str) -> dict[str, str]:
        """Parse a unified diff into a mapping of filename -> new content."""
        files: dict[str, str] = {}
        current_file: str | None = None
        current_lines: list[str] = []
        old_lines: list[str] = []

        for line in diff_text.splitlines():
            if line.startswith("diff --git"):
                # Save previous file
                if current_file and current_lines:
                    files[current_file] = "\n".join(current_lines)
                # Extract new filename from "diff --git a/path b/path"
                parts = line.split(" ")
                if len(parts) >= 4:
                    current_file = parts[3].lstrip("b/")
                else:
                    current_file = None
                current_lines = []
                old_lines = []
            elif line.startswith("--- ") or line.startswith("+++ "):
                continue
            elif line.startswith("@@"):
                # hunk header
                continue
            elif line.startswith("-"):
                old_lines.append(line[1:])
            elif line.startswith("+"):
                current_lines.append(line[1:])
            elif current_file is not None:
                # Context line — appears in both old and new
                current_lines.append(line)

        # Save last file
        if current_file and current_lines:
            files[current_file] = "\n".join(current_lines)

        return files
