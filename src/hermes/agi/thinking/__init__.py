"""
Hermes AGI/ASI Harness — Deep Thinking Package.
"""

from .engine import (
    Critique,
    DeepThinkingEngine,
    Hypothesis,
    Invariant,
    ThinkingResult,
)
from .mcts import (
    MCTSNode,
    MCTSResult,
    MCTSSearchEngine,
)

__all__ = [
    "DeepThinkingEngine",
    "ThinkingResult",
    "Hypothesis",
    "Critique",
    "Invariant",
    "MCTSSearchEngine",
    "MCTSResult",
    "MCTSNode",
]
