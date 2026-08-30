"""Tests for Formal Verification Module."""

import os
import sys
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from verification.proof_checker import (
    ProofChecker, Proof, ProofStep, ProofStatus, CheckResult,
)
from verification.specification_parser import (
    SpecificationParser, Specification, SpecFormat, ParseResult,
)
from verification.formal_verifier import (
    FormalVerifier, VerifyStatus, VerificationResult,
)
from verification.counterexample_generator import (
    CounterexampleGenerator, Counterexample,
)
from verification.verification_orchestrator import VerificationOrchestrator


# ============== Proof Checker Tests ==============

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
        proof = Proof(id="p1", steps=[ProofStep(1, "A", "step", depends_on=[99])])
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

    def test_find_redundancies(self):
        pc = ProofChecker()
        proof = Proof(
            id="p1",
            steps=[
                ProofStep(1, "A", "step"),
                ProofStep(2, "A", "step"),
            ],
        )
        pc.register(proof)
        redundancies = pc.find_redundancies("p1")
        assert len(redundancies) >= 1


# ============== Specification Parser Tests ==============

class TestSpecificationParser:
    def test_create(self):
        sp = SpecificationParser()
        assert sp.list_specs() == []

    def test_parse_z(self):
        sp = SpecificationParser()
        result = sp.parse("x : N\ny : N", SpecFormat.Z, "z1", "Z Spec")
        assert result.success is True
        assert result.spec.format == SpecFormat.Z

    def test_parse_tla(self):
        sp = SpecificationParser()
        result = sp.parse("VARIABLES x, y\nINVARIANT TypeOK", SpecFormat.TLA, "tla1", "TLA Spec")
        assert result.success is True
        assert result.spec.format == SpecFormat.TLA

    def test_parse_alloy(self):
        sp = SpecificationParser()
        result = sp.parse("fact { }\nassert { }", SpecFormat.ALLOY, "a1", "Alloy Spec")
        assert result.success is True

    def test_parse_acl2(self):
        sp = SpecificationParser()
        result = sp.parse("(defun f (x) x)", SpecFormat.ACL2, "acl2_1", "ACL2 Spec")
        assert result.success is True

    def test_parse_coq(self):
        sp = SpecificationParser()
        result = sp.parse("Theorem t : True.", SpecFormat.COQ, "coq1", "Coq Spec")
        assert result.success is True

    def test_parse_lean(self):
        sp = SpecificationParser()
        result = sp.parse("theorem t : True := trivial", SpecFormat.LEAN, "lean1", "Lean Spec")
        assert result.success is True

    def test_parse_custom(self):
        sp = SpecificationParser()
        result = sp.parse("custom spec content", SpecFormat.CUSTOM, "c1", "Custom Spec")
        assert result.success is True

    def test_get_spec(self):
        sp = SpecificationParser()
        result = sp.parse("content", SpecFormat.Z, "z1", "Z")
        retrieved = sp.get("z1")
        assert retrieved is not None
        assert retrieved.id == "z1"

    def test_get_all(self):
        sp = SpecificationParser()
        sp.parse("c1", SpecFormat.Z, "z1", "Z1")
        sp.parse("c2", SpecFormat.TLA, "tla1", "TLA1")
        assert len(sp.get_all()) == 2


# ============== Formal Verifier Tests ==============

class TestFormalVerifier:
    def test_create(self):
        fv = FormalVerifier()
        assert fv.list_results() == []

    def test_verify_invariant_pass(self):
        fv = FormalVerifier()
        result = fv.verify_invariant("s1", "x >= 0", {"x": 5})
        assert result.status == VerifyStatus.VERIFIED

    def test_verify_invariant_fail(self):
        fv = FormalVerifier()
        result = fv.verify_invariant("s1", "x >= 0", {"x": -1})
        assert result.status == VerifyStatus.FALSIFIED

    def test_verify_precondition(self):
        fv = FormalVerifier()
        result = fv.verify_precondition("s1", "x > 0", {"x": 10})
        assert result.status == VerifyStatus.VERIFIED

    def test_verify_postcondition(self):
        fv = FormalVerifier()
        result = fv.verify_postcondition("s1", "y > x", {"x": 1}, {"y": 5})
        assert result.status == VerifyStatus.VERIFIED

    def test_verify_equivalence(self):
        fv = FormalVerifier()
        result = fv.verify_equivalence("s1", "impl1", "impl2", [1, 2, 3])
        assert result.status == VerifyStatus.VERIFIED

    def test_verify_safety_pass(self):
        fv = FormalVerifier()
        result = fv.verify_safety("s1", "x >= 0", [{"x": 1}, {"x": 2}])
        assert result.status == VerifyStatus.VERIFIED

    def test_verify_safety_fail(self):
        fv = FormalVerifier()
        result = fv.verify_safety("s1", "x >= 0", [{"x": 1}, {"x": -1}])
        assert result.status == VerifyStatus.FALSIFIED

    def test_get_result(self):
        fv = FormalVerifier()
        fv.verify_invariant("s1", "x >= 0", {"x": 5})
        result = fv.get_result("s1")
        assert result is not None
        assert result.status == VerifyStatus.VERIFIED


# ============== Counterexample Generator Tests ==============

class TestCounterexampleGenerator:
    def test_create(self):
        cg = CounterexampleGenerator()
        assert cg.count() == 0

    def test_generate(self):
        cg = CounterexampleGenerator()
        cexes = cg.generate("x > y", ["x", "y"], {"x_domain": [0, 1, 2], "y_domain": [0, 1, 2]})
        assert isinstance(cexes, list)

    def test_get(self):
        cg = CounterexampleGenerator()
        cg.generate("x > y", ["x", "y"], {"x_domain": [0], "y_domain": [1]})
        cexes = cg.get_all()
        if cexes:
            retrieved = cg.get(cexes[0].id)
            assert retrieved is not None

    def test_get_by_property(self):
        cg = CounterexampleGenerator()
        cg.generate("x > y", ["x", "y"], {"x_domain": [0], "y_domain": [1]})
        cexes = cg.get_by_property("x > y")
        assert isinstance(cexes, list)

    def test_clear(self):
        cg = CounterexampleGenerator()
        cg.generate("x > y", ["x", "y"], {"x_domain": [0], "y_domain": [1]})
        cg.clear()
        assert cg.count() == 0


# ============== Verification Orchestrator Tests ==============

class TestVerificationOrchestrator:
    def test_create(self):
        vo = VerificationOrchestrator()
        assert vo.get_stats()["specifications"] == 0

    def test_parse_specification(self):
        vo = VerificationOrchestrator()
        result = vo.parse_specification("content", SpecFormat.Z, "z1", "Z")
        assert result.success is True

    def test_verify_specification(self):
        vo = VerificationOrchestrator()
        vo.parse_specification(
            "VARIABLES x\nINVARIANT x >= 0",
            SpecFormat.TLA, "tla1", "TLA",
        )
        result = vo.verify_specification("tla1")
        assert "spec_id" in result

    def test_verify_specification_not_found(self):
        vo = VerificationOrchestrator()
        result = vo.verify_specification("nonexistent")
        assert "error" in result

    def test_check_proof(self):
        vo = VerificationOrchestrator()
        proof = Proof(id="p1", steps=[ProofStep(1, "A", "premise")])
        vo._proof_checker.register(proof)
        result = vo.check_proof("p1")
        assert isinstance(result, CheckResult)

    def test_verify_proof(self):
        vo = VerificationOrchestrator()
        proof = Proof(id="p1", steps=[ProofStep(1, "A", "premise")])
        result = vo.verify_proof(proof)
        assert "proof_id" in result
        assert "status" in result

    def test_get_history(self):
        vo = VerificationOrchestrator()
        assert vo.get_history() == []

    def test_get_stats(self):
        vo = VerificationOrchestrator()
        vo.parse_specification("content", SpecFormat.Z, "z1", "Z")
        stats = vo.get_stats()
        assert stats["specifications"] == 1

    def test_verify_invariant_via_orchestrator(self):
        vo = VerificationOrchestrator()
        vo.parse_specification(
            "VARIABLES x, y\nINVARIANT x > y",
            SpecFormat.TLA, "tla1", "TLA",
        )
        result = vo.verify_specification("tla1")
        assert "steps" in result

    def test_multiple_specifications(self):
        vo = VerificationOrchestrator()
        vo.parse_specification("c1", SpecFormat.Z, "z1", "Z1")
        vo.parse_specification("c2", SpecFormat.TLA, "tla1", "TLA1")
        vo.parse_specification("c3", SpecFormat.COQ, "coq1", "Coq1")
        stats = vo.get_stats()
        assert stats["specifications"] == 3
