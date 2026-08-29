"""Static analysis integration for pylint, mypy, ruff, and eslint."""

from __future__ import annotations

import asyncio
import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import Issue, Severity


@dataclass
class AnalysisConfig:
    """Configuration for static analysis tools."""
    enable_pylint: bool = True
    enable_mypy: bool = True
    enable_ruff: bool = True
    enable_eslint: bool = True
    pylint_rc: str = ""
    mypy_ini: str = ""
    ruff_config: str = ""
    eslint_config: str = ""


class StaticAnalyzer:
    """Runs static analysis tools and parses their output."""

    def __init__(self, config: AnalysisConfig | None = None):
        self.config = config or AnalysisConfig()

    async def analyze(self, file_path: str, language: str = "python") -> list[Issue]:
        """Run all enabled static analysis tools on a file."""
        issues: list[Issue] = []
        tasks = []

        if language == "python":
            if self.config.enable_pylint:
                tasks.append(self._run_pylint(file_path))
            if self.config.enable_mypy:
                tasks.append(self._run_mypy(file_path))
            if self.config.enable_ruff:
                tasks.append(self._run_ruff(file_path))
        elif language in ("javascript", "typescript"):
            if self.config.enable_eslint:
                tasks.append(self._run_eslint(file_path))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, list):
                issues.extend(result)
            elif isinstance(result, Exception):
                # Log error but don't fail the review
                pass

        return issues

    async def _run_pylint(self, file_path: str) -> list[Issue]:
        """Run pylint on a Python file."""
        cmd = ["pylint", "--output-format=json", file_path]
        if self.config.pylint_rc:
            cmd.insert(1, f"--rcfile={self.config.pylint_rc}")

        result = await self._run_command(cmd)
        if not result:
            return []

        issues = []
        try:
            data = json.loads(result)
            for item in data:
                severity = self._pylint_severity(item.get("type", "convention"))
                issues.append(Issue(
                    file=file_path,
                    line=item.get("line", 0),
                    column=item.get("column", 0),
                    severity=severity,
                    message=item.get("message", ""),
                    rule_id=item.get("symbol", ""),
                    source="pylint",
                ))
        except json.JSONDecodeError:
            pass
        return issues

    async def _run_mypy(self, file_path: str) -> list[Issue]:
        """Run mypy on a Python file."""
        cmd = ["mypy", "--show-column-numbers", "--no-error-summary", file_path]
        if self.config.mypy_ini:
            cmd.insert(1, f"--config-file={self.config.mypy_ini}")

        result = await self._run_command(cmd)
        if not result:
            return []

        issues = []
        for line in result.strip().split("\n"):
            if not line:
                continue
            # Parse mypy output: file:line:col: severity: message
            parts = line.split(":", 3)
            if len(parts) >= 4:
                try:
                    issues.append(Issue(
                        file=parts[0],
                        line=int(parts[1]),
                        column=int(parts[2]),
                        severity=self._mypy_severity(parts[3]),
                        message=parts[3].split(": ", 1)[1] if ": " in parts[3] else parts[3],
                        rule_id="mypy",
                        source="mypy",
                    ))
                except (ValueError, IndexError):
                    continue
        return issues

    async def _run_ruff(self, file_path: str) -> list[Issue]:
        """Run ruff on a Python file."""
        cmd = ["ruff", "check", "--output-format=json", file_path]
        if self.config.ruff_config:
            cmd.insert(1, f"--config={self.config.ruff_config}")

        result = await self._run_command(cmd)
        if not result:
            return []

        issues = []
        try:
            data = json.loads(result)
            for item in data:
                severity = self._ruff_severity(item.get("code", ""))
                issues.append(Issue(
                    file=item.get("filename", file_path),
                    line=item.get("location", {}).get("row", 0),
                    column=item.get("location", {}).get("column", 0),
                    severity=severity,
                    message=item.get("message", ""),
                    rule_id=item.get("code", ""),
                    source="ruff",
                    suggestion=item.get("fix", {}).get("message", "") if item.get("fix") else "",
                ))
        except json.JSONDecodeError:
            pass
        return issues

    async def _run_eslint(self, file_path: str) -> list[Issue]:
        """Run eslint on a JavaScript/TypeScript file."""
        cmd = ["eslint", "--format=json", file_path]
        if self.config.eslint_config:
            cmd.insert(1, f"--config={self.config.eslint_config}")

        result = await self._run_command(cmd)
        if not result:
            return []

        issues = []
        try:
            data = json.loads(result)
            for file_result in data:
                for msg in file_result.get("messages", []):
                    severity = self._eslint_severity(msg.get("severity", 1))
                    issues.append(Issue(
                        file=file_result.get("filePath", file_path),
                        line=msg.get("line", 0),
                        column=msg.get("column", 0),
                        severity=severity,
                        message=msg.get("message", ""),
                        rule_id=msg.get("ruleId", ""),
                        source="eslint",
                    ))
        except json.JSONDecodeError:
            pass
        return issues

    async def _run_command(self, cmd: list[str]) -> str:
        """Run a command and return stdout."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            return stdout.decode("utf-8", errors="replace")
        except FileNotFoundError:
            return ""

    def _pylint_severity(self, type_: str) -> Severity:
        mapping = {
            "convention": Severity.INFO,
            "refactor": Severity.INFO,
            "warning": Severity.WARNING,
            "error": Severity.ERROR,
            "fatal": Severity.CRITICAL,
        }
        return mapping.get(type_, Severity.WARNING)

    def _mypy_severity(self, part: str) -> Severity:
        if "error" in part.lower():
            return Severity.ERROR
        return Severity.WARNING

    def _ruff_severity(self, code: str) -> Severity:
        if code.startswith("E"):
            return Severity.ERROR
        if code.startswith("F"):
            return Severity.ERROR
        if code.startswith("W"):
            return Severity.WARNING
        return Severity.INFO

    def _eslint_severity(self, level: int) -> Severity:
        if level >= 2:
            return Severity.ERROR
        return Severity.WARNING
