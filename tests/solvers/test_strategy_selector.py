"""Tests for StrategySelector."""
import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from harness.solvers.arc_agi_3.rule_hypothesizer import Hypothesis, HypothesisSet
from harness.solvers.arc_agi_3.strategy_selector import (
    StrategySelector,
    StrategyResult,
    Strategy,
    STRATEGY_RULE_BASED,
    STRATEGY_PATTERN_MATCH,
    STRATEGY_BRUTE_FORCE,
    STRATEGY_LLM_REASONING,
    STRATEGY_FALLBACK,
    _router_rule_based,
    _router_pattern_match,
    _router_brute_force,
    _router_llm_fallback,
)


class TestRouters:
    def test_router_rule_based_high_confidence(self):
        hyp_set = HypothesisSet(puzzle_id="test")
        hyp_set.hypotheses = [Hypothesis(name="Identity", description="test", confidence=0.95)]
        result = _router_rule_based(hyp_set)
        assert result is not None
        assert result.strategy == STRATEGY_RULE_BASED

    def test_router_rule_based_low_confidence(self):
        hyp_set = HypothesisSet(puzzle_id="test")
        hyp_set.hypotheses = [Hypothesis(name="Identity", description="test", confidence=0.5)]
        result = _router_rule_based(hyp_set)
        assert result is None

    def test_router_rule_based_empty(self):
        hyp_set = HypothesisSet(puzzle_id="test")
        result = _router_rule_based(hyp_set)
        assert result is None

    def test_router_pattern_match_medium_confidence(self):
        hyp_set = HypothesisSet(puzzle_id="test")
        hyp_set.hypotheses = [Hypothesis(name="Rotation", description="test", confidence=0.6)]
        result = _router_pattern_match(hyp_set)
        assert result is not None
        assert result.strategy == STRATEGY_PATTERN_MATCH

    def test_router_pattern_match_low_confidence(self):
        hyp_set = HypothesisSet(puzzle_id="test")
        hyp_set.hypotheses = [Hypothesis(name="Rotation", description="test", confidence=0.3)]
        result = _router_pattern_match(hyp_set)
        assert result is None

    def test_router_brute_force_with_hypotheses(self):
        hyp_set = HypothesisSet(puzzle_id="test")
        hyp_set.hypotheses = [Hypothesis(name="Color Shift", description="test", confidence=0.3)]
        result = _router_brute_force(hyp_set)
        assert result is not None
        assert result.strategy == STRATEGY_BRUTE_FORCE

    def test_router_brute_force_empty(self):
        hyp_set = HypothesisSet(puzzle_id="test")
        result = _router_brute_force(hyp_set)
        assert result is None

    def test_router_llm_fallback_always_returns(self):
        hyp_set = HypothesisSet(puzzle_id="test")
        result = _router_llm_fallback(hyp_set)
        assert result is not None
        assert result.strategy == STRATEGY_LLM_REASONING


class TestStrategySelector:
    def test_select_rule_based(self):
        selector = StrategySelector()
        hyp_set = HypothesisSet(puzzle_id="test")
        hyp_set.hypotheses = [Hypothesis(name="Identity", description="test", confidence=0.95)]
        result = selector.select(hyp_set)
        assert result.strategy == STRATEGY_RULE_BASED

    def test_select_pattern_match(self):
        selector = StrategySelector()
        hyp_set = HypothesisSet(puzzle_id="test")
        hyp_set.hypotheses = [Hypothesis(name="Rotation", description="test", confidence=0.6)]
        result = selector.select(hyp_set)
        assert result.strategy == STRATEGY_PATTERN_MATCH

    def test_select_brute_force(self):
        selector = StrategySelector()
        hyp_set = HypothesisSet(puzzle_id="test")
        hyp_set.hypotheses = [Hypothesis(name="Color Shift", description="test", confidence=0.3)]
        result = selector.select(hyp_set)
        assert result.strategy == STRATEGY_BRUTE_FORCE

    def test_select_llm_fallback(self):
        selector = StrategySelector()
        hyp_set = HypothesisSet(puzzle_id="test")
        result = selector.select(hyp_set)
        assert result.strategy == STRATEGY_LLM_REASONING

    def test_select_batch(self):
        selector = StrategySelector()
        hyp_sets = []
        for i in range(3):
            hs = HypothesisSet(puzzle_id=f"test_{i}")
            hs.hypotheses = [Hypothesis(name="Identity", description="test", confidence=0.95)]
            hyp_sets.append(hs)
        results = selector.select_batch(hyp_sets)
        assert len(results) == 3
        for r in results:
            assert r.strategy == STRATEGY_RULE_BASED

    def test_select_count(self):
        selector = StrategySelector()
        hyp_set = HypothesisSet(puzzle_id="test")
        selector.select(hyp_set)
        selector.select(hyp_set)
        assert selector.selection_count == 2

    def test_custom_routers(self):
        def custom_router(hyp_set):
            return StrategyResult(
                strategy=STRATEGY_BRUTE_FORCE,
                confidence=1.0,
                reasoning="custom",
            )
        selector = StrategySelector(routers=[custom_router])
        hyp_set = HypothesisSet(puzzle_id="test")
        result = selector.select(hyp_set)
        assert result.strategy == STRATEGY_BRUTE_FORCE

    def test_select_returns_confidence(self):
        selector = StrategySelector()
        hyp_set = HypothesisSet(puzzle_id="test")
        hyp_set.hypotheses = [Hypothesis(name="Identity", description="test", confidence=0.95)]
        result = selector.select(hyp_set)
        assert result.confidence > 0.7

    def test_select_returns_reasoning(self):
        selector = StrategySelector()
        hyp_set = HypothesisSet(puzzle_id="test")
        hyp_set.hypotheses = [Hypothesis(name="Identity", description="test", confidence=0.95)]
        result = selector.select(hyp_set)
        assert len(result.reasoning) > 0
