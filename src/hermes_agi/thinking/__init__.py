"""
Hermes AGI/ASI Harness — Deep Thinking Package.
"""

from .engine import (
    DeepThinkingEngine,
    ThinkingResult,
    Hypothesis,
    Critique,
    Invariant,
)
from .mcts import (
    MCTSSearchEngine,
    MCTSResult,
    MCTSNode,
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
