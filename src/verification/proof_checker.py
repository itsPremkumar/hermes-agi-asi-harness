"""Proof Checker — verify formal proofs and logical arguments."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ProofStatus(Enum):
    VALID = "valid"
    INVALID = "invalid"
    INCOMPLETE = "incomplete"
    ERROR = "error"


@dataclass
class ProofStep:
    """A single step in a proof."""
    step_number: int
    statement: str
    justification: str
    depends_on: list[int] = field(default_factory=list)


@dataclass
class Proof:
    """A formal proof consisting of steps."""
    id: str
    premises: list[str] = field(default_factory=list)
    conclusion: str = ""
    steps: list[ProofStep] = field(default_factory=list)
    status: ProofStatus = ProofStatus.INCOMPLETE


@dataclass
class CheckResult:
    """Result of a proof check."""
    proof_id: str
    status: ProofStatus
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    step_results: dict[int, str] = field(default_factory=dict)


class ProofChecker:
    """Check formal proofs for correctness."""

    def __init__(self):
        self._proofs: dict[str, Proof] = {}
        self._results: dict[str, CheckResult] = {}

    def register(self, proof: Proof) -> None:
        """Register a proof for checking."""
        self._proofs[proof.id] = proof

    def get(self, proof_id: str) -> Proof | None:
        """Get a registered proof."""
        return self._proofs.get(proof_id)

    def check(self, proof_id: str) -> CheckResult:
        """Check a proof for correctness."""
        proof = self._proofs.get(proof_id)
        if not proof:
            return CheckResult(
                proof_id=proof_id,
                status=ProofStatus.ERROR,
                errors=[f"Proof not found: {proof_id}"],
            )

        errors = []
        warnings = []
        step_results = {}

        # Check if proof has steps
        if not proof.steps:
            errors.append("Proof has no steps")
            result = CheckResult(
                proof_id=proof_id,
                status=ProofStatus.INCOMPLETE,
                errors=errors,
                warnings=warnings,
                step_results=step_results,
            )
            self._results[proof_id] = result
            proof.status = ProofStatus.INCOMPLETE
            return result

        # Check each step
        for step in proof.steps:
            # Check for circular dependencies
            if step.step_number in step.depends_on:
                errors.append(f"Step {step.step_number} depends on itself")
                step_results[step.step_number] = "ERROR"
                continue

            # Check that dependencies exist
            dep_ok = True
            for dep in step.depends_on:
                if dep not in [s.step_number for s in proof.steps]:
                    errors.append(f"Step {step.step_number} depends on missing step {dep}")
                    dep_ok = False
                    step_results[step.step_number] = "ERROR"

            if dep_ok:
                step_results[step.step_number] = "OK"

        status = ProofStatus.VALID if not errors else ProofStatus.INVALID
        result = CheckResult(
            proof_id=proof_id,
            status=status,
            errors=errors,
            warnings=warnings,
            step_results=step_results,
        )
        self._results[proof_id] = result
        proof.status = status
        return result

    def validate_syntax(self, statement: str) -> tuple[bool, list[str]]:
        """Validate the syntax of a logical statement."""
        errors = []
        warnings_list: list[str] = []

        # Check balanced parentheses
        depth = 0
        for char in statement:
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            if depth < 0:
                errors.append("Unbalanced parentheses")
                break
        if depth != 0:
            errors.append("Unbalanced parentheses")

        # Check for common logical operators
        valid_operators = ['and', 'or', 'not', 'implies', 'iff', 'forall', 'exists']
        has_operator = any(op in statement.lower() for op in valid_operators)

        if not has_operator and len(statement.split()) > 1:
            warnings_list.append("No logical operators found")

        return len(errors) == 0, errors

    def check_equivalence(self, stmt1: str, stmt2: str) -> bool:
        """Check if two statements are syntactically equivalent."""
        # Normalize: lowercase, strip whitespace
        norm1 = ' '.join(stmt1.lower().split())
        norm2 = ' '.join(stmt2.lower().split())
        return norm1 == norm2
