"""StrategySelector — choose best solving strategy using chain pattern with routing.

Given a HypothesisSet, selects the optimal solving strategy from a registry
of available strategies. Uses a LangChain-style chain pattern with routing
to pick the strategy that best matches the detected transformation rules.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

from .rule_hypothesizer import HypothesisSet

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# data types
# ---------------------------------------------------------------------------

@dataclass
class Strategy:
    """A solving strategy with metadata."""
    name: str
    description: str
    priority: int = 0  # higher = preferred when scores tie
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class StrategyResult:
    """Result of strategy selection."""
    strategy: Strategy
    confidence: float = 0.0
    reasoning: str = ""


# ---------------------------------------------------------------------------
# routing function type
# ---------------------------------------------------------------------------

RoutingFn = Callable[[HypothesisSet], Optional[StrategyResult]]


# ---------------------------------------------------------------------------
# default strategies
# ---------------------------------------------------------------------------

STRATEGY_RULE_BASED = Strategy(
    name="rule_based",
    description="Apply detected transformation rules directly to test input",
    priority=10,
)

STRATEGY_PATTERN_MATCH = Strategy(
    name="pattern_match",
    description="Match input patterns to known ARC-AGI pattern templates",
    priority=8,
)

STRATEGY_BRUTE_FORCE = Strategy(
    name="brute_force",
    description="Enumerate all possible simple transformations and test each",
    priority=5,
)

STRATEGY_LLM_REASONING = Strategy(
    name="llm_reasoning",
    description="Use LLM to reason about the transformation and generate output",
    priority=3,
)

STRATEGY_FALLBACK = Strategy(
    name="fallback",
    description="Return input unchanged as last resort",
    priority=0,
)


# ---------------------------------------------------------------------------
# default routers
# ---------------------------------------------------------------------------

def _router_rule_based(hyp_set: HypothesisSet) -> Optional[StrategyResult]:
    """Route to rule-based strategy if we have high-confidence hypotheses."""
    top = hyp_set.top()
    if top and top.confidence >= 0.7:
        return StrategyResult(
            strategy=STRATEGY_RULE_BASED,
            confidence=top.confidence,
            reasoning=f"High-confidence hypothesis: {top.name} ({top.confidence:.2f})",
        )
    return None


def _router_pattern_match(hyp_set: HypothesisSet) -> Optional[StrategyResult]:
    """Route to pattern match if we have medium-confidence hypotheses."""
    top = hyp_set.top()
    if top and top.confidence >= 0.4:
        return StrategyResult(
            strategy=STRATEGY_PATTERN_MATCH,
            confidence=top.confidence * 0.8,
            reasoning=f"Medium-confidence hypothesis: {top.name} ({top.confidence:.2f})",
        )
    return None


def _router_brute_force(hyp_set: HypothesisSet) -> Optional[StrategyResult]:
    """Route to brute force if we have any hypotheses at all."""
    if hyp_set.hypotheses:
        return StrategyResult(
            strategy=STRATEGY_BRUTE_FORCE,
            confidence=0.3,
            reasoning=f"Low confidence hypotheses ({len(hyp_set.hypotheses)} found)",
        )
    return None


def _router_llm_fallback(hyp_set: HypothesisSet) -> Optional[StrategyResult]:
    """Always available as a fallback using LLM reasoning."""
    return StrategyResult(
        strategy=STRATEGY_LLM_REASONING,
        confidence=0.2,
        reasoning="No strong hypotheses; using LLM reasoning as fallback",
    )


# ---------------------------------------------------------------------------
# selector
# ---------------------------------------------------------------------------

class StrategySelector:
    """Select the best solving strategy for a given hypothesis set.

    Uses a chain of routing functions (LangChain-style). Each router
    either returns a StrategyResult or None. The first non-None result
    wins. If all routers return None, the fallback strategy is used.
    """

    DEFAULT_ROUTERS: list[RoutingFn] = [
        _router_rule_based,
        _router_pattern_match,
        _router_brute_force,
        _router_llm_fallback,
    ]

    def __init__(
        self,
        routers: Optional[list[RoutingFn]] = None,
        strategies: Optional[list[Strategy]] = None,
    ) -> None:
        self.routers = routers if routers is not None else self.DEFAULT_ROUTERS
        self.strategies = strategies if strategies is not None else [
            STRATEGY_RULE_BASED,
            STRATEGY_PATTERN_MATCH,
            STRATEGY_BRUTE_FORCE,
            STRATEGY_LLM_REASONING,
            STRATEGY_FALLBACK,
        ]
        self._selection_count = 0

    def select(self, hyp_set: HypothesisSet) -> StrategyResult:
        """Select the best strategy for the given hypothesis set.

        Args:
            hyp_set: ranked hypotheses from RuleHypothesizer.

        Returns:
            A StrategyResult with the chosen strategy and confidence.
        """
        self._selection_count += 1
        logger.info("select_start puzzle_id=%s", hyp_set.puzzle_id)

        for router in self.routers:
            result = router(hyp_set)
            if result is not None:
                logger.info(
                    "select_done puzzle_id=%s strategy=%s confidence=%.2f",
                    hyp_set.puzzle_id, result.strategy.name, result.confidence,
                )
                return result

        # ultimate fallback
        return StrategyResult(
            strategy=STRATEGY_FALLBACK,
            confidence=0.0,
            reasoning="All routers returned None; using fallback",
        )

    def select_batch(self, hyp_sets: list[HypothesisSet]) -> list[StrategyResult]:
        """Select strategies for multiple hypothesis sets."""
        return [self.select(hs) for hs in hyp_sets]

    @property
    def selection_count(self) -> int:
        return self._selection_count
