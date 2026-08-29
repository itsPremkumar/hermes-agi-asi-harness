"""Performance regression detection."""

from __future__ import annotations

import re
from typing import Any

from .models import Issue, Severity


# Performance anti-patterns
PERFORMANCE_PATTERNS: list[dict[str, Any]] = [
    {
        "pattern": r"for\s+\w+\s+in\s+range\s*\(\s*len\s*\(",
        "message": "Using range(len()) instead of enumerate() is less readable and potentially slower",
        "severity": Severity.INFO,
        "rule_id": "PERF001",
        "suggestion": "Use enumerate() instead of range(len())",
    },
    {
        "pattern": r"\.append\s*\(\s*\)\s*(?:for|if)",
        "message": "List comprehension is faster than append in a loop",
        "severity": Severity.INFO,
        "rule_id": "PERF002",
        "suggestion": "Use list comprehension instead of append in a loop",
    },
    {
        "pattern": r"while\s+True\s*:",
        "message": "Infinite loop detected; ensure there is a break condition",
        "severity": Severity.WARNING,
        "rule_id": "PERF003",
        "suggestion": "Add a clear break condition or use a different loop structure",
    },
    {
        "pattern": r"time\.sleep\s*\(",
        "message": "time.sleep() blocks the thread; consider async alternatives",
        "severity": Severity.WARNING,
        "rule_id": "PERF004",
        "suggestion": "Use asyncio.sleep() in async contexts",
    },
    {
        "pattern": r"SELECT\s+\*\s+FROM",
        "message": "SELECT * can be slow; specify only needed columns",
        "severity": Severity.WARNING,
        "rule_id": "PERF005",
        "suggestion": "Specify only the columns you need",
    },
    {
        "pattern": r"\.find\s*\(\s*\)\s*==\s*-1",
        "message": "Use 'in' operator instead of find() for membership testing",
        "severity": Severity.INFO,
        "rule_id": "PERF006",
        "suggestion": "Use 'substring in string' instead of 'string.find(substring) != -1'",
    },
    {
        "pattern": r"global\s+\w+",
        "message": "Global variables can cause performance issues and make code harder to reason about",
        "severity": Severity.WARNING,
        "rule_id": "PERF007",
        "suggestion": "Pass variables as parameters or use class attributes",
    },
    {
        "pattern": r"import\s+\w+\s+inside\s+(?:function|method)",
        "message": "Import inside function can cause repeated import overhead",
        "severity": Severity.INFO,
        "rule_id": "PERF008",
        "suggestion": "Move imports to the top of the file unless circular imports require otherwise",
    },
]


class PerformanceAnalyzer:
    """Detects performance anti-patterns in code."""

    def __init__(self, custom_patterns: list[dict[str, Any]] | None = None):
        self.patterns = PERFORMANCE_PATTERNS + (custom_patterns or [])

    def analyze_diff(self, diff: str) -> list[Issue]:
        """Analyze a diff for performance issues."""
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
                for pattern in self.patterns:
                    if re.search(pattern["pattern"], line[1:], re.IGNORECASE):
                        issues.append(Issue(
                            file=current_file,
                            line=line_number,
                            severity=pattern["severity"],
                            message=pattern["message"],
                            rule_id=pattern["rule_id"],
                            source="performance",
                            suggestion=pattern.get("suggestion", ""),
                        ))
            elif not line.startswith("-"):
                line_number += 1

        return issues

    def analyze_complexity(self, file_path: str, content: str) -> list[str]:
        """Analyze code complexity and return notes."""
        notes = []
        lines = content.split("\n")

        # Check for deeply nested code
        max_indent = 0
        for line in lines:
            indent = len(line) - len(line.lstrip())
            if indent > max_indent:
                max_indent = indent

        if max_indent > 20:
            notes.append(f"Deep nesting detected in {file_path} (max indent: {max_indent} spaces)")

        # Check for long functions
        func_start = 0
        func_name = ""
        for i, line in enumerate(lines):
            if line.strip().startswith("def "):
                if func_name:
                    func_len = i - func_start
                    if func_len > 50:
                        notes.append(f"Long function '{func_name}' in {file_path} ({func_len} lines)")
                func_start = i
                func_name = line.strip().split("(")[0].replace("def ", "")

        return notes
