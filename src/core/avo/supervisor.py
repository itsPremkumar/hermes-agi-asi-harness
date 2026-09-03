"""AVO Supervisor: watches the trajectory and redirects on stagnation."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class StagnationSignal:
    detected: bool = False
    reason: str = ""
    recommended_action: str = "continue"
    strategy_change: str | None = None
    force_exploration: bool = False
    redirect_target: str | None = None


class Supervisor:
    """Higher-level controller that detects stagnation and redirects search.

    The Main Agent answers: ``What should I do next?``
    The Supervisor answers: ``Is the overall search still productive?``

    Watches for:
    - repeated failure
    - stagnation (low information gain)
    - same strategy repeated
    - search plateau
    then redirects: new direction, forced exploration, or strategy change.
    """

    def __init__(
        self,
        max_no_improve: int = 10,
        stagnation_window: int = 20,
    ) -> None:
        self._max_no_improve = max_no_improve
        self._stagnation_window = stagnation_window
        self._history: List[Dict[str, Any]] = []
        self._last_improvement_at: float | None = None

    def observe(self, score: float, strategy: str, meta: Dict[str, Any] | None = None) -> StagnationSignal:
        now = time.time()
        entry = {
            "timestamp": now,
            "score": score,
            "strategy": strategy,
            **(meta or {}),
        }
        self._history.append(entry)
        if score > 0 and self._last_improvement_at is None:
            self._last_improvement_at = now

        signal = self._diagnose(now)
        return signal

    def _diagnose(self, now: float) -> StagnationSignal:
        # Has there been any improvement in the window?
        recent = self._history[-self._stagnation_window :]
        if not recent:
            return StagnationSignal(detected=False, reason="insufficient history")

        best_recent = max(r["score"] for r in recent)
        best_ever = max(r["score"] for r in self._history)
        no_improve_count = sum(1 for r in recent if r["score"] < best_ever)

        # Did score increase at all?
        improved = any(
            self._history[i]["score"] > self._history[i - 1]["score"]
            for i in range(1, len(self._history))
            if len(self._history) > 1
        )

        if no_improve_count >= self._max_no_improve and not improved:
            return StagnationSignal(
                detected=True,
                reason=f"no improvement in last {no_improve_count} evaluations",
                recommended_action="redirect",
                strategy_change="diversify",
                force_exploration=True,
                redirect_target="new_hypothesis",
            )
        if no_improve_count >= self._max_no_improve // 2:
            return StagnationSignal(
                detected=True,
                reason="plateau forming",
                recommended_action="explore",
                force_exploration=True,
                redirect_target="exploration_branch",
            )
        return StagnationSignal(detected=False, reason="search healthy")

    def stats(self) -> Dict[str, Any]:
        return {
            "total_observations": len(self._history),
            "last_improvement_at": self._last_improvement_at,
            "best_score": max((r["score"] for r in self._history), default=None),
            "recent_count": len(self._history),
        }
