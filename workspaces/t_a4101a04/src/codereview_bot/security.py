"""Security vulnerability scanning."""

from __future__ import annotations

import re
from typing import Any

from .models import Issue, Severity


# Security patterns to detect in code
SECURITY_PATTERNS: list[dict[str, Any]] = [
    {
        "pattern": r"eval\s*\(",
        "message": "Use of eval() is dangerous and can lead to code injection",
        "severity": Severity.CRITICAL,
        "rule_id": "SEC001",
        "suggestion": "Use ast.literal_eval() or json.loads() for safe evaluation",
    },
    {
        "pattern": r"exec\s*\(",
        "message": "Use of exec() is dangerous and can lead to code injection",
        "severity": Severity.CRITICAL,
        "rule_id": "SEC002",
        "suggestion": "Avoid dynamic code execution; use safer alternatives",
    },
    {
        "pattern": r"os\.system\s*\(",
        "message": "os.system() is vulnerable to shell injection",
        "severity": Severity.ERROR,
        "rule_id": "SEC003",
        "suggestion": "Use subprocess.run() with shell=False and pass arguments as a list",
    },
    {
        "pattern": r"subprocess\..*shell\s*=\s*True",
        "message": "subprocess with shell=True is vulnerable to shell injection",
        "severity": Severity.ERROR,
        "rule_id": "SEC004",
        "suggestion": "Use shell=False and pass arguments as a list",
    },
    {
        "pattern": r"pickle\.loads?\s*\(",
        "message": "pickle deserialization can execute arbitrary code",
        "severity": Severity.ERROR,
        "rule_id": "SEC005",
        "suggestion": "Use json or msgpack for serialization of untrusted data",
    },
    {
        "pattern": r"yaml\.load\s*\(.*(?!\s*Loader\s*=)",
        "message": "yaml.load() without Loader is vulnerable to code execution",
        "severity": Severity.ERROR,
        "rule_id": "SEC006",
        "suggestion": "Use yaml.safe_load() or yaml.load(data, Loader=yaml.SafeLoader)",
    },
    {
        "pattern": r"input\s*\(",
        "message": "input() in Python 2 evaluates code; ensure Python 3 is used",
        "severity": Severity.WARNING,
        "rule_id": "SEC007",
        "suggestion": "Verify Python 3 is being used; input() is safe in Python 3",
    },
    {
        "pattern": r"password\s*=\s*['\"][^'\"]+['\"]",
        "message": "Hardcoded password detected",
        "severity": Severity.CRITICAL,
        "rule_id": "SEC008",
        "suggestion": "Use environment variables or a secrets manager",
    },
    {
        "pattern": r"api_key\s*=\s*['\"][^'\"]+['\"]",
        "message": "Hardcoded API key detected",
        "severity": Severity.CRITICAL,
        "rule_id": "SEC009",
        "suggestion": "Use environment variables or a secrets manager",
    },
    {
        "pattern": r"secret\s*=\s*['\"][^'\"]+['\"]",
        "message": "Hardcoded secret detected",
        "severity": Severity.CRITICAL,
        "rule_id": "SEC010",
        "suggestion": "Use environment variables or a secrets manager",
    },
    {
        "pattern": r"token\s*=\s*['\"][a-zA-Z0-9_\-]{20,}['\"]",
        "message": "Hardcoded token detected",
        "severity": Severity.CRITICAL,
        "rule_id": "SEC011",
        "suggestion": "Use environment variables or a secrets manager",
    },
    {
        "pattern": r"md5\s*\(",
        "message": "MD5 is cryptographically broken and should not be used for security",
        "severity": Severity.WARNING,
        "rule_id": "SEC012",
        "suggestion": "Use SHA-256 or better for cryptographic purposes",
    },
    {
        "pattern": r"sha1\s*\(",
        "message": "SHA-1 is cryptographically weak",
        "severity": Severity.WARNING,
        "rule_id": "SEC013",
        "suggestion": "Use SHA-256 or better for cryptographic purposes",
    },
    {
        "pattern": r"random\.random\s*\(",
        "message": "random.random() is not cryptographically secure",
        "severity": Severity.WARNING,
        "rule_id": "SEC014",
        "suggestion": "Use secrets module for cryptographic randomness",
    },
    {
        "pattern": r"debug\s*=\s*True",
        "message": "Debug mode should not be enabled in production",
        "severity": Severity.WARNING,
        "rule_id": "SEC015",
        "suggestion": "Set debug=False or use environment variable to control it",
    },
    {
        "pattern": r"verify\s*=\s*False",
        "message": "SSL certificate verification is disabled",
        "severity": Severity.ERROR,
        "rule_id": "SEC016",
        "suggestion": "Enable SSL verification to prevent MITM attacks",
    },
    {
        "pattern": r"\.format\s*\(.*\).*(?:SELECT|INSERT|UPDATE|DELETE)",
        "message": "Potential SQL injection via string formatting",
        "severity": Severity.CRITICAL,
        "rule_id": "SEC017",
        "suggestion": "Use parameterized queries instead of string formatting",
    },
    {
        "pattern": r"f['\"].*(?:SELECT|INSERT|UPDATE|DELETE).*",
        "message": "Potential SQL injection via f-string",
        "severity": Severity.CRITICAL,
        "rule_id": "SEC018",
        "suggestion": "Use parameterized queries instead of f-strings",
    },
]


class SecurityScanner:
    """Scans code for security vulnerabilities."""

    def __init__(self, custom_patterns: list[dict[str, Any]] | None = None):
        self.patterns = SECURITY_PATTERNS + (custom_patterns or [])

    def scan_diff(self, diff: str) -> list[Issue]:
        """Scan a diff for security issues."""
        issues = []
        current_file = ""
        line_number = 0

        for line in diff.split("\n"):
            # Track current file from diff headers
            if line.startswith("+++ b/"):
                current_file = line[6:]
                line_number = 0
            elif line.startswith("@@"):
                # Parse hunk header for line number
                match = re.search(r"@@ -\d+(?:,\d+)? \+(\d+)", line)
                if match:
                    line_number = int(match.group(1)) - 1
            elif line.startswith("+") and not line.startswith("+++"):
                line_number += 1
                # Scan added lines for security issues
                for pattern in self.patterns:
                    if re.search(pattern["pattern"], line[1:], re.IGNORECASE):
                        issues.append(Issue(
                            file=current_file,
                            line=line_number,
                            severity=pattern["severity"],
                            message=pattern["message"],
                            rule_id=pattern["rule_id"],
                            source="security",
                            suggestion=pattern.get("suggestion", ""),
                        ))
            elif not line.startswith("-"):
                line_number += 1

        return issues

    def scan_file(self, file_path: str, content: str) -> list[Issue]:
        """Scan a file's content for security issues."""
        issues = []
        for line_num, line in enumerate(content.split("\n"), 1):
            for pattern in self.patterns:
                if re.search(pattern["pattern"], line, re.IGNORECASE):
                    issues.append(Issue(
                        file=file_path,
                        line=line_num,
                        severity=pattern["severity"],
                        message=pattern["message"],
                        rule_id=pattern["rule_id"],
                        source="security",
                        suggestion=pattern.get("suggestion", ""),
                    ))
        return issues
