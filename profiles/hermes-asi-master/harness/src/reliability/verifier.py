#!/usr/bin/env python3
"""
verifier.py — Multi-Layer Reliability Verifier & Proof Gatekeeper
Enforces zero self-delusion and earned-completion verification.
"""

import os
import ast
import re
import pathlib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

@dataclass
class VerificationVerdict:
    passed: bool
    confidence: float
    checks: Dict[str, bool] = field(default_factory=dict)
    details: List[str] = field(default_factory=list)

class ReliabilityVerifier:
    SECRET_REGEX = re.compile(
        r"(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16})"
    )

    def verify_python_code(self, code_str: str) -> VerificationVerdict:
        checks = {}
        details = []

        # 1. AST Syntax validation
        try:
            tree = ast.parse(code_str)
            checks["ast_syntax"] = True
        except SyntaxError as e:
            checks["ast_syntax"] = False
            details.append(f"Syntax Error: {e}")

        # 2. Secret leakage detection
        if self.SECRET_REGEX.search(code_str):
            checks["zero_secrets"] = False
            details.append("Detected hardcoded API secret token in source code")
        else:
            checks["zero_secrets"] = True

        all_ok = all(checks.values())
        return VerificationVerdict(
            passed=all_ok,
            confidence=1.0 if all_ok else 0.0,
            checks=checks,
            details=details
        )

    def verify_directory(self, dir_path: pathlib.Path) -> VerificationVerdict:
        if not dir_path.is_dir():
            return VerificationVerdict(passed=False, confidence=0.0, details=["Directory does not exist"])

        checks = {"all_files_compile": True, "zero_secrets": True}
        details = []
        py_files = list(dir_path.glob("**/*.py"))

        for p in py_files:
            if "venv" in str(p) or "__pycache__" in str(p):
                continue
            text = p.read_text(encoding="utf-8")
            res = self.verify_python_code(text)
            if not res.passed:
                checks["all_files_compile"] = False
                details.extend([f"{p.name}: {d}" for d in res.details])

        all_ok = all(checks.values()) and len(py_files) > 0
        return VerificationVerdict(
            passed=all_ok,
            confidence=1.0 if all_ok else 0.0,
            checks=checks,
            details=details
        )

    def verify_earned_proofs(self, proofs: List[Dict[str, Any]]) -> VerificationVerdict:
        """Verifies proof checklist items (status == 'PASS')."""
        if not proofs:
            return VerificationVerdict(passed=False, confidence=0.0, details=["No proofs provided"])

        passed_count = sum(1 for p in proofs if p.get("status") == "PASS")
        total_count = len(proofs)
        is_complete = passed_count == total_count

        return VerificationVerdict(
            passed=is_complete,
            confidence=passed_count / total_count,
            checks={"proofs_passed": is_complete},
            details=[f"{p.get('id')}: {p.get('status')}" for p in proofs]
        )
