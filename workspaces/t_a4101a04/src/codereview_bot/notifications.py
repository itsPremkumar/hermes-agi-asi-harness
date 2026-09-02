"""Slack and Teams notification integration."""

from __future__ import annotations

import json
from typing import Any

from .models import ReviewResult


class NotificationClient:
    """Sends review notifications to Slack and Teams."""

    def __init__(self, slack_webhook_url: str = "", teams_webhook_url: str = ""):
        self.slack_webhook_url = slack_webhook_url
        self.teams_webhook_url = teams_webhook_url

    async def notify_review_complete(self, result: ReviewResult) -> None:
        """Send review completion notification to all configured channels."""
        if self.slack_webhook_url:
            await self._send_slack(result)
        if self.teams_webhook_url:
            await self._send_teams(result)

    async def _send_slack(self, result: ReviewResult) -> None:
        """Send notification to Slack."""
        import httpx

        payload = self._build_slack_payload(result)
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(self.slack_webhook_url, json=payload)

    async def _send_teams(self, result: ReviewResult) -> None:
        """Send notification to Microsoft Teams."""
        import httpx

        payload = self._build_teams_payload(result)
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(self.teams_webhook_url, json=payload)

    def _build_slack_payload(self, result: ReviewResult) -> dict[str, Any]:
        """Build Slack message payload."""
        issue_count = len(result.issues)
        severity_counts = self._count_by_severity(result.issues)

        color = "#36a64f"  # green
        if severity_counts.get("critical", 0) > 0:
            color = "#ff0000"  # red
        elif severity_counts.get("error", 0) > 0:
            color = "#ff9900"  # orange
        elif severity_counts.get("warning", 0) > 0:
            color = "#ffcc00"  # yellow

        fields = [
            {"title": "Repository", "value": result.repo, "short": True},
            {"title": "PR Number", "value": f"#{result.pr_number}", "short": True},
            {"title": "Total Issues", "value": str(issue_count), "short": True},
        ]

        for severity, count in severity_counts.items():
            fields.append({"title": severity.capitalize(), "value": str(count), "short": True})

        return {
            "attachments": [
                {
                    "color": color,
                    "title": f"CodeReview Bot — PR #{result.pr_number} Review Complete",
                    "text": result.summary or "Review completed",
                    "fields": fields,
                    "footer": "CodeReview Bot v1.0.0",
                }
            ]
        }

    def _build_teams_payload(self, result: ReviewResult) -> dict[str, Any]:
        """Build Microsoft Teams message payload (MessageCard)."""
        issue_count = len(result.issues)
        severity_counts = self._count_by_severity(result.issues)

        facts = [
            {"name": "Repository", "value": result.repo},
            {"name": "PR Number", "value": f"#{result.pr_number}"},
            {"name": "Total Issues", "value": str(issue_count)},
        ]

        for severity, count in severity_counts.items():
            facts.append({"name": severity.capitalize(), "value": str(count)})

        theme_color = "00FF00"  # green
        if severity_counts.get("critical", 0) > 0:
            theme_color = "FF0000"  # red
        elif severity_counts.get("error", 0) > 0:
            theme_color = "FF9900"  # orange
        elif severity_counts.get("warning", 0) > 0:
            theme_color = "FFCC00"  # yellow

        return {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "themeColor": theme_color,
            "summary": f"CodeReview Bot — PR #{result.pr_number} Review Complete",
            "sections": [
                {
                    "activityTitle": f"CodeReview Bot — PR #{result.pr_number}",
                    "activitySubtitle": result.repo,
                    "text": result.summary or "Review completed",
                    "facts": facts,
                }
            ],
        }

    def _count_by_severity(self, issues: list[Any]) -> dict[str, int]:
        """Count issues by severity."""
        counts: dict[str, int] = {}
        for issue in issues:
            sev = issue.severity.value if hasattr(issue.severity, "value") else str(issue.severity)
            counts[sev] = counts.get(sev, 0) + 1
        return counts
