
"""
Self-healing Orchestration — decide the recovery action after a failure.

Extracted & enhanced from agx-harness-main:
- selfheal.py: self_heal (retry, replace, replan)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class RetryPolicy:
    """Exponential backoff retry policy."""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay

    def should_retry(self, attempt: int) -> bool:
        return attempt < self.max_retries

    def delay(self, attempt: int) -> float:
        return self.base_delay * (2 ** (attempt - 1))


def maybe_replace(state: dict, role: str) -> str:
    """Maybe replace a failed agent with a different role."""
    # Simple rotation: researcher -> planner -> coder -> critic -> evaluator
    rotation = {
        "researcher": "planner",
        "planner": "coder",
        "coder": "critic",
        "critic": "evaluator",
        "evaluator": "researcher",
    }
    return rotation.get(role)


def self_heal(state: dict, role: str, attempt: int, policy: RetryPolicy = None) -> Any:
    """Decide the recovery action after a failure."""
    policy = policy or RetryPolicy()
    if policy.should_retry(attempt):
        return "retry"
    repl = maybe_replace(state, role)
    if repl:
        return ("replace", repl)
    return "replan"
