"""ReviewReporter — generate structured review reports.

Produces formatted reports from ReviewResult objects in multiple formats.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .engine import ReviewResult, ReviewSeverity

logger = logging.getLogger(__name__)


class ReviewReporter:
    """Generates structured reports from review results.

    Supports markdown, JSON, and plain text output formats.
    """

    def generate(self, result: ReviewResult, format: str = "markdown") -> str:  # noqa: F821
        """Generate a formatted report.

        Args:
            result: The review result to report on.
            format: Output format — 'markdown', 'json', or 'text'.

        Returns:
            Formatted report string.
        """
        if format == "markdown":
            return self._generate_markdown(result)
        elif format == "json":
            return self._generate_json(result)
        elif format == "text":
            return self._generate_text(result)
        else:
            raise ValueError(f"Unknown format: {format}")

    def _generate_markdown(self, result: ReviewResult) -> str:
        """Generate a markdown report."""
        lines: list[str] = []

        # Header
        status = "PASSED" if result.passed else "FAILED"
        lines.append(f"# Code Review Report")
        lines.append("")
        lines.append(f"**Status:** {status}")
        lines.append(f"**Score:** {result.score:.1f}/100")
        lines.append(f"**Issues:** {len(result.issues)}")
        lines.append(f"**Suggestions:** {len(result.suggestions)}")
        lines.append("")

        # Summary
        if result.issues:
            lines.append("## Issues")
            lines.append("")
            lines.append("| File | Line | Severity | Category | Rule | Message |")
            lines.append("|------|------|----------|----------|------|---------|")

            for issue in result.issues:
                file = issue.get("file", "-")
                line = issue.get("line", "-")
                severity = issue.get("severity", "-")
                category = issue.get("category", "-")
                rule = issue.get("rule", "-")
                message = issue.get("message", "-")
                lines.append(f"| {file} | {line} | {severity} | {category} | {rule} | {message} |")

            lines.append("")

        # Suggestions
        if result.suggestions:
            lines.append("## Suggestions")
            lines.append("")
            for suggestion in result.suggestions:
                lines.append(f"- {suggestion}")
            lines.append("")

        # Quality report
        if result.quality_report:
            qr = result.quality_report
            lines.append("## Quality Report")
            lines.append("")
            if qr.overall_score is not None:
                lines.append(f"**Quality Score:** {qr.overall_score:.1f}/100")
            if qr.metrics:
                lines.append("")
                lines.append("**Metrics:**")
                for key, value in qr.metrics.items():
                    lines.append(f"- {key}: {value}")
            lines.append("")

        # Security report
        if result.security_report:
            sr = result.security_report
            lines.append("## Security Report")
            lines.append("")
            if sr.overall_score is not None:
                lines.append(f"**Security Score:** {sr.overall_score:.1f}/100")
            if sr.vulnerabilities:
                lines.append("")
                lines.append(f"**Vulnerabilities:** {len(sr.vulnerabilities)}")
            lines.append("")

        # Convention violations
        if result.convention_violations:
            lines.append("## Convention Violations")
            lines.append("")
            for v in result.convention_violations:
                lines.append(f"- **{v.file}:{v.line}** [{v.rule}] {v.message}")
            lines.append("")

        # Fixed files
        if result.fixed_code:
            lines.append("## Auto-Fixed Files")
            lines.append("")
            for filename in result.fixed_code:
                lines.append(f"- {filename}")
            lines.append("")

        # Metadata
        if result.metadata:
            lines.append("## Metadata")
            lines.append("")
            for key, value in result.metadata.items():
                lines.append(f"- {key}: {value}")
            lines.append("")

        return "\n".join(lines)

    def _generate_json(self, result: ReviewResult) -> str:
        """Generate a JSON report."""
        return json.dumps(result.to_dict(), indent=2, default=str)

    def _generate_text(self, result: ReviewResult) -> str:
        """Generate a plain text report."""
        lines: list[str] = []

        status = "PASSED" if result.passed else "FAILED"
        lines.append("=" * 60)
        lines.append("CODE REVIEW REPORT")
        lines.append("=" * 60)
        lines.append(f"Status:     {status}")
        lines.append(f"Score:      {result.score:.1f}/100")
        lines.append(f"Issues:     {len(result.issues)}")
        lines.append(f"Suggestions: {len(result.suggestions)}")
        lines.append("")

        if result.issues:
            lines.append("-" * 60)
            lines.append("ISSUES")
            lines.append("-" * 60)
            for issue in result.issues:
                file = issue.get("file", "-")
                line = issue.get("line", "-")
                severity = issue.get("severity", "-")
                message = issue.get("message", "-")
                lines.append(f"  [{severity.upper()}] {file}:{line}  {message}")
            lines.append("")

        if result.suggestions:
            lines.append("-" * 60)
            lines.append("SUGGESTIONS")
            lines.append("-" * 60)
            for suggestion in result.suggestions:
                lines.append(f"  - {suggestion}")
            lines.append("")

        if result.quality_report and result.quality_report.overall_score is not None:
            lines.append(f"Quality Score: {result.quality_report.overall_score:.1f}/100")

        if result.security_report and result.security_report.overall_score is not None:
            lines.append(f"Security Score: {result.security_report.overall_score:.1f}/100")

        lines.append("=" * 60)

        return "\n".join(lines)
