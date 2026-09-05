"""Tests for feedback/ — Feedback Engine."""

from __future__ import annotations

from harness.feedback import (
    CritiqueResult,
    FeedbackEngine,
    NodeValidator,
    SelfCritique,
    ValidationResult,
    VerificationPipeline,
)


class TestValidationResult:
    """Tests for ValidationResult."""

    def test_passed(self):
        r = ValidationResult(passed=True, score=1.0)
        assert r.passed is True

    def test_failed(self):
        r = ValidationResult(passed=False, score=0.3)
        assert r.passed is False

    def test_with_message(self):
        r = ValidationResult(passed=False, score=0.3, message="failed")
        assert r.message == "failed"


class TestNodeValidator:
    """Tests for NodeValidator."""

    def test_create(self):
        v = NodeValidator()
        assert v.rules == []

    def test_add_rule(self):
        v = NodeValidator()
        v.add_rule("len_check", lambda x: len(x) > 0)
        assert len(v.rules) == 1

    def test_validate_no_rules(self):
        v = NodeValidator()
        result = v.validate("anything")
        assert result.passed is True

    def test_validate_passes(self):
        v = NodeValidator()
        v.add_rule("min_len", lambda x: len(x) >= 3)
        result = v.validate("hello")
        assert result.passed is True

    def test_validate_fails(self):
        v = NodeValidator()
        v.add_rule("min_len", lambda x: len(x) >= 10)
        result = v.validate("hi")
        assert result.passed is False

    def test_validate_multiple_rules(self):
        v = NodeValidator()
        v.add_rule("len", lambda x: len(x) >= 3, weight=1.0)
        v.add_rule("upper", lambda x: x[0].isupper(), weight=1.0)
        result = v.validate("Hello world")
        assert result.score == 1.0

    def test_validate_weighted(self):
        v = NodeValidator()
        v.add_rule("pass", lambda x: True, weight=0.7)
        v.add_rule("fail", lambda x: False, weight=0.3)
        result = v.validate("x")
        assert result.score == 0.7

    def test_validate_rule_error(self):
        v = NodeValidator()
        v.add_rule("bad", lambda x: (_ for _ in ()).throw(ValueError("oops")))
        result = v.validate("x")
        assert result.passed is False


class TestVerificationPipeline:
    """Tests for VerificationPipeline."""

    def test_create(self):
        p = VerificationPipeline()
        assert p.max_rounds == 3

    def test_add_validator(self):
        p = VerificationPipeline()
        p.add_validator(NodeValidator())
        assert len(p._validators) == 1

    def test_verify_passes(self):
        p = VerificationPipeline(min_score=0.8)
        v = NodeValidator()
        v.add_rule("min_len", lambda x: len(x) >= 3)
        p.add_validator(v)
        passed, results = p.verify("hello")
        assert passed is True

    def test_verify_fails(self):
        p = VerificationPipeline(max_rounds=1, min_score=0.9)
        v = NodeValidator()
        v.add_rule("exact", lambda x: x == "exact")
        p.add_validator(v)
        passed, results = p.verify("wrong")
        assert passed is False

    def test_verify_returns_results(self):
        p = VerificationPipeline()
        v = NodeValidator()
        v.add_rule("always", lambda x: True)
        p.add_validator(v)
        passed, results = p.verify("x")
        assert len(results) >= 1


class TestSelfCritique:
    """Tests for SelfCritique."""

    def test_create(self):
        sc = SelfCritique()
        assert sc.critique_fn is not None

    def test_critique_short_text(self):
        sc = SelfCritique()
        result = sc.critique("hi")
        assert result.score < 1.0
        assert len(result.issues) > 0

    def test_critique_good_text(self):
        sc = SelfCritique()
        result = sc.critique("This is a sufficiently long and detailed response")
        assert result.score >= 0.8

    def test_critique_and_revise(self):
        sc = SelfCritique()
        result = sc.critique_and_revise("hello world, this is long enough")
        assert isinstance(result, CritiqueResult)


class TestFeedbackEngine:
    """Tests for FeedbackEngine."""

    def test_create(self):
        fe = FeedbackEngine()
        assert fe.validators == {}

    def test_register_validator(self):
        fe = FeedbackEngine()
        v = NodeValidator()
        fe.register_validator("n1", v)
        assert "n1" in fe.validators

    def test_validate_node_no_validator(self):
        fe = FeedbackEngine()
        result = fe.validate_node("n1", "output")
        assert result.passed is True

    def test_validate_node_with_validator(self):
        fe = FeedbackEngine()
        v = NodeValidator()
        v.add_rule("min_len", lambda x: len(x) >= 5)
        fe.register_validator("n1", v)
        result = fe.validate_node("n1", "hello world")
        assert result.passed is True

    def test_register_pipeline(self):
        fe = FeedbackEngine()
        p = VerificationPipeline()
        fe.register_pipeline("p1", p)
        assert "p1" in fe.pipelines

    def test_verify_with_pipeline_missing(self):
        fe = FeedbackEngine()
        passed, results = fe.verify_with_pipeline("missing", "x")
        assert passed is True

    def test_critique_output(self):
        fe = FeedbackEngine()
        result = fe.critique_output("This is a long enough text to pass validation")
        assert result.score > 0.5
