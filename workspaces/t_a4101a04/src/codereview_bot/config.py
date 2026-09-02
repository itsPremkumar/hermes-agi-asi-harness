"""Configuration management for CodeReview Bot."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    # GitHub App settings
    github_app_id: int = 0
    github_private_key_path: str = ""
    github_webhook_secret: str = ""

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # AI settings
    ai_provider: str = "openai"
    ai_model: str = "gpt-4o-mini"
    ai_api_key: str = ""

    # Notification settings
    slack_webhook_url: str = ""
    teams_webhook_url: str = ""

    # Analysis settings
    max_diff_lines: int = 500
    max_files_reviewed: int = 50
    enable_security_scan: bool = True
    enable_performance_check: bool = True
    enable_coverage_check: bool = True

    # Rule engine
    rules_path: str = ".codereview.yaml"

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        return cls(
            github_app_id=int(os.getenv("GITHUB_APP_ID", "0")),
            github_private_key_path=os.getenv("GITHUB_PRIVATE_KEY_PATH", ""),
            github_webhook_secret=os.getenv("GITHUB_WEBHOOK_SECRET", ""),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            ai_provider=os.getenv("AI_PROVIDER", "openai"),
            ai_model=os.getenv("AI_MODEL", "gpt-4o-mini"),
            ai_api_key=os.getenv("AI_API_KEY", ""),
            slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL", ""),
            teams_webhook_url=os.getenv("TEAMS_WEBHOOK_URL", ""),
            max_diff_lines=int(os.getenv("MAX_DIFF_LINES", "500")),
            max_files_reviewed=int(os.getenv("MAX_FILES_REVIEWED", "50")),
            enable_security_scan=os.getenv("ENABLE_SECURITY_SCAN", "true").lower() == "true",
            enable_performance_check=os.getenv("ENABLE_PERFORMANCE_CHECK", "true").lower() == "true",
            enable_coverage_check=os.getenv("ENABLE_COVERAGE_CHECK", "true").lower() == "true",
            rules_path=os.getenv("RULES_PATH", ".codereview.yaml"),
        )

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        if not self.github_app_id:
            errors.append("GITHUB_APP_ID is required")
        if not self.github_private_key_path:
            errors.append("GITHUB_PRIVATE_KEY_PATH is required")
        if self.github_private_key_path and not Path(self.github_private_key_path).exists():
            errors.append(f"Private key not found: {self.github_private_key_path}")
        return errors
