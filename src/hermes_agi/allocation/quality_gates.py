"""
Hermes AGI/ASI Harness — Autonomous Quality Gates & Continuation Enforcement.

Ported from Prime Agent (packages/coding-agent/src/core/autonomous.ts):
- Evaluates user-defined automated test / verification quality gates
- Forbids premature stopping when gates fail
- Injects evidence-backed autonomous continuation directives so the agent
  repairs failing tests rather than asking the user questions or giving up
"""

from __future__ import annotations

import logging
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes.allocation.quality_gates")

DEFAULT_AUTONOMOUS_CONTINUATION_DIRECTIVE = (
    "No human input is available in autonomous mode. Continue working until the host evaluator, "
    "verifier, or configured autonomous quality gates pass. If you were asking the user a question, "
    "make a reasonable technical assumption and verify it. If you believe you are blocked, prove it "
    "with host-observable evidence, preserve that evidence, and keep looking for safe progress while "
    "budget remains. Do not end the session yourself; the verifier decides completion when configured gates pass."
)


@dataclass
class QualityGateFailure:
    """Detailed diagnosis of a failing quality gate command."""
    command: str
    attempt: int
    exit_code: int
    output_snippet: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "attempt": self.attempt,
            "exit_code": self.exit_code,
            "output_snippet": self.output_snippet,
        }


@dataclass
class QualityGateVerdict:
    """Outcome of evaluating configured quality gates."""
    passed: bool
    total_gates: int
    passed_count: int
    failures: list[QualityGateFailure] = field(default_factory=list)
    continuation_directive: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "total_gates": self.total_gates,
            "passed_count": self.passed_count,
            "failures": [f.to_dict() for f in self.failures],
            "continuation_directive": self.continuation_directive,
        }


class AutonomousQualityGatePolicy:
    """
    Enforces quality gates before an agent is permitted to conclude.
    Guarantees that all unit tests, linters, and verification commands pass.
    """

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()

    def evaluate_gates(
        self,
        gate_commands: list[str],
        timeout_seconds: int = 30,
    ) -> QualityGateVerdict:
        """Run each quality gate command and assess pass/fail status."""
        if not gate_commands:
            return QualityGateVerdict(passed=True, total_gates=0, passed_count=0)

        failures: list[QualityGateFailure] = []
        passed_count = 0

        for idx, cmd in enumerate(gate_commands, start=1):
            try:
                res = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=str(self.workspace_root),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=timeout_seconds,
                )
                if res.returncode == 0:
                    passed_count += 1
                else:
                    output = (res.stderr or res.stdout).strip()[:300]
                    failures.append(QualityGateFailure(
                        command=cmd,
                        attempt=1,
                        exit_code=res.returncode,
                        output_snippet=output,
                    ))
            except Exception as e:
                failures.append(QualityGateFailure(
                    command=cmd,
                    attempt=1,
                    exit_code=-1,
                    output_snippet=str(e),
                ))

        all_passed = len(failures) == 0

        continuation = ""
        if not all_passed:
            fail_summary = "\n".join(f"- Gate '{f.command}' failed (exit {f.exit_code}): {f.output_snippet}" for f in failures)
            continuation = (
                f"{DEFAULT_AUTONOMOUS_CONTINUATION_DIRECTIVE}\n\n"
                f"Failing Quality Gates:\n{fail_summary}\n\n"
                "Action Required: Diagnose the failure, modify the source code, and ensure all gates pass."
            )

        return QualityGateVerdict(
            passed=all_passed,
            total_gates=len(gate_commands),
            passed_count=passed_count,
            failures=failures,
            continuation_directive=continuation,
        )
