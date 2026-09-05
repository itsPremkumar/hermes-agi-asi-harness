"""Delegate Task Concurrency Diagnostic Tool.

Detects which of the 3 cap paths is affecting delegate_task concurrency.
Reference: hermes-agent/references/delegate-task-concurrency-diagnosis.md
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class CapType(str, Enum):
    NONE = "none"
    PER_CALL_REJECT = "per_call_reject"
    PER_TURN_TRUNCATOR = "per_turn_truncator"
    COST_WARNING = "cost_warning"
    MODEL_SELF_LIMIT = "model_self_limit"


@dataclass
class DiagnosticResult:
    """Result of a diagnostic check."""
    cap_type: CapType
    detected: bool
    message: str
    suggestion: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DiagnosticReport:
    """Complete diagnostic report."""
    profile: str
    config_path: str
    max_concurrent_children: int | None
    env_var_value: str | None
    running_processes: list[dict[str, str]]
    log_path: str | None
    cap_paths_detected: list[DiagnosticResult]
    summary: str
    recommendations: list[str]


class DelegateTaskDiagnostic:
    """Diagnose delegate_task concurrency caps."""

    def __init__(self, profile: str | None = None, hermes_home: str | None = None):
        self.profile = profile or os.environ.get("HERMES_PROFILE", "default")
        self.hermes_home = Path(hermes_home or os.environ.get("HERMES_HOME", "~/.hermes")).expanduser()
        self.config_path = self.hermes_home / "profiles" / self.profile / "config.yaml"
        self.log_path = self.hermes_home / "logs" / "agent.log"

    def run(self) -> DiagnosticReport:
        """Run all diagnostics and return a report."""
        running = self._get_running_processes()
        max_children = self._get_max_concurrent_children()
        env_var = os.environ.get("DELEGATION_MAX_CONCURRENT_CHILDREN")

        cap_results: list[DiagnosticResult] = []

        # Check cap path 1: per-call reject
        cap_results.append(self._check_per_call_reject(max_children))

        # Check cap path 2: per-turn truncator
        cap_results.append(self._check_per_turn_truncator())

        # Check cap path 3: cost warning
        cap_results.append(self._check_cost_warning(max_children))

        # Check if model self-limit is the likely cause
        cap_results.append(self._check_model_self_limit(max_children, cap_results))

        # Build recommendations
        recommendations = self._build_recommendations(cap_results, max_children)

        # Build summary
        summary = self._build_summary(cap_results, max_children)

        return DiagnosticReport(
            profile=self.profile,
            config_path=str(self.config_path),
            max_concurrent_children=max_children,
            env_var_value=env_var,
            running_processes=running,
            log_path=str(self.log_path) if self.log_path.exists() else None,
            cap_paths_detected=cap_results,
            summary=summary,
            recommendations=recommendations,
        )

    def _get_running_processes(self) -> list[dict[str, str]]:
        """Get running Hermes agent processes."""
        processes = []
        try:
            result = subprocess.run(
                ["ps", "aux"] if sys.platform != "win32" else ["tasklist", "/FO", "CSV"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if "hermes" in line.lower() or "agent" in line.lower():
                        parts = line.split()
                        if len(parts) >= 2:
                            processes.append({
                                "pid": parts[1] if sys.platform != "win32" else parts[0],
                                "command": " ".join(parts[-3:]) if sys.platform != "win32" else line,
                            })
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return processes

    def _get_max_concurrent_children(self) -> int | None:
        """Read max_concurrent_children from config.yaml."""
        if not self.config_path.exists():
            return None
        try:
            import yaml
            with open(self.config_path) as f:
                config = yaml.safe_load(f)
            delegation = config.get("delegation", {})
            return delegation.get("max_concurrent_children", 3)
        except Exception:
            return None

    def _check_per_call_reject(self, max_children: int | None) -> DiagnosticResult:
        """Check for per-call hard reject errors."""
        if not self.log_path.exists():
            return DiagnosticResult(
                cap_type=CapType.PER_CALL_REJECT,
                detected=False,
                message="No agent log found to check for per-call rejects.",
            )

        try:
            with open(self.log_path) as f:
                log_content = f.read()
            matches = re.findall(r"Too many tasks: (\d+) provided, but max_concurrent_children is (\d+)", log_content)
            if matches:
                last_n, last_max = matches[-1]
                return DiagnosticResult(
                    cap_type=CapType.PER_CALL_REJECT,
                    detected=True,
                    message=f"Per-call reject detected: {last_n} tasks provided, max is {last_max}.",
                    suggestion=f"Reduce tasks per call to ≤ {last_max}, or increase max_concurrent_children in config.yaml.",
                    details={"tasks_provided": int(last_n), "max_allowed": int(last_max)},
                )
        except Exception:
            pass

        return DiagnosticResult(
            cap_type=CapType.PER_CALL_REJECT,
            detected=False,
            message="No per-call rejects found in logs.",
        )

    def _check_per_turn_truncator(self) -> DiagnosticResult:
        """Check for per-turn truncator warnings."""
        if not self.log_path.exists():
            return DiagnosticResult(
                cap_type=CapType.PER_TURN_TRUNCATOR,
                detected=False,
                message="No agent log found to check for per-turn truncation.",
            )

        try:
            with open(self.log_path) as f:
                log_content = f.read()
            matches = re.findall(r"Truncated (\d+) excess delegate_task call\(s\) to enforce max_concurrent_children=(\d+) limit", log_content)
            if matches:
                last_excess, last_max = matches[-1]
                return DiagnosticResult(
                    cap_type=CapType.PER_TURN_TRUNCATOR,
                    detected=True,
                    message=f"Per-turn truncator detected: {last_excess} calls truncated, max is {last_max}.",
                    suggestion="Send all tasks in a single delegate_task call instead of multiple calls per turn.",
                    details={"truncated_calls": int(last_excess), "max_allowed": int(last_max)},
                )
        except Exception:
            pass

        return DiagnosticResult(
            cap_type=CapType.PER_TURN_TRUNCATOR,
            detected=False,
            message="No per-turn truncation found in logs.",
        )

    def _check_cost_warning(self, max_children: int | None) -> DiagnosticResult:
        """Check for cost-warning log lines."""
        if not self.log_path.exists():
            return DiagnosticResult(
                cap_type=CapType.COST_WARNING,
                detected=False,
                message="No agent log found to check for cost warnings.",
            )

        try:
            with open(self.log_path) as f:
                log_content = f.read()
            matches = re.findall(r"delegation\.max_concurrent_children=(\d+): each child consumes API tokens independently", log_content)
            if matches:
                last_val = matches[-1]
                return DiagnosticResult(
                    cap_type=CapType.COST_WARNING,
                    detected=True,
                    message=f"Cost warning detected: max_concurrent_children={last_val}. This is a WARNING only, not a cap.",
                    suggestion="This log line does not cap anything. It may cause the model to self-limit. Ignore or lower to ≤10.",
                    details={"value": int(last_val)},
                )
        except Exception:
            pass

        return DiagnosticResult(
            cap_type=CapType.COST_WARNING,
            detected=False,
            message="No cost warnings found in logs.",
        )

    def _check_model_self_limit(self, max_children: int | None, other_caps: list[DiagnosticResult]) -> DiagnosticResult:
        """Check if model self-limit is the likely cause."""
        any_cap_detected = any(c.detected and c.cap_type != CapType.COST_WARNING for c in other_caps)

        if any_cap_detected:
            return DiagnosticResult(
                cap_type=CapType.MODEL_SELF_LIMIT,
                detected=False,
                message="Another cap path is already active; model self-limit is not the primary cause.",
            )

        if max_children and max_children > 10:
            return DiagnosticResult(
                cap_type=CapType.MODEL_SELF_LIMIT,
                detected=True,
                message="No Hermes caps detected. The model is likely self-limiting (common with reasoning models).",
                suggestion="Tell the model explicitly: 'Send all N tasks in ONE delegate_task call with a tasks array of N items.'",
            )

        return DiagnosticResult(
            cap_type=CapType.MODEL_SELF_LIMIT,
            detected=False,
            message="No model self-limit indicators detected.",
        )

    def _build_recommendations(self, cap_results: list[DiagnosticResult], max_children: int | None) -> list[str]:
        """Build actionable recommendations."""
        recs = []

        for result in cap_results:
            if result.detected and result.suggestion:
                recs.append(f"[{result.cap_type.value}] {result.suggestion}")

        if max_children is None:
            recs.append("Set delegation.max_concurrent_children in config.yaml to your desired value.")
        elif max_children > 10:
            recs.append("Consider lowering max_concurrent_children to ≤10 to reduce cost-warning noise.")
        elif max_children < 3:
            recs.append(f"max_concurrent_children is only {max_children}. Increase it for better parallelism.")

        recs.append("Run 'hermes config get delegation.max_concurrent_children' to verify current value.")

        return recs

    def _build_summary(self, cap_results: list[DiagnosticResult], max_children: int | None) -> str:
        """Build a human-readable summary."""
        detected = [r for r in cap_results if r.detected]

        if not detected:
            return f"No caps detected. max_concurrent_children={max_children}. If tasks are still limited, the model is self-limiting."

        parts = [f"Detected {len(detected)} cap(s):"]
        for r in detected:
            parts.append(f"  - {r.cap_type.value}: {r.message}")

        return "\n".join(parts)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Diagnose delegate_task concurrency caps in Hermes Agent",
    )
    parser.add_argument("--profile", help="Hermes profile name (default: $HERMES_PROFILE or 'default')")
    parser.add_argument("--hermes-home", help="Path to .hermes directory (default: $HERMES_HOME or ~/.hermes)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    diagnostic = DelegateTaskDiagnostic(profile=args.profile, hermes_home=args.hermes_home)
    report = diagnostic.run()

    if args.json:
        import json
        print(json.dumps({
            "profile": report.profile,
            "config_path": report.config_path,
            "max_concurrent_children": report.max_concurrent_children,
            "env_var_value": report.env_var_value,
            "running_processes": report.running_processes,
            "log_path": report.log_path,
            "cap_paths": [
                {
                    "type": r.cap_type.value,
                    "detected": r.detected,
                    "message": r.message,
                    "suggestion": r.suggestion,
                    "details": r.details,
                }
                for r in report.cap_paths_detected
            ],
            "summary": report.summary,
            "recommendations": report.recommendations,
        }, indent=2))
    else:
        print("Delegate Task Concurrency Diagnostic Report")
        print(f"{'='*50}")
        print(f"Profile: {report.profile}")
        print(f"Config: {report.config_path}")
        print(f"max_concurrent_children: {report.max_concurrent_children}")
        print(f"DELEGATION_MAX_CONCURRENT_CHILDREN env: {report.env_var_value}")
        print(f"Log: {report.log_path}")
        print()
        print(report.summary)
        print()
        if report.recommendations:
            print("Recommendations:")
            for i, rec in enumerate(report.recommendations, 1):
                print(f"  {i}. {rec}")


if __name__ == "__main__":
    main()
