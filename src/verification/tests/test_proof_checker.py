"""Tests for proof_checker."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from verification.proof_checker import (
    ProofChecker, Proof, ProofStep, ProofStatus,
)


class TestProofStep:
    def test_create_step(self):
        step = ProofStep(step_number=1, statement="A", justification="premise")
        assert step.step_number == 1
        assert step.statement == "A"
        assert step.justification == "premise"
        assert step.depends_on == []


class TestProof:
    def test_create_proof(self):
        proof = Proof(id="p1", premises=["A"], conclusion="B")
        assert proof.id == "p1"
        assert proof.premises == ["A"]
        assert proof.conclusion == "B"
        assert proof.status == ProofStatus.INCOMPLETE


class TestProofChecker:
    def test_register(self):
        pc = ProofChecker()
        proof = Proof(id="p1")
        pc.register(proof)
        assert pc.get("p1") is proof

    def test_check_valid(self):
        pc = ProofChecker()
        proof = Proof(
            id="p1",
            premises=["A"],
            conclusion="A and B",
            steps=[
                ProofStep(1, "A", "premise"),
                ProofStep(2, "B", "premise"),
                ProofStep(3, "A and B", "and-intro", [1, 2]),
            ],
        )
        pc.register(proof)
        result = pc.check("p1")
        assert result.status == ProofStatus.VALID

    def test_check_invalid_dependency(self):
        pc = ProofChecker()
        proof = Proof(
            id="p1",
            steps=[ProofStep(1, "A", "step", depends_on=[99])],
        )
        pc.register(proof)
        result = pc.check("p1")
        assert result.status == ProofStatus.INVALID

    def test_check_empty(self):
        pc = ProofChecker()
        proof = Proof(id="p1")
        pc.register(proof)
        result = pc.check("p1")
        assert result.status == ProofStatus.INCOMPLETE

    def test_validate_syntax(self):
        pc = ProofChecker()
        valid, errors = pc.validate_syntax("(A and B) implies C")
        assert valid is True

    def test_validate_syntax_unbalanced(self):
        pc = ProofChecker()
        valid, errors = pc.validate_syntax("(A and B")
        assert valid is False

    def test_check_equivalence(self):
        pc = ProofChecker()
        assert pc.check_equivalence("A and B", "a and b") is True
