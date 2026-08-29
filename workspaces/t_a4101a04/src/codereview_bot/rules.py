"""Custom rule engine for code review."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .models import Issue, Severity


class RuleEngine:
    """Configurable rule engine for code review."""

    def __init__(self, rules_path: str = ".codereview.yaml"):
        self.rules_path = rules_path
        self.rules: list[dict[str, Any]] = []
        self.enabled = True

    def load_rules(self, content: str) -> None:
        """Load rules from YAML content."""
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict):
                self.rules = data.get("rules", [])
                self.enabled = data.get("enabled", True)
            else:
                self.rules = []
        except yaml.YAMLError:
            self.rules = []

    def load_from_file(self, path: str | None = None) -> bool:
        """Load rules from a file. Returns True if successful."""
        file_path = Path(path or self.rules_path)
        if not file_path.exists():
            return False
        try:
            self.load_rules(file_path.read_text())
            return True
        except OSError:
            return False

    def evaluate_diff(self, diff: str) -> list[Issue]:
        """Evaluate all rules against a diff."""
        if not self.enabled:
            return []

        issues = []
        current_file = ""
        line_number = 0

        for line in diff.split("\n"):
            if line.startswith("+++ b/"):
                current_file = line[6:]
                line_number = 0
            elif line.startswith("@@"):
                match = re.search(r"@@ -\d+(?:,\d+)? \+(\d+)", line)
                if match:
                    line_number = int(match.group(1)) - 1
            elif line.startswith("+") and not line.startswith("+++"):
                line_number += 1
                for rule in self.rules:
                    issue = self._evaluate_rule(rule, current_file, line_number, line[1:])
                    if issue:
                        issues.append(issue)
            elif not line.startswith("-"):
                line_number += 1

        return issues

    def _evaluate_rule(
        self, rule: dict[str, Any], file_path: str, line_number: int, line: str
    ) -> Issue | None:
        """Evaluate a single rule against a line."""
        if not rule.get("enabled", True):
            return None

        pattern = rule.get("pattern", "")
        if not pattern:
            return None

        # Check file pattern
        file_pattern = rule.get("files", "")
        if file_pattern and not re.search(file_pattern, file_path):
            return None

        # Check exclude pattern
        exclude_pattern = rule.get("exclude", "")
        if exclude_pattern and re.search(exclude_pattern, file_path):
            return None

        # Match the rule pattern
        if re.search(pattern, line, re.IGNORECASE):
            return Issue(
                file=file_path,
                line=line_number,
                severity=Severity(rule.get("severity", "warning")),
                message=rule.get("message", "Custom rule violation"),
                rule_id=rule.get("id", "custom"),
                source="custom_rule",
                suggestion=rule.get("suggestion", ""),
            )

        return None
