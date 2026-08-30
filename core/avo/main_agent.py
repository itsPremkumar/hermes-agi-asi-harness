"""AVO Main Agent: the autonomous variation operator loop.

Per the paper, the Main Agent is the worker that replaces the
traditional ``Vary(P)`` operator:

    Observe → Reason → Plan → Implement → Test → Evaluate → Diagnose
                                                              → Revise

The agent decides what to inspect, which previous solutions to
consult, which diagnostics to run, how to revise, and what
direction to explore next.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .memory import AVOMemory, MemoryEntry
from .lineage import Lineage, VersionRecord
from .correctness_gate import CorrectnessGate
from .supervisor import Supervisor, StagnationSignal


@dataclass
class Observation:
    current_state: Dict[str, Any] = field(default_factory=dict)
    previous_attempts: List[Dict[str, Any]] = field(default_factory=list)
    domain_knowledge: List[str] = field(default_factory=list)
    feedback: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    hypothesis: str = ""
    steps: List[str] = field(default_factory=list)
    expected_improvement: float = 0.0


@dataclass
class Candidate:
    version: str = ""
    source: str = ""
    parent: str | None = None
    modification: str = ""
    hypothesis: str = ""
    test_results: Dict[str, Any] = field(default_factory=dict)
    benchmark_results: Dict[str, Any] = field(default_factory=dict)
    correctness: bool = False
    performance: float = 0.0
    reasoning_summary: str = ""
    commit_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dataclass_fields__.items()}


@dataclass
class EvaluationResult:
    accepted: bool = False
    correctness: bool = False
    performance: float = 0.0
    reason: str = ""
    candidate_version: str | None = None


class MainAgent:
    """Autonomous Main Agent — the AVO variation operator.

    Iterative engineering loop that produces, tests, evaluates, and
    revises candidates, persisting everything to memory and lineage.
    """

    def __init__(
        self,
        memory: AVOMemory | None = None,
        lineage: Lineage | None = None,
        gate: CorrectnessGate | None = None,
        supervisor: Supervisor | None = None,
    ) -> None:
        self.memory = memory or AVOMemory()
        self.lineage = lineage or Lineage()
        self.gate = gate or CorrectnessGate()
        self.supervisor = supervisor or Supervisor()
        self._strategy: str = "default"
        self._diagnose_count: int = 0
        self._revision_count: int = 0

    def observe(
        self,
        current_state: Dict[str, Any],
        domain_knowledge: List[str] | None = None,
    ) -> Observation:
        recent = self.memory.recent(10)
        previous = [r.to_dict() for r in recent]
        return Observation(
            current_state=current_state,
            previous_attempts=previous,
            domain_knowledge=domain_knowledge or [],
            feedback={},
        )

    def reason(self, obs: Observation) -> Plan:
        hypothesis = self._form_hypothesis(obs)
        steps = self._plan_steps(obs)
        return Plan(
            hypothesis=hypothesis,
            steps=steps,
            expected_improvement=0.05,
        )

    def implement(self, plan: Plan) -> Candidate:
        vid = "v" + uuid.uuid4().hex[:6]
        return Candidate(
            version=vid,
            source="MainAgent.implement",
            modification=plan.hypothesis,
            hypothesis=plan.hypothesis,
            reasoning_summary=f"Implemented hypothesis: {plan.hypothesis}",
        )

    def test(self, candidate: Candidate) -> Dict[str, Any]:
        tests = []
        if candidate.correctness:
            tests.append({"name": "correctness", "passed": True})
        return {"tests": tests, "candidate": candidate.version}

    def evaluate(
        self,
        candidate: Candidate,
        score_fn: Any | None = None,
    ) -> EvaluationResult:
        score = float(candidate.performance)
        gate = self.gate.evaluate(candidate)
        accepted = gate.can_evaluate and score > 0
        return EvaluationResult(
            accepted=accepted,
            correctness=gate.correctness,
            performance=score,
            reason=gate.reason if not accepted else "accepted",
            candidate_version=candidate.version,
        )

    def diagnose(self, result: EvaluationResult) -> str:
        self._diagnose_count += 1
        if result.correctness and result.performance == 0.0:
            return "repair"
        if result.correctness and result.performance > 0:
            return "validate"
        return "repair"

    def revise(self, candidate: Candidate, signal: StagnationSignal) -> Candidate:
        self._revision_count += 1
        candidate.modification += f" [revised:{signal.recommended_action}]"
        return candidate

    def run_iteration(
        self,
        current_state: Dict[str, Any],
        score_fn: Any | None = None,
    ) -> Dict[str, Any]:
        obs = self.observe(current_state)
        plan = self.reason(obs)
        candidate = self.implement(plan)
        self.test(candidate)
        result = self.evaluate(candidate, score_fn)
        action = self.diagnose(result)
        meta = self.supervisor.observe(result.performance, self._strategy)
        if meta.detected:
            candidate = self.revise(candidate, meta)
            self._strategy = meta.strategy_change or self._strategy
        candidate.correctness = result.correctness
        candidate.performance = result.performance
        committed = self.lineage.commit_candidate(
            VersionRecord(
                version=candidate.version,
                modification=candidate.modification,
                hypothesis=candidate.hypothesis,
                test_results=candidate.test_results,
                benchmark_results=candidate.benchmark_results,
                correctness=candidate.correctness,
                performance=candidate.performance,
                reasoning_summary=candidate.reasoning_summary,
            ),
        )
        self.memory.add(MemoryEntry(
            kind="iteration",
            content=f"AVO iteration {candidate.version}: {action} -> accepted={result.accepted} committed={committed}",
            success=result.accepted,
            tags=["avo", "iteration"],
        ))
        return {
            "candidate": candidate.version,
            "action": action,
            "accepted": result.accepted,
            "committed": committed,
            "stagnation": meta.detected,
            "strategy": self._strategy,
        }

    # -- Internal helpers --------------------------------------------

    def _form_hypothesis(self, obs: Observation) -> str:
        best = None
        for a in reversed(obs.previous_attempts):
            if a.get("score", 0) > 0:
                best = a
                break
        if best:
            return f"improve_on:{best.get('modification', 'previous')}"
        return "baseline_exploration"

    def _plan_steps(self, obs: Observation) -> List[str]:
        return ["inspect_previous", "form_hypothesis", "implement", "test", "evaluate"]
