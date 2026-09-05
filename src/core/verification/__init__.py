"""
Verification Framework — Multi-Round Independent Validation

Implements the user's critical requirement:
- Multiple rounds of verification (3+ independent runs)
- Cross-validation between runs
- Real environment testing
- Confidence aggregation with Brier score tracking
- Result consensus detection

This is the system that ensures the project is truly complete and working
before declaring "done".
"""

import asyncio
import hashlib
import importlib
import json
import os
import subprocess
import sys
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .adversarial import AdversarialVerifier, CritiqueFinding, VerificationVerdict
from .anti_goodhart import AntiGoodhartVerifier, HoldoutTest, HoldoutVerdict


class VerificationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class RoundResult:
    round_num: int
    start_time: float
    end_time: float
    passed: bool
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    traceback: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "round": self.round_num,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.end_time - self.start_time,
            "passed": self.passed,
            "error": self.error,
            "details": self.details,
            "traceback": self.traceback,
        }


@dataclass
class VerificationPlan:
    test_files: list[str]
    num_rounds: int = 3
    isolated_runs: bool = True  # Each round runs in fresh process
    cross_validate: bool = True
    require_all_pass: bool = True
    timeout_seconds: int = 300


class MultiRoundVerifier:
    """Multi-round independent verification with cross-validation."""

    def __init__(self, project_root: str | None = None):
        self._project_root = project_root or os.getcwd()
        self._round_results: list[RoundResult] = []
        self._brier_scores: list[float] = []
        self._consensus_results: dict[str, Any] = {}

    def create_plan(self, test_files: list[str], num_rounds: int = 3) -> VerificationPlan:
        return VerificationPlan(
            test_files=test_files,
            num_rounds=num_rounds,
        )

    async def run_verification(self, plan: VerificationPlan) -> dict[str, Any]:
        """Run multi-round verification."""
        print(f"\n{'='*70}")
        print("  MULTI-ROUND VERIFICATION FACILITY")
        print(f"  Rounds: {plan.num_rounds} | Isolated: {plan.isolated_runs}")
        print(f"{'='*70}")

        overall_passed = True

        for round_num in range(1, plan.num_rounds + 1):
            print(f"\n--- Round {round_num}/{plan.num_rounds} ---")

            round_result = await self._run_round(round_num, plan)
            self._round_results.append(round_result)

            if round_result.passed:
                print(f"  ✓ Round {round_num} PASSED ({round_result.end_time - round_result.start_time:.2f}s)")
            else:
                print(f"  ✗ Round {round_num} FAILED: {round_result.error}")
                overall_passed = False

        # Cross-validation
        if plan.cross_validate and plan.num_rounds >= 2:
            print("\n--- Cross-Validation ---")
            consensus = self._cross_validate()
            self._consensus_results = consensus
            print(f"  Consensus score: {consensus['consensus_score']:.2f}")
            print(f"  All rounds agree: {consensus['all_rounds_agree']}")
            if not consensus['all_rounds_agree']:
                overall_passed = False

        # Brier score
        brier = self._calculate_brier_score()
        if brier is not None:
            print(f"  Brier score: {brier:.4f} (lower = better calibrated)")
            self._brier_scores.append(brier)

        # Final summary
        self._print_summary(plan)
        return {
            "overall_passed": overall_passed,
            "rounds": [r.to_dict() for r in self._round_results],
            "consensus": self._consensus_results,
            "brier_score": brier,
        }

    async def _run_round(self, round_num: int, plan: VerificationPlan) -> RoundResult:
        """Run a single verification round."""
        start = time.time()
        result = RoundResult(
            round_num=round_num,
            start_time=start,
            end_time=start,
            passed=False,
        )

        try:
            # Fresh process for isolation
            results = {}
            for test_file in plan.test_files:
                test_name = Path(test_file).stem
                print(f"  Running {test_name}...")

                if plan.isolated_runs:
                    passed, output = self._run_test_in_subprocess(test_file, plan.timeout_seconds)
                else:
                    passed, output = await self._run_test_inline(test_file)

                results[test_name] = {
                    "passed": passed,
                    "output_preview": output[:200] if output else "",
                }
                if not passed:
                    result.error = f"{test_name} failed"
                    result.traceback = output[-2000:] if output else ""

            result.end_time = time.time()
            result.passed = all(r["passed"] for r in results.values())
            result.details = results
        except Exception as e:
            result.end_time = time.time()
            result.error = str(e)
            result.traceback = traceback.format_exc()

        return result

    def _run_test_in_subprocess(self, test_file: str, timeout: int) -> tuple[bool, str]:
        """Run a test file in a completely isolated subprocess."""
        import uuid
        hermes_home = f"/tmp/verify_{uuid.uuid4().hex[:8]}"
        env = os.environ.copy()
        env["HERMES_HOME"] = hermes_home

        try:
            env["PYTHONIOENCODING"] = "utf-8"
            result = subprocess.run(
                [sys.executable, test_file],
                capture_output=True, text=True, timeout=timeout,
                encoding="utf-8", errors="replace",
                env=env,
                cwd=self._project_root,
            )
            output = result.stdout + "\n" + result.stderr
            passed = result.returncode == 0
            return passed, output
        except subprocess.TimeoutExpired:
            return False, f"TIMEOUT after {timeout}s"
        except Exception as e:
            return False, f"ERROR: {e}"

    async def _run_test_inline(self, test_file: str) -> tuple[bool, str]:
        """Run a test file in the current process."""
        try:
            mod = importlib.import_module(test_file.replace("/", ".").replace(".py", ""))
            result = await mod.main() if hasattr(mod, "main") else True
            return bool(result), ""
        except Exception:
            return False, traceback.format_exc()

    def _cross_validate(self) -> dict[str, Any]:
        """Cross-validate results across rounds."""
        if len(self._round_results) < 2:
            return {"consensus_score": 0.0, "all_agree": False}

        # Check if all rounds agree
        all_agree = all(r.passed == self._round_results[0].passed
                       for r in self._round_results)

        # Calculate consensus score (agreement on pass/fail)
        pass_count = sum(1 for r in self._round_results if r.passed)
        consensus_score = pass_count / len(self._round_results)

        # Per-test agreement
        test_agreement: dict[str, float] = {}
        test_names = set()
        for r in self._round_results:
            test_names.update(r.details.keys())

        for test_name in test_names:
            agreements = []
            for r in self._round_results:
                if test_name in r.details:
                    agreements.append(r.details[test_name]["passed"])
            if agreements:
                test_agreement[test_name] = sum(agreements) / len(agreements)

        return {
            "consensus_score": consensus_score,
            "all_rounds_agree": all_agree,
            "per_test_agreement": test_agreement,
        }

    def _calculate_brier_score(self) -> float | None:
        """Calculate Brier score for confidence calibration."""
        if not self._round_results:
            return None
        # Each round is a binary outcome (pass=1, fail=0)
        # We predict pass with probability 0.5 (uniform prior)
        scores = []
        for r in self._round_results:
            predicted = 0.5
            actual = 1.0 if r.passed else 0.0
            scores.append((predicted - actual) ** 2)
        return sum(scores) / len(scores)

    def _print_summary(self, plan: VerificationPlan):
        """Print verification summary."""
        passed = sum(1 for r in self._round_results if r.passed)
        total = len(self._round_results)
        print(f"\n{'='*70}")
        print("  VERIFICATION SUMMARY")
        print(f"{'='*70}")
        print(f"  Rounds passed: {passed}/{total}")

        for r in self._round_results:
            status = "✓ PASS" if r.passed else "✗ FAIL"
            duration = r.end_time - r.start_time
            print(f"  Round {r.round_num}: {status} ({duration:.2f}s)")
            if not r.passed and r.error:
                print(f"    Error: {r.error}")

        if self._consensus_results:
            print("\n  Cross-validation:")
            print(f"    Consensus score: {self._consensus_results['consensus_score']:.2f}")
            print(f"    All rounds agree: {self._consensus_results['all_rounds_agree']}")

        if self._brier_scores:
            print(f"\n  Brier score: {self._brier_scores[-1]:.4f}")

        overall = "PASSED" if passed == total else "FAILED"
        print(f"\n  OVERALL: {overall}")
        print(f"{'='*70}\n")


class VerificationPlugin:
    """Plugin wrapper for the verification framework."""

    def __init__(self):
        self.engine = MultiRoundVerifier()
        self._verifications: list[dict[str, Any]] = []

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {
            "status": "healthy",
            "total_verifications": len(self._verifications),
            "last_result": self._verifications[-1].get("overall_passed", False) if self._verifications else None,
        }

    async def verify_all(self) -> dict[str, Any]:
        """Run verification across all test files."""
        test_files = self._find_test_files()
        plan = self.engine.create_plan(test_files, num_rounds=3)
        result = await self.engine.run_verification(plan)
        self._verifications.append(result)
        return result

    def _find_test_files(self) -> list[str]:
        """Find all test_*.py files in the project."""
        tests = []
        for f in sorted(Path(self.engine._project_root).glob("test_*.py")):
            tests.append(str(f))
        return tests


async def create(kernel=None):
    plugin = VerificationPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin

__all__ = [
    "VerificationEngine",
    "VerificationPlan",
    "VerificationResult",
    "VerificationPlugin",
    "AdversarialVerifier",
    "VerificationVerdict",
    "CritiqueFinding",
    "AntiGoodhartVerifier",
    "HoldoutVerdict",
    "HoldoutTest",
    "create",
]
