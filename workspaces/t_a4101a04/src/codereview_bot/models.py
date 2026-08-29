"""Data models for CodeReview Bot."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    """Issue severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ReviewStatus(str, Enum):
    """Review completion status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Issue:
    """A single review issue."""
    file: str
    line: int
    column: int = 0
    severity: Severity = Severity.WARNING
    message: str = ""
    rule_id: str = ""
    source: str = ""  # e.g., "pylint", "security", "ai_review"
    suggestion: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "severity": self.severity.value,
            "message": self.message,
            "rule_id": self.rule_id,
            "source": self.source,
            "suggestion": self.suggestion,
        }


@dataclass
class ReviewResult:
    """Complete review result for a PR."""
    pr_number: int
    repo: str
    status: ReviewStatus = ReviewStatus.PENDING
    issues: list[Issue] = field(default_factory=list)
    summary: str = ""
    coverage_impact: float | None = None
    performance_notes: list[str] = field(default_factory=list)
    security_findings: list[Issue] = field(default_factory=list)

    def add_issue(self, issue: Issue) -> None:
        self.issues.append(issue)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pr_number": self.pr_number,
            "repo": self.repo,
            "status": self.status.value,
            "issues": [i.to_dict() for i in self.issues],
            "summary": self.summary,
            "coverage_impact": self.coverage_impact,
            "performance_notes": self.performance_notes,
            "security_findings": [s.to_dict() for s in self.security_findings],
        }


@dataclass
class PullRequest:
    """GitHub Pull Request data."""
    number: int
    title: str
    body: str
    head_sha: str
    base_sha: str
    head_ref: str
    base_ref: str
    user: str
    repo_full_name: str
    diff_url: str
    changed_files: int = 0
    additions: int = 0
    deletions: int = 0

    @classmethod
    def from_webhook(cls, payload: dict[str, Any]) -> "PullRequest":
        pr = payload.get("pull_request", {})
        return cls(
            number=pr.get("number", 0),
            title=pr.get("title", ""),
            body=pr.get("body", ""),
            head_sha=pr.get("head", {}).get("sha", ""),
            base_sha=pr.get("base", {}).get("sha", ""),
            head_ref=pr.get("head", {}).get("ref", ""),
            base_ref=pr.get("base", {}).get("ref", ""),
            user=pr.get("user", {}).get("login", ""),
            repo_full_name=payload.get("repository", {}).get("full_name", ""),
            diff_url=pr.get("diff_url", ""),
            changed_files=pr.get("changed_files", 0),
            additions=pr.get("additions", 0),
            deletions=pr.get("deletions", 0),
        )
