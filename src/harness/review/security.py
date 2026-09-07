"""SecurityScanner — security vulnerability detection.

Scans code for common security vulnerabilities including injection, unsafe deserialization,
hardcoded secrets, and dangerous function usage.
"""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Vulnerability:
    """A security vulnerability finding."""

    file: str
    line: int
    severity: str
    message: str
    cwe_id: str
    category: str = "security"
    column: int = 0


@dataclass
class SecurityReport:
    """Aggregated security report."""

    vulnerabilities: list[Vulnerability] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    overall_score: float | None = None
    scan_metadata: dict[str, Any] = field(default_factory=dict)


class SecurityScanner:
    """Scans code for security vulnerabilities.

    Detects injection flaws, hardcoded secrets, unsafe deserialization,
    path traversal, and other common security issues.
    """

    # Patterns for hardcoded secrets
    SECRET_PATTERNS = [
        (
            re.compile(r"""(?:password|passwd|secret|token|api_key|apikey)\s*=\s*["'][^"']{8,}["']""", re.IGNORECASE),
            "CWE-798",
            "Hardcoded credentials",
        ),
        (
            re.compile(r"""(?:AWS|AMAZON)_?(?:ACCESS_?KEY|SECRET_?KEY)?\s*=\s*["'][A-Z0-9/+=]{20,}["']""", re.IGNORECASE),
            "CWE-798",
            "Hardcoded AWS credentials",
        ),
        (
            re.compile(r"""-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----"""),
            "CWE-798",
            "Private key embedded in source",
        ),
        (
            re.compile(r"""(?:sk|pk)_(?:test|live)_[A-Za-z0-9]{24,}"""),
            "CWE-798",
            "Hardcoded API key (Stripe-style)",
        ),
    ]

    # Dangerous functions and their CWEs
    DANGEROUS_FUNCTIONS = {
        "eval": ("CWE-95", "Code injection via eval()"),
        "exec": ("CWE-95", "Code injection via exec()"),
        "pickle.loads": ("CWE-502", "Unsafe deserialization with pickle"),
        "pickle.load": ("CWE-502", "Unsafe deserialization with pickle"),
        "yaml.load": ("CWE-502", "Unsafe YAML deserialization (use yaml.safe_load)"),
        "marshal.loads": ("CWE-502", "Unsafe deserialization with marshal"),
        "marshal.load": ("CWE-502", "Unsafe deserialization with marshal"),
        "subprocess.call": ("CWE-78", "OS command injection risk"),
        "subprocess.Popen": ("CWE-78", "OS command injection risk"),
        "os.system": ("CWE-78", "OS command injection risk"),
        "os.popen": ("CWE-78", "OS command injection risk"),
        "input": ("CWE-20", "Unvalidated input (Python 2 raw_input equivalent)"),
    }

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        re.compile(r"""(?:execute|executemany)\s*\(\s*["'].*%s"""),
        re.compile(r"""(?:execute|executemany)\s*\(\s*f["']"""),
        re.compile(r"""(?:execute|executemany)\s*\(\s*["'].*\+"""),
        re.compile(r"""(?:execute|executemany)\s*\(\s*.*\.format\("""),
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        re.compile(r"""(?:open|file|read|write)\s*\(\s*.*\+"""),
        re.compile(r"""(?:open|file|read|write)\s*\(\s*f["']"""),
    ]

    def scan_files(self, files: dict[str, str]) -> SecurityReport:
        """Scan files for security vulnerabilities.

        Args:
            files: Mapping of filename to source code.

        Returns:
            SecurityReport with findings.
        """
        vulnerabilities: list[Vulnerability] = []
        suggestions: list[str] = []

        for filename, source in files.items():
            if not filename.endswith(".py"):
                continue

            vulns = self._scan_file(filename, source)
            vulnerabilities.extend(vulns)

        # Generate suggestions
        suggestions.extend(self._generate_suggestions(vulnerabilities))

        # Compute score
        score = self._compute_score(vulnerabilities)

        return SecurityReport(
            vulnerabilities=vulnerabilities,
            suggestions=suggestions,
            overall_score=score,
            scan_metadata={
                "files_scanned": len(files),
                "vulnerability_count": len(vulnerabilities),
                "categories": list({v.category for v in vulnerabilities}),
            },
        )

    def _scan_file(self, filename: str, source: str) -> list[Vulnerability]:
        """Scan a single file for vulnerabilities."""
        vulnerabilities: list[Vulnerability] = []
        lines = source.splitlines()

        # Pattern-based checks
        for i, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("#"):
                continue

            # Check for hardcoded secrets
            for pattern, cwe, message in self.SECRET_PATTERNS:
                if pattern.search(line):
                    vulnerabilities.append(
                        Vulnerability(
                            file=filename,
                            line=i,
                            severity="critical",
                            message=message,
                            cwe_id=cwe,
                            category="hardcoded-secret",
                        )
                    )

            # Check for dangerous functions
            for func_name, (cwe, message) in self.DANGEROUS_FUNCTIONS.items():
                if self._line_uses_function(line, func_name):
                    severity = "high"
                    if func_name in ("eval", "exec"):
                        severity = "critical"
                    elif func_name.startswith("pickle") or func_name.startswith("marshal"):
                        severity = "high"
                    elif func_name.startswith("subprocess") or func_name.startswith("os."):
                        severity = "medium"

                    vulnerabilities.append(
                        Vulnerability(
                            file=filename,
                            line=i,
                            severity=severity,
                            message=message,
                            cwe_id=cwe,
                            category="dangerous-function",
                        )
                    )

            # Check for SQL injection
            for pattern in self.SQL_INJECTION_PATTERNS:
                if pattern.search(line):
                    vulnerabilities.append(
                        Vulnerability(
                            file=filename,
                            line=i,
                            severity="critical",
                            message="Potential SQL injection — use parameterized queries",
                            cwe_id="CWE-89",
                            category="sql-injection",
                        )
                    )

            # Check for path traversal
            for pattern in self.PATH_TRAVERSAL_PATTERNS:
                if pattern.search(line):
                    vulnerabilities.append(
                        Vulnerability(
                            file=filename,
                            line=i,
                            severity="medium",
                            message="Potential path traversal — validate file paths",
                            cwe_id="CWE-22",
                            category="path-traversal",
                        )
                    )

            # Check for assert statements (disabled with -O flag)
            if re.search(r"^\s*assert\s+", line):
                vulnerabilities.append(
                    Vulnerability(
                        file=filename,
                        line=i,
                        severity="low",
                        message="Assert used for validation — asserts are removed with -O flag",
                        cwe_id="CWE-703",
                        category="improper-handling",
                    )
                )

        # AST-based checks
        try:
            tree = ast.parse(source)
            ast_vulns = self._scan_ast(filename, tree)
            vulnerabilities.extend(ast_vulns)
        except SyntaxError:
            pass  # Already reported by quality checker

        return vulnerabilities

    def _scan_ast(self, filename: str, tree: ast.Module) -> list[Vulnerability]:
        """AST-based security checks."""
        vulnerabilities: list[Vulnerability] = []

        for node in ast.walk(tree):
            # Check for use of assert for security checks
            if isinstance(node, ast.Assert):
                vulnerabilities.append(
                    Vulnerability(
                        file=filename,
                        line=node.lineno,
                        severity="low",
                        message="Assert statement — not suitable for security checks",
                        cwe_id="CWE-703",
                        category="improper-handling",
                    )
                )

            # Check for __import__ usage
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "__import__":
                    vulnerabilities.append(
                        Vulnerability(
                            file=filename,
                            line=node.lineno,
                            severity="medium",
                            message="Use of __import__() — prefer importlib.import_module()",
                            cwe_id="CWE-95",
                            category="dangerous-function",
                        )
                    )

            # Check for compile() usage
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "compile":
                    vulnerabilities.append(
                        Vulnerability(
                            file=filename,
                            line=node.lineno,
                            severity="medium",
                            message="Use of compile() — potential code injection vector",
                            cwe_id="CWE-95",
                            category="dangerous-function",
                        )
                    )

            # Check for globals()/locals() usage
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ("globals", "locals"):
                    vulnerabilities.append(
                        Vulnerability(
                            file=filename,
                            line=node.lineno,
                            severity="low",
                            message=f"Use of {node.func.id}() — potential information disclosure",
                            cwe_id="CWE-916",
                            category="improper-handling",
                        )
                    )

        return vulnerabilities

    def _line_uses_function(self, line: str, func_name: str) -> bool:
        """Check if a line uses a specific function."""
        # Simple heuristic: look for the function name followed by (
        # Avoid matching it inside strings or comments
        stripped = line.strip()
        if stripped.startswith("#"):
            return False

        # Remove string literals for analysis
        cleaned = re.sub(r"""(["'])(?:(?=(\\?))\2.)*?\1""", '""', stripped)

        # Check for function call pattern
        if "." in func_name:
            # Method call like pickle.loads
            pattern = re.escape(func_name) + r"\s*\("
        else:
            # Direct function call
            pattern = r"\b" + re.escape(func_name) + r"\s*\("

        return bool(re.search(pattern, cleaned))

    def _generate_suggestions(self, vulnerabilities: list[Vulnerability]) -> list[str]:
        """Generate security improvement suggestions."""
        suggestions: list[str] = []
        categories = {v.category for v in vulnerabilities}

        if "hardcoded-secret" in categories:
            suggestions.append(
                "Use environment variables or a secrets manager instead of hardcoded credentials"
            )
        if "sql-injection" in categories:
            suggestions.append(
                "Use parameterized queries or an ORM to prevent SQL injection"
            )
        if "dangerous-function" in categories:
            suggestions.append(
                "Replace dangerous functions (eval, exec, pickle) with safer alternatives"
            )
        if "path-traversal" in categories:
            suggestions.append(
                "Validate and sanitize all file paths using os.path.abspath() and os.path.realpath()"
            )

        if not suggestions and not vulnerabilities:
            suggestions.append("No security vulnerabilities detected — good job!")

        return suggestions

    def _compute_score(self, vulnerabilities: list[Vulnerability]) -> float:
        """Compute security score (0-100) from vulnerabilities."""
        score = 100.0
        severity_weights = {"info": 1.0, "low": 3.0, "medium": 7.0, "high": 15.0, "critical": 35.0}

        for vuln in vulnerabilities:
            weight = severity_weights.get(vuln.severity, 5.0)
            score -= weight

        return max(0.0, min(100.0, score))
