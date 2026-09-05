"""
Adversarial Verification Engine — Fable-5 / Apodex Pattern
===========================================================
Actively tries to REFUTE completed work rather than just verify it.
Catches: fake completion, hallucinated tests, scope creep, weakened assertions.
"""

from __future__ import annotations

import asyncio
import ast
import hashlib
import json
import logging
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class VerificationVerdict(str, Enum):
    """Final verdict from adversarial verification."""
    VERIFIED = "VERIFIED"       # All checks pass, work is solid
    CAVEATS = "CAVEATS"         # Passes but with documented concerns
    REFUTED = "REFUTED"         # Active evidence against claimed completion


@dataclass
class VerificationFinding:
    """A single finding from adversarial verification."""
    severity: str  # "critical" | "major" | "minor" | "info"
    category: str  # "weakened_test" | "scope_creep" | "fake_completion" | "hallucinated_check" | "untested_path"
    title: str
    description: str
    evidence: dict
    file_path: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class AdversarialReport:
    """Complete adversarial verification report."""
    verdict: VerificationVerdict
    findings: list[VerificationFinding] = field(default_factory=list)
    re_run_results: dict = field(default_factory=dict)
    diff_analysis: dict = field(default_factory=dict)
    checked_claims: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    proof_hash: str = ""

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict.value,
            "findings": [
                {
                    "severity": f.severity,
                    "category": f.category,
                    "title": f.title,
                    "description": f.description,
                    "evidence": f.evidence,
                    "file_path": f.file_path,
                    "line_number": f.line_number,
                }
                for f in self.findings
            ],
            "re_run_results": self.re_run_results,
            "diff_analysis": self.diff_analysis,
            "checked_claims": self.checked_claims,
            "timestamp": self.timestamp,
            "proof_hash": self.proof_hash,
        }

    def summary(self) -> str:
        critical = sum(1 for f in self.findings if f.severity == "critical")
        major = sum(1 for f in self.findings if f.severity == "major")
        minor = sum(1 for f in self.findings if f.severity == "minor")
        return f"{self.verdict.value} | Critical: {critical}, Major: {major}, Minor: {minor}"


class AdversarialVerifier:
    """
    Adversarial Verifier — actively tries to refute work.

    Four verification pillars:
    1. RE-RUN: Execute every claimed test/check independently
    2. DIFF: Compare actual changes vs claimed changes
    3. HUNT: Search for weakened tests (assert True, mock-only, tautologies)
    4. SCOPE: Detect scope creep (did more/less than required)
    """

    def __init__(
        self,
        workspace_root: Path,
        timeout_per_check: int = 120,
        max_parallel: int = 4,
    ):
        self.workspace_root = Path(workspace_root).resolve()
        self.timeout_per_check = timeout_per_check
        self.max_parallel = max_parallel
        self._trap_fixtures: dict[str, dict] = {}

    async def verify(self, work_package: "WorkPackage") -> AdversarialReport:
        """
        Main entry point: verify a completed work package adversarially.

        Args:
            work_package: Contains task, claimed changes, test commands, proof artifacts

        Returns:
            AdversarialReport with VERIFIED | CAVEATS | REFUTED verdict
        """
        logger.info(f"Starting adversarial verification for: {work_package.task_id}")

        report = AdversarialReport(verdict=VerificationVerdict.VERIFIED)

        # Pillar 1: Re-run every claimed check
        await self._pillar_rerun_checks(work_package, report)

        # Pillar 2: Diff actual vs claimed changes
        await self._pillar_diff_analysis(work_package, report)

        # Pillar 3: Hunt for weakened tests
        await self._pillar_hunt_weakened_tests(work_package, report)

        # Pillar 4: Scope verification
        await self._pillar_scope_verification(work_package, report)

        # Determine final verdict
        self._determine_verdict(report)

        # Generate cryptographic proof hash
        report.proof_hash = self._compute_proof_hash(report)

        logger.info(f"Adversarial verification complete: {report.summary()}")
        return report

    async def _pillar_rerun_checks(self, wp: "WorkPackage", report: AdversarialReport) -> None:
        """Pillar 1: Independently re-run every claimed test/check."""
        logger.debug("Pillar 1: Re-running claimed checks")

        checks = wp.get_claimed_checks()  # List of {name, command, expected_result}
        if not checks:
            report.findings.append(VerificationFinding(
                severity="major",
                category="hallucinated_check",
                title="No verifiable checks claimed",
                description="Work package claims completion but provides no runnable verification commands",
                evidence={"claimed_checks": []}
            ))
            return

        semaphore = asyncio.Semaphore(self.max_parallel)

        async def run_check(check: dict) -> dict:
            async with semaphore:
                cmd = check.get("command")
                if not cmd:
                    return {"name": check.get("name", "unnamed"), "status": "no_command", "error": "Missing command"}

                try:
                    proc = await asyncio.wait_for(
                        asyncio.create_subprocess_shell(
                            cmd,
                            cwd=self.workspace_root,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        ),
                        timeout=self.timeout_per_check,
                    )
                    stdout, stderr = await proc.communicate()
                    return {
                        "name": check.get("name", "unnamed"),
                        "status": "passed" if proc.returncode == 0 else "failed",
                        "returncode": proc.returncode,
                        "stdout": stdout.decode()[:5000],
                        "stderr": stderr.decode()[:5000],
                    }
                except asyncio.TimeoutError:
                    return {"name": check.get("name", "unnamed"), "status": "timeout", "error": f"Exceeded {self.timeout_per_check}s"}
                except Exception as e:
                    return {"name": check.get("name", "unnamed"), "status": "error", "error": str(e)}

        results = await asyncio.gather(*[run_check(c) for c in checks])
        report.re_run_results = {r["name"]: r for r in results}

        # Check for failures
        failed = [r for r in results if r["status"] != "passed"]
        if failed:
            report.findings.append(VerificationFinding(
                severity="critical",
                category="fake_completion",
                title=f"{len(failed)} claimed check(s) failed on independent re-run",
                description="Work claims completion but verification commands fail when run independently",
                evidence={"failed_checks": failed}
            ))

        report.checked_claims = [c.get("name", "unnamed") for c in checks]

    async def _pillar_diff_analysis(self, wp: "WorkPackage", report: AdversarialReport) -> None:
        """Pillar 2: Diff actual changes vs claimed changes."""
        logger.debug("Pillar 2: Diff analysis")

        claimed_files = wp.get_claimed_file_changes()  # List of {path, claimed_change_type}
        if not claimed_files:
            return

        try:
            # Get actual git diff
            proc = await asyncio.create_subprocess_shell(
                "git diff --name-status HEAD~1..HEAD",
                cwd=self.workspace_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            actual_changes = stdout.decode().strip().split("\n") if stdout.decode().strip() else []

            # Parse actual changes
            actual_files = {}
            for line in actual_changes:
                if "\t" in line:
                    status, path = line.split("\t", 1)
                    actual_files[path] = status

            # Compare
            claimed_paths = {f["path"] for f in claimed_files}
            actual_paths = set(actual_files.keys())

            missing_from_claims = actual_paths - claimed_paths
            missing_from_actual = claimed_paths - actual_paths

            report.diff_analysis = {
                "claimed_files": list(claimed_paths),
                "actual_files": list(actual_paths),
                "actual_change_types": actual_files,
                "unclaimed_changes": list(missing_from_claims),
                "claimed_but_missing": list(missing_from_actual),
            }

            if missing_from_claims:
                report.findings.append(VerificationFinding(
                    severity="major",
                    category="scope_creep",
                    title=f"Unclaimed changes detected: {len(missing_from_claims)} file(s)",
                    description="Actual git changes include files not mentioned in work package claims",
                    evidence={"unclaimed_files": list(missing_from_claims)}
                ))

            if missing_from_actual:
                report.findings.append(VerificationFinding(
                    severity="major",
                    category="fake_completion",
                    title=f"Claimed changes not found in git: {len(missing_from_actual)} file(s)",
                    description="Work package claims changes to files that don't appear in git diff",
                    evidence={"missing_files": list(missing_from_actual)}
                ))

        except Exception as e:
            logger.warning(f"Diff analysis failed: {e}")
            report.diff_analysis = {"error": str(e)}

    async def _pillar_hunt_weakened_tests(self, wp: "WorkPackage", report: AdversarialReport) -> None:
        """Pillar 3: Hunt for weakened tests (assert True, mock-only, tautologies)."""
        logger.debug("Pillar 3: Hunting weakened tests")

        test_files = list(self.workspace_root.rglob("test_*.py")) + list(self.workspace_root.rglob("*_test.py"))
        weakened_patterns = []

        for test_file in test_files:
            try:
                content = test_file.read_text(encoding="utf-8")
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    # Check for assert True / assert False patterns
                    if isinstance(node, ast.Assert):
                        if isinstance(node.test, ast.Constant) and node.test.value is True:
                            weakened_patterns.append({
                                "file": str(test_file.relative_to(self.workspace_root)),
                                "line": node.lineno,
                                "pattern": "assert True",
                                "code": ast.get_source_segment(content, node) or "assert True",
                            })
                        elif isinstance(node.test, ast.Constant) and node.test.value is False:
                            weakened_patterns.append({
                                "file": str(test_file.relative_to(self.workspace_root)),
                                "line": node.lineno,
                                "pattern": "assert False",
                                "code": ast.get_source_segment(content, node) or "assert False",
                            })

                    # Check for mock-only tests (patch without real assertion)
                    if isinstance(node, ast.With):
                        for item in node.items:
                            if isinstance(item.context_expr, ast.Call):
                                if hasattr(item.context_expr.func, 'attr') and 'patch' in str(item.context_expr.func.attr):
                                    # Check if there's any real assertion in the body
                                    has_real_assert = any(
                                        isinstance(n, ast.Assert) and not (
                                            isinstance(n.test, ast.Constant) and n.test.value is True
                                        )
                                        for n in ast.walk(node)
                                    )
                                    if not has_real_assert:
                                        weakened_patterns.append({
                                            "file": str(test_file.relative_to(self.workspace_root)),
                                            "line": node.lineno,
                                            "pattern": "mock_only_test",
                                            "code": "with patch(...) block with no real assertions",
                                        })

                    # Check for tautological assertions (x == x, True == True)
                    if isinstance(node, ast.Assert) and isinstance(node.test, ast.Compare):
                        if (isinstance(node.test.left, ast.Name) and
                            isinstance(node.test.comparators[0], ast.Name) and
                            node.test.left.id == node.test.comparators[0].id and
                            len(node.test.ops) == 1 and
                            isinstance(node.test.ops[0], ast.Eq)):
                            weakened_patterns.append({
                                "file": str(test_file.relative_to(self.workspace_root)),
                                "line": node.lineno,
                                "pattern": "tautology",
                                "code": f"{node.test.left.id} == {node.test.comparators[0].id}",
                            })

            except Exception:
                continue  # Skip unparsable files

        if weakened_patterns:
            report.findings.append(VerificationFinding(
                severity="critical",
                category="weakened_test",
                title=f"Found {len(weakened_patterns)} weakened test pattern(s)",
                description="Tests contain assertions that cannot fail (assert True, tautologies, mock-only)",
                evidence={"patterns": weakened_patterns[:20]}  # Limit for report size
            ))

    async def _pillar_scope_verification(self, wp: "WorkPackage", report: AdversarialReport) -> None:
        """Pillar 4: Verify work matches declared scope (no creep, no gaps)."""
        logger.debug("Pillar 4: Scope verification")

        declared_scope = wp.get_declared_scope()  # List of required deliverables
        if not declared_scope:
            return

        # Check each declared deliverable has evidence
        missing_deliverables = []
        for deliverable in declared_scope:
            evidence = wp.get_evidence_for(deliverable)
            if not evidence:
                missing_deliverables.append(deliverable)

        if missing_deliverables:
            report.findings.append(VerificationFinding(
                severity="major",
                category="scope_creep",
                title=f"Missing evidence for {len(missing_deliverables)} declared deliverable(s)",
                description="Work package declares deliverables but provides no evidence of completion",
                evidence={"missing_deliverables": missing_deliverables}
            ))

        # Check for undeclared work (scope creep)
        actual_deliverables = wp.get_actual_deliverables()
        undeclared = [d for d in actual_deliverables if d not in declared_scope]
        if undeclared:
            report.findings.append(VerificationFinding(
                severity="minor",
                category="scope_creep",
                title=f"Undeclared work detected: {len(undeclared)} item(s)",
                description="Work includes deliverables not in original scope declaration",
                evidence={"undeclared_work": undeclared}
            ))

    def _determine_verdict(self, report: AdversarialReport) -> None:
        """Determine final verdict based on findings."""
        critical = sum(1 for f in report.findings if f.severity == "critical")
        major = sum(1 for f in report.findings if f.severity == "major")

        if critical > 0:
            report.verdict = VerificationVerdict.REFUTED
        elif major > 0:
            report.verdict = VerificationVerdict.CAVEATS
        else:
            report.verdict = VerificationVerdict.VERIFIED

    def _compute_proof_hash(self, report: AdversarialReport) -> str:
        """Compute cryptographic hash of the verification report."""
        content = json.dumps(report.to_dict(), sort_keys=True).encode()
        return hashlib.sha256(content).hexdigest()[:32]

    # Trap fixture support (Fable-5 pattern)
    def register_trap_fixture(self, name: str, fixture: dict) -> None:
        """Register a trap fixture for regression testing."""
        self._trap_fixtures[name] = fixture

    async def run_trap_suite(self) -> dict:
        """Run all registered trap fixtures."""
        results = {}
        for name, fixture in self._trap_fixtures.items():
            try:
                # Execute the trap scenario
                if "command" in fixture:
                    proc = await asyncio.create_subprocess_shell(
                        fixture["command"],
                        cwd=self.workspace_root,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await proc.communicate()
                    passed = proc.returncode == fixture.get("expected_returncode", 0)
                else:
                    passed = False

                results[name] = {"passed": passed, "fixture": fixture}
            except Exception as e:
                results[name] = {"passed": False, "error": str(e)}

        return results


# WorkPackage interface (to be implemented by caller)
class WorkPackage:
    """
    Interface for work packages to be verified.
    Implement this in your harness to provide verification data.
    """

    def __init__(self, task_id: str, task_description: str):
        self.task_id = task_id
        self.task_description = task_description
        self._claimed_checks: list[dict] = []
        self._claimed_file_changes: list[dict] = []
        self._declared_scope: list[str] = []
        self._evidence: dict[str, Any] = {}
        self._actual_deliverables: list[str] = []

    def add_claimed_check(self, name: str, command: str, expected_result: str = "pass") -> None:
        self._claimed_checks.append({"name": name, "command": command, "expected": expected_result})

    def add_claimed_file_change(self, path: str, change_type: str) -> None:
        self._claimed_file_changes.append({"path": path, "type": change_type})

    def add_declared_scope(self, deliverable: str) -> None:
        self._declared_scope.append(deliverable)

    def add_evidence(self, deliverable: str, evidence: Any) -> None:
        self._evidence[deliverable] = evidence

    def add_actual_deliverable(self, deliverable: str) -> None:
        self._actual_deliverables.append(deliverable)

    def get_claimed_checks(self) -> list[dict]:
        return self._claimed_checks

    def get_claimed_file_changes(self) -> list[dict]:
        return self._claimed_file_changes

    def get_declared_scope(self) -> list[str]:
        return self._declared_scope

    def get_evidence_for(self, deliverable: str) -> Any:
        return self._evidence.get(deliverable)

    def get_actual_deliverables(self) -> list[str]:
        return self._actual_deliverables


# Convenience function for CLI integration
async def verify_work_package(
    task_id: str,
    task_description: str,
    claimed_checks: list[dict],
    claimed_file_changes: list[dict],
    declared_scope: list[str],
    evidence: dict,
    workspace_root: Path = Path("."),
) -> AdversarialReport:
    """Convenience function for standalone verification."""
    wp = WorkPackage(task_id, task_description)
    for c in claimed_checks:
        wp.add_claimed_check(c["name"], c["command"], c.get("expected", "pass"))
    for f in claimed_file_changes:
        wp.add_claimed_file_change(f["path"], f["type"])
    for d in declared_scope:
        wp.add_declared_scope(d)
    for k, v in evidence.items():
        wp.add_evidence(k, v)

    verifier = AdversarialVerifier(workspace_root)
    return await verifier.verify(wp)


if __name__ == "__main__":
    # Demo / self-test
    async def demo():
        wp = WorkPackage("demo-1", "Implement add function")
        wp.add_claimed_check("test_add", "python -c \"assert add(2,3)==5\"")
        wp.add_claimed_file_change("math.py", "create")
        wp.add_declared_scope("add function")
        wp.add_evidence("add function", {"file": "math.py", "tests_passed": True})
        wp.add_actual_deliverable("add function")

        verifier = AdversarialVerifier(Path("."))
        report = await verifier.verify(wp)
        print(json.dumps(report.to_dict(), indent=2))

    asyncio.run(demo())