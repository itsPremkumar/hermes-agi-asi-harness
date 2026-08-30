"""Verification Orchestrator — coordinates all verification activities."""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from typing import Any, Optional

from verification.proof_checker import ProofChecker, Proof, ProofStep, ProofStatus, CheckResult
from verification.specification_parser import SpecificationParser, Specification, SpecFormat, ParseResult
from verification.formal_verifier import FormalVerifier, VerifyStatus, VerificationResult
from verification.counterexample_generator import CounterexampleGenerator, Counterexample


class VerificationOrchestrator:
    """Coordinates all verification activities."""

    def __init__(self):
        self._lock = threading.RLock()
        self._proof_checker = ProofChecker()
        self._spec_parser = SpecificationParser()
        self._verifier = FormalVerifier()
        self._cex_generator = CounterexampleGenerator()
        self._history: list[dict[str, Any]] = []

    def verify_specification(self, spec_id: str) -> dict[str, Any]:
        """Verify a specification: parse, check proofs, generate counterexamples."""
        with self._lock:
            start = time.time()
            result = {"spec_id": spec_id, "steps": []}

            # Get specification
            spec = self._spec_parser.get(spec_id)
            if not spec:
                result["error"] = f"Specification not found: {spec_id}"
                return result

            # Verify invariants
            for invariant in spec.invariants:
                inv_result = self._verifier.verify_invariant(spec_id, invariant, {})
                result["steps"].append({
                    "type": "invariant",
                    "expression": invariant,
                    "status": inv_result.status.value,
                })

                # Generate counterexample if falsified
                if inv_result.status == VerifyStatus.FALSIFIED:
                    cexes = self._cex_generator.generate(
                        invariant,
                        spec.variables,
                        {f"{v}_domain": [0, 1, -1, 10, -10] for v in spec.variables},
                    )
                    result["steps"][-1]["counterexamples"] = [c.values for c in cexes]

            result["duration_ms"] = (time.time() - start) * 1000
            self._history.append(result)
            return result

    def check_proof(self, proof_id: str) -> CheckResult:
        """Check a proof."""
        return self._proof_checker.check(proof_id)

    def parse_specification(self, content: str, format: SpecFormat, spec_id: str = "", name: str = "") -> ParseResult:
        """Parse and register a specification."""
        result = self._spec_parser.parse(content, format, spec_id, name)
        return result

    def verify_proof(self, proof: Proof) -> dict[str, Any]:
        """Register and verify a proof."""
        self._proof_checker.register(proof)
        check_result = self._proof_checker.check(proof.id)
        return {
            "proof_id": proof.id,
            "status": check_result.status.value,
            "errors": check_result.errors,
            "warnings": check_result.warnings,
        }

    def get_history(self) -> list[dict[str, Any]]:
        return list(self._history)

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "specifications": len(self._spec_parser.list_specs()),
                "proofs": len(self._proof_checker.list_proofs()),
                "counterexamples": self._cex_generator.count(),
                "verification_history": len(self._history),
            }


__all__ = ["VerificationOrchestrator"]
