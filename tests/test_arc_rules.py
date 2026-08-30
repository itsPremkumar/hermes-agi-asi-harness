"""Tests for ARC-AGI-3 Rule Inference."""
import pytest
from core.arc_agi_3.rule_inference import (
    RuleInferenceEngine, Rule, RuleType, Example
)


class TestRuleInferenceEngine:
    def test_create(self):
        engine = RuleInferenceEngine()
        assert engine._rules == []

    def test_infer_empty(self):
        engine = RuleInferenceEngine()
        rules = engine.infer([])
        assert rules == []

    def test_infer_identity(self):
        engine = RuleInferenceEngine()
        examples = [
            Example("e1", [[1, 2], [3, 4]], [[1, 2], [3, 4]]),
        ]
        rules = engine.infer(examples)
        assert any(r.rule_type == RuleType.IDENTITY for r in rules)

    def test_infer_rotation(self):
        engine = RuleInferenceEngine()
        examples = [
            Example("e1", [[1, 2], [3, 4]], [[3, 1], [4, 2]]),
        ]
        rules = engine.infer(examples)
        assert any(r.rule_type == RuleType.ROTATE for r in rules)

    def test_infer_flip(self):
        engine = RuleInferenceEngine()
        examples = [
            Example("e1", [[1, 2, 3], [4, 5, 6]], [[3, 2, 1], [6, 5, 4]]),
        ]
        rules = engine.infer(examples)
        assert any(r.rule_type == RuleType.FLIP for r in rules)

    def test_infer_color_map(self):
        engine = RuleInferenceEngine()
        examples = [
            Example("e1", [[1, 2], [3, 4]], [[5, 6], [7, 8]]),
        ]
        rules = engine.infer(examples)
        assert any(r.rule_type == RuleType.COLOR_MAP for r in rules)

    def test_get_best_rule(self):
        engine = RuleInferenceEngine()
        examples = [
            Example("e1", [[1]], [[1]]),
        ]
        engine.infer(examples)
        best = engine.get_best_rule()
        assert best is not None
        assert best.confidence == 1.0

    def test_apply_identity(self):
        engine = RuleInferenceEngine()
        rule = Rule("r1", RuleType.IDENTITY, 1.0, "identity")
        result = engine.apply_rule(rule, [[1, 2], [3, 4]])
        assert result == [[1, 2], [3, 4]]

    def test_apply_rotation(self):
        engine = RuleInferenceEngine()
        rule = Rule("r1", RuleType.ROTATE, 0.9, "rotate")
        result = engine.apply_rule(rule, [[1, 2], [3, 4]])
        assert result == [[3, 1], [4, 2]]

    def test_apply_flip(self):
        engine = RuleInferenceEngine()
        rule = Rule("r1", RuleType.FLIP, 0.9, "flip")
        result = engine.apply_rule(rule, [[1, 2, 3]])
        assert result == [[3, 2, 1]]

    def test_apply_color_map(self):
        engine = RuleInferenceEngine()
        rule = Rule("r1", RuleType.COLOR_MAP, 0.85, "color_map", params={"mapping": {1: 5, 2: 6}})
        result = engine.apply_rule(rule, [[1, 2]])
        assert result == [[5, 6]]

    def test_get_state(self):
        engine = RuleInferenceEngine()
        state = engine.get_state()
        assert state["rules_found"] == 0
