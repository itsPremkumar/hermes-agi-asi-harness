"""Reviewer assignment based on CODEOWNERS."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class ReviewAssigner:
    """Assigns reviewers based on CODEOWNERS file and change patterns."""

    def __init__(self, codeowners_path: str = ".github/CODEOWNERS"):
        self.codeowners_path = codeowners_path
        self.rules: list[tuple[str, list[str]]] = []
        self.default_reviewers: list[str] = []

    def load_codeowners(self, content: str) -> None:
        """Parse CODEOWNERS file content."""
        self.rules = []
        self.default_reviewers = []

        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if len(parts) >= 2:
                pattern = parts[0]
                reviewers = [r.lstrip("@") for r in parts[1:]]

                if pattern == "*":
                    self.default_reviewers = reviewers
                else:
                    self.rules.append((pattern, reviewers))

    def assign_reviewers(self, changed_files: list[str]) -> dict[str, list[str]]:
        """Assign reviewers based on changed files."""
        assignments: dict[str, list[str]] = {}

        for file_path in changed_files:
            matched = False
            for pattern, reviewers in self.rules:
                if self._matches_pattern(file_path, pattern):
                    for reviewer in reviewers:
                        if reviewer not in assignments:
                            assignments[reviewer] = []
                        if file_path not in assignments[reviewer]:
                            assignments[reviewer].append(file_path)
                    matched = True

            if not matched and self.default_reviewers:
                for reviewer in self.default_reviewers:
                    if reviewer not in assignments:
                        assignments[reviewer] = []
                    assignments[reviewer].append(file_path)

        return assignments

    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if a file path matches a CODEOWNERS pattern."""
        # Convert CODEOWNERS glob to regex
        regex_pattern = pattern
        # ** matches any path including /
        regex_pattern = regex_pattern.replace("**", "{{GLOBSTAR}}")
        # Leading * (not preceded by /) matches any path prefix
        if regex_pattern.startswith("*"):
            regex_pattern = "{{ANY}}" + regex_pattern[1:]
        # Remaining * matches any chars except /
        regex_pattern = regex_pattern.replace("*", "[^/]*")
        regex_pattern = regex_pattern.replace("{{GLOBSTAR}}", ".*")
        regex_pattern = regex_pattern.replace("{{ANY}}", ".*")
        regex_pattern = regex_pattern.replace("?", ".")
        regex_pattern = f"^{regex_pattern}$"

        return bool(re.match(regex_pattern, file_path))

    def get_reviewers_for_pr(self, changed_files: list[str]) -> list[str]:
        """Get list of reviewers for a PR."""
        assignments = self.assign_reviewers(changed_files)
        return list(assignments.keys())
