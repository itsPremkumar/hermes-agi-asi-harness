"""
SelfHealer — Detect and fix common issues automatically.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class IssueCategory(str, Enum):
    SYNTAX = "syntax"
    IMPORT = "import"
    STYLE = "style"
    SECURITY = "security"
    PERFORMANCE = "performance"
    LOGIC = "logic"


@dataclass
class DetectedIssue:
    """An issue detected by the SelfHealer."""

    file_path: str
    line: int
    category: IssueCategory
    severity: str  # low, medium, high, critical
    message: str
    fixable: bool = True
    fix_description: str = ""


@dataclass
class HealResult:
    """Result of a healing operation."""

    file_path: str
    issues_detected: int = 0
    issues_fixed: int = 0
    issues_skipped: int = 0
    fixes_applied: list[dict[str, Any]] = field(default_factory=list)
    success: bool = True
    error: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


class SelfHealer:
    """Detects and automatically fixes common code issues."""

    def __init__(self, project_root: str | Path | None = None, dry_run: bool = False) -> None:
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.dry_run = dry_run
        self._heal_history: list[HealResult] = []
        self._issue_patterns = self._build_issue_patterns()

    @property
    def heal_history(self) -> list[HealResult]:
        return list(self._heal_history)

    @staticmethod
    def _build_issue_patterns() -> list[dict[str, Any]]:
        """Build regex patterns for common issue detection."""
        return [
            {
                "pattern": re.compile(r"^\s*import\s+(\w+)\s*$"),
                "category": IssueCategory.IMPORT,
                "check": "unused_import",
            },
            {
                "pattern": re.compile(r"except\s*:"),
                "category": IssueCategory.LOGIC,
                "severity": "high",
                "message": "Bare except clause — catches SystemExit and KeyboardInterrupt",
                "fixable": True,
                "fix_description": "Replace 'except:' with 'except Exception:'",
            },
            {
                "pattern": re.compile(r"print\s*\("),
                "category": IssueCategory.STYLE,
                "severity": "low",
                "message": "Print statement found — consider using logging",
                "fixable": False,
            },
            {
                "pattern": re.compile(r"\.has_key\s*\("),
                "category": IssueCategory.STYLE,
                "severity": "medium",
                "message": "Deprecated .has_key() — use 'in' operator",
                "fixable": True,
                "fix_description": "Replace .has_key(x) with 'x in dict'",
            },
            {
                "pattern": re.compile(r"==\s*(True|False|None)\b"),
                "category": IssueCategory.STYLE,
                "severity": "low",
                "message": "Comparison to True/False/None — use 'is' or 'is not'",
                "fixable": True,
                "fix_description": "Use 'is None' / 'is not None' instead of ==",
            },
            {
                "pattern": re.compile(r"except\s+(\w+)\s*,\s*(\w+)\s*:"),
                "category": IssueCategory.SYNTAX,
                "severity": "critical",
                "message": "Python 2 except syntax — use 'as' instead of comma",
                "fixable": True,
                "fix_description": "Replace 'except E, e:' with 'except E as e:'",
            },
            {
                "pattern": re.compile(r"raise\s+(\w+)\s*,\s*"),
                "category": IssueCategory.SYNTAX,
                "severity": "critical",
                "message": "Python 2 raise syntax — use 'raise Exception()'",
                "fixable": True,
                "fix_description": "Use Python 3 raise syntax",
            },
            {
                "pattern": re.compile(r"^\s{2,3}\S"),
                "category": IssueCategory.STYLE,
                "severity": "low",
                "message": "Inconsistent indentation — use 4 spaces",
                "fixable": True,
                "fix_description": "Convert to 4-space indentation",
            },
        ]

    def scan_file(self, file_path: str | Path) -> list[DetectedIssue]:
        """Scan a single file for common issues."""
        path = Path(file_path)
        issues: list[DetectedIssue] = []

        if not path.exists() or not path.suffix == ".py":
            return issues

        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return issues

        lines = source.splitlines()

        # AST-based checks
        try:
            tree = ast.parse(source)
            issues.extend(self._ast_checks(tree, str(path)))
        except SyntaxError as e:
            issues.append(DetectedIssue(
                file_path=str(path),
                line=e.lineno or 0,
                category=IssueCategory.SYNTAX,
                severity="critical",
                message=f"Syntax error: {e.msg}",
                fixable=False,
            ))

        # Pattern-based checks
        for i, line in enumerate(lines, 1):
            for pat_info in self._issue_patterns:
                pattern = pat_info["pattern"]
                if pattern.search(line):
                    # Skip if it's a comment or string
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue

                    issues.append(DetectedIssue(
                        file_path=str(path),
                        line=i,
                        category=pat_info["category"],
                        severity=pat_info.get("severity", "medium"),
                        message=pat_info.get("message", "Issue detected"),
                        fixable=pat_info.get("fixable", False),
                        fix_description=pat_info.get("fix_description", ""),
                    ))

        return issues

    def _ast_checks(self, tree: ast.AST, file_path: str) -> list[DetectedIssue]:
        """Run AST-based checks on parsed code."""
        issues: list[DetectedIssue] = []

        for node in ast.walk(tree):
            # Check for mutable default arguments
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults + node.args.kw_defaults:
                    if default is None:
                        continue
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        issues.append(DetectedIssue(
                            file_path=file_path,
                            line=default.lineno,
                            category=IssueCategory.LOGIC,
                            severity="high",
                            message=f"Mutable default argument in '{node.name}' — use None and initialize in body",
                            fixable=False,
                        ))

            # Check for unused variables (simple heuristic)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                name = node.id
                if name == "_":
                    continue
                # Check if the name is used elsewhere in the same scope
                parent = getattr(node, "_parent", None)
                if parent:
                    used = any(
                        isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, ast.Load)
                        for n in ast.walk(parent)
                    )
                    if not used:
                        issues.append(DetectedIssue(
                            file_path=file_path,
                            line=node.lineno,
                            category=IssueCategory.LOGIC,
                            severity="low",
                            message=f"Potentially unused variable '{name}'",
                            fixable=False,
                        ))

        return issues

    def scan_project(self, file_paths: list[str] | list[Path] | None = None) -> list[DetectedIssue]:
        """Scan the entire project for issues."""
        if file_paths is None:
            file_paths = [str(p) for p in self.project_root.rglob("*.py") if "__pycache__" not in str(p)]

        all_issues: list[DetectedIssue] = []
        for fp in file_paths:
            all_issues.extend(self.scan_file(fp))

        return all_issues

    def heal_file(self, file_path: str | Path, issues: list[DetectedIssue] | None = None) -> HealResult:
        """Attempt to fix issues in a single file."""
        path = Path(file_path)
        result = HealResult(file_path=str(path))

        if not path.exists():
            result.success = False
            result.error = f"File not found: {file_path}"
            return result

        if issues is None:
            issues = self.scan_file(path)

        result.issues_detected = len(issues)

        fixable = [i for i in issues if i.fixable]
        result.issues_skipped = len(issues) - len(fixable)

        if not fixable:
            self._heal_history.append(result)
            return result

        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            result.success = False
            result.error = str(e)
            self._heal_history.append(result)
            return result

        healed = source

        for issue in fixable:
            fix = self._apply_fix(healed, issue)
            if fix != healed:
                healed = fix
                result.issues_fixed += 1
                result.fixes_applied.append({
                    "line": issue.line,
                    "category": issue.category.value,
                    "description": issue.fix_description,
                })

        if not self.dry_run and healed != source:
            path.write_text(healed, encoding="utf-8")

        self._heal_history.append(result)
        return result

    def _apply_fix(self, source: str, issue: DetectedIssue) -> str:
        """Apply a single fix to source code."""
        lines = source.splitlines(keepends=True)

        if issue.line < 1 or issue.line > len(lines):
            return source

        line = lines[issue.line - 1]

        # Bare except
        if "Bare except" in issue.message:
            lines[issue.line - 1] = line.replace("except:", "except Exception:")
            return "".join(lines)

        # .has_key()
        if ".has_key(" in issue.message:
            fixed = re.sub(r"\.has_key\(([^)]+)\)", r"in \1", line)
            lines[issue.line - 1] = fixed
            return "".join(lines)

        # == True/False/None
        if "Comparison to True/False/None" in issue.message:
            fixed = re.sub(r"==\s*True\b", "is True", line)
            fixed = re.sub(r"==\s*False\b", "is False", fixed)
            fixed = re.sub(r"==\s*None\b", "is None", fixed)
            fixed = re.sub(r"!=\s*None\b", "is not None", fixed)
            lines[issue.line - 1] = fixed
            return "".join(lines)

        # Python 2 except syntax
        if "Python 2 except syntax" in issue.message:
            fixed = re.sub(r"except\s+(\w+)\s*,\s*(\w+)\s*:", r"except \1 as \2:", line)
            lines[issue.line - 1] = fixed
            return "".join(lines)

        # Python 2 raise syntax
        if "Python 2 raise syntax" in issue.message:
            fixed = re.sub(r"raise\s+(\w+)\s*,\s*(.+)", r"raise \1(\2)", line)
            lines[issue.line - 1] = fixed
            return "".join(lines)

        # Inconsistent indentation
        if "Inconsistent indentation" in issue.message:
            # Count leading spaces
            stripped = line.lstrip()
            if stripped:
                spaces = len(line) - len(stripped)
                if spaces % 4 != 0:
                    new_spaces = ((spaces // 4) + 1) * 4
                    lines[issue.line - 1] = " " * new_spaces + stripped
                    return "".join(lines)

        return source

    def heal_project(self, file_paths: list[str] | list[Path] | None = None) -> list[HealResult]:
        """Scan and heal the entire project."""
        if file_paths is None:
            file_paths = [str(p) for p in self.project_root.rglob("*.py") if "__pycache__" not in str(p)]

        results: list[HealResult] = []
        for fp in file_paths:
            issues = self.scan_file(fp)
            if issues:
                result = self.heal_file(fp, issues)
                results.append(result)

        return results

    def get_healing_summary(self) -> dict[str, Any]:
        """Get a summary of all healing operations."""
        total_detected = sum(r.issues_detected for r in self._heal_history)
        total_fixed = sum(r.issues_fixed for r in self._heal_history)
        total_skipped = sum(r.issues_skipped for r in self._heal_history)
        total_files = len(self._heal_history)
        failures = sum(1 for r in self._heal_history if not r.success)

        return {
            "files_scanned": total_files,
            "issues_detected": total_detected,
            "issues_fixed": total_fixed,
            "issues_skipped": total_skipped,
            "fix_rate": total_fixed / total_detected if total_detected > 0 else 0.0,
            "failures": failures,
        }
