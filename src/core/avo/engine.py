"""AVO Engine: top-level orchestrator combining Main Agent + Supervisor + Memory + Lineage."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Callable

from .main_agent import MainAgent, Candidate
from .memory import AVOMemory
from .lineage import Lineage
from .correctness_gate import CorrectnessGate
from .supervisor import Supervisor


@dataclass
class AVOConfig:
    max_iterations: int = 50
    max_no_improve: int = 10
    correctness_gate: bool = True
    enable_supervisor: bool = True
    persist_memory: bool = True
    store_dir: str = ".avo_memory"
    score_fn: Callable | None = None


class AVOEngine:
    """AVO search engine — autonomous evolutionary variation operator.

    Runs the closed-loop AVO process:
        OBSERVE → HYPOTHESIZE → ACT → OBSERVE RESULT → UPDATE STATE → REASON → ACT AGAIN
    with persistent memory, lineage, a correctness gate, and a supervisor.
    """

    def __init__(self, config: AVOConfig | None = None) -> None:
        self.config = config or AVOConfig()
        self.memory = AVOMemory(store_dir=self.config.store_dir)
        self.lineage = Lineage(store_dir=self.config.store_dir + "/lineage")
        self.gate = CorrectnessGate() if self.config.correctness_gate else None
        self.supervisor = Supervisor(
            max_no_improve=self.config.max_no_improve,
        ) if self.config.enable_supervisor else None
        self.agent = MainAgent(
            memory=self.memory,
            lineage=self.lineage,
            gate=self.gate,
            supervisor=self.supervisor,
        )
        self._iteration = 0
        self._history: List[Dict[str, Any]] = []

    def run(
        self,
        initial_state: Dict[str, Any],
        score_fn: Callable[[Candidate], float] | None = None,
    ) -> Dict[str, Any]:
        state = dict(initial_state)
        best = None
        for i in range(self.config.max_iterations):
            self._iteration = i
            result = self.agent.run_iteration(state, score_fn=score_fn)
            self._history.append(result)
            if result["accepted"] and (best is None or result["accepted"]):
                head = self.lineage.head()
                if head:
                    best = head.version
            state = {"iteration": i, "best": best, **state}
        return self.summary(best)

    def summary(self, best: str | None = None) -> Dict[str, Any]:
        return {
            "iterations": self._iteration + 1,
            "history": self._history,
            "best_version": best,
            "memory_stats": self.memory.stats(),
            "lineage_stats": self.lineage.stats(),
            "supervisor_stats": self.supervisor.stats() if self.supervisor else None,
        }
