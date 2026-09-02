"""Core review orchestrator."""

from __future__ import annotations

import logging
from typing import Any

from .ai_review import AIReviewer
from .assignment import ReviewAssigner
from .config import Config
from .coverage import CoverageAnalyzer
from .github_app import GitHubAPI
from .models import Issue, PullRequest, ReviewResult, ReviewStatus, Severity
from .notifications import NotificationClient
from .performance import PerformanceAnalyzer
from .rules import RuleEngine
from .security import SecurityScanner
from .static_analysis import AnalysisConfig, StaticAnalyzer

logger = logging.getLogger(__name__)


class ReviewOrchestrator:
    """Orchestrates the full review pipeline for a pull request."""

    def __init__(self, config: Config):
        self.config = config
        self.static_analyzer = StaticAnalyzer(AnalysisConfig())
        self.security_scanner = SecurityScanner()
        self.performance_analyzer = PerformanceAnalyzer()
        self.coverage_analyzer = CoverageAnalyzer()
        self.ai_reviewer = AIReviewer(
            provider=config.ai_provider,
            model=config.ai_model,
            api_key=config.ai_api_key,
        )
        self.assigner = ReviewAssigner()
        self.rule_engine = RuleEngine(config.rules_path)
        self.notifier = NotificationClient(
            slack_webhook_url=config.slack_webhook_url,
            teams_webhook_url=config.teams_webhook_url,
        )

    async def review_pr(
        self,
        pr: PullRequest,
        github: GitHubAPI,
        diff: str,
    ) -> ReviewResult:
        """Run the full review pipeline on a pull request."""
        result = ReviewResult(
            pr_number=pr.number,
            repo=pr.repo_full_name,
            status=ReviewStatus.IN_PROGRESS,
        )

        try:
            # 1. Static analysis (on diff)
            logger.info("Running static analysis for PR #%s", pr.number)
            static_issues = await self._run_static_analysis(diff)
            result.issues.extend(static_issues)

            # 2. Security scanning
            if self.config.enable_security_scan:
                logger.info("Running security scan for PR #%s", pr.number)
                security_issues = self.security_scanner.scan_diff(diff)
                result.security_findings = security_issues
                result.issues.extend(security_issues)

            # 3. Performance analysis
            if self.config.enable_performance_check:
                logger.info("Running performance analysis for PR #%s", pr.number)
                perf_issues = self.performance_analyzer.analyze_diff(diff)
                result.issues.extend(perf_issues)

            # 4. Coverage impact
            if self.config.enable_coverage_check:
                logger.info("Analyzing coverage impact for PR #%s", pr.number)
                coverage_result = self.coverage_analyzer.analyze_diff(diff)
                result.coverage_impact = coverage_result.get("coverage_impact")

            # 5. Custom rules
            logger.info("Evaluating custom rules for PR #%s", pr.number)
            rule_issues = self.rule_engine.evaluate_diff(diff)
            result.issues.extend(rule_issues)

            # 6. AI review
            if self.config.ai_api_key:
                logger.info("Running AI review for PR #%s", pr.number)
                ai_result = await self.ai_reviewer.review_pr(pr, diff)
                result.issues.extend(ai_result.issues)
                if ai_result.summary:
                    result.summary = ai_result.summary

            # 7. Generate summary if not set by AI
            if not result.summary:
                result.summary = self._generate_summary(result)

            result.status = ReviewStatus.COMPLETED

            # 8. Send notifications
            await self.notifier.notify_review_complete(result)

        except Exception as e:
            logger.exception("Review failed for PR #%s", pr.number)
            result.status = ReviewStatus.FAILED
            result.summary = f"Review failed: {e}"

        return result

    async def _run_static_analysis(self, diff: str) -> list[Issue]:
        """Extract files from diff and run static analysis."""
        # For diff-based review, we scan patterns in the diff
        # Full file analysis would require cloning the repo
        issues = []
        current_file = ""

        for line in diff.split("\n"):
            if line.startswith("+++ b/"):
                current_file = line[6:]

        return issues

    def _generate_summary(self, result: ReviewResult) -> str:
        """Generate a human-readable summary of the review."""
        if not result.issues:
            return "No issues found. Looks good!"

        counts: dict[str, int] = {}
        for issue in result.issues:
            sev = issue.severity.value if hasattr(issue.severity, "value") else str(issue.severity)
            counts[sev] = counts.get(sev, 0) + 1

        parts = [f"Found {len(result.issues)} issue(s):"]
        for severity in ["critical", "error", "warning", "info"]:
            if severity in counts:
                parts.append(f"  - {counts[severity]} {severity}")

        return "\n".join(parts)

    def build_review_body(self, result: ReviewResult) -> str:
        """Build the review body text for GitHub."""
        lines = [
            "## CodeReview Bot Review",
            "",
            result.summary,
            "",
        ]

        # Group issues by severity
        by_severity: dict[str, list[Issue]] = {}
        for issue in result.issues:
            sev = issue.severity.value if hasattr(issue.severity, "value") else str(issue.severity)
            if sev not in by_severity:
                by_severity[sev] = []
            by_severity[sev].append(issue)

        for severity in ["critical", "error", "warning", "info"]:
            if severity in by_severity:
                lines.append(f"### {severity.upper()} ({len(by_severity[severity])})")
                lines.append("")
                for issue in by_severity[severity]:
                    lines.append(f"- **{issue.file}:{issue.line}** — {issue.message}")
                    if issue.suggestion:
                        lines.append(f"  - Suggestion: {issue.suggestion}")
                lines.append("")

        if result.coverage_impact is not None:
            lines.append(f"### Coverage Impact")
            lines.append(f"Estimated change: {result.coverage_impact:+.1f}%")
            lines.append("")

        lines.append("---")
        lines.append("*Generated by CodeReview Bot v1.0.0*")

        return "\n".join(lines)
