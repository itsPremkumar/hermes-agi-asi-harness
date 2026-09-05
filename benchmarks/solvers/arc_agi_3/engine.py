"""engine.py — AVOPISAging Agent with LangGraph-style state graph.

Implements the perceive -> reason -> plan -> act -> evaluate -> diagnose -> revise
loop as a cyclic state graph. Each node is a function that takes the current
state and returns an updated state. Edges connect nodes in the loop, with
conditional branching for success/failure.

The engine orchestrates the full pipeline:
    PuzzleParser -> RuleHypothesizer -> StrategySelector -> SolutionGenerator -> SolutionVerifier
and loops back through diagnose/revise when verification fails.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .puzzle_parser import Puzzle, PuzzleParser
from .rule_hypothesizer import HypothesisSet, RuleHypothesizer
from .solution_generator import Solution, SolutionGenerator
from .solution_verifier import SolutionVerification, SolutionVerifier
from .strategy_selector import StrategyResult, StrategySelector

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# state graph types
# ---------------------------------------------------------------------------

class Node(str, Enum):
    """State graph nodes."""
    PERCEIVE = "perceive"
    REASON = "reason"
    PLAN = "plan"
    ACT = "act"
    EVALUATE = "evaluate"
    DIAGNOSE = "diagnose"
    REVISE = "revise"
    DONE = "done"
    FAILED = "failed"


class Edge(str, Enum):
    """State graph edges."""
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    LOOP = "loop"


@dataclass
class AgentState:
    """Mutable state passed through the graph nodes."""
    puzzle: Optional[Puzzle] = None
    hypothesis_set: Optional[HypothesisSet] = None
    strategy_result: Optional[StrategyResult] = None
    solution: Optional[Solution] = None
    verification: Optional[SolutionVerification] = None
    current_node: Node = Node.PERCEIVE
    iteration: int = 0
    max_iterations: int = 5
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    history: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    done: bool = False

    def record(self, node: Node, **kwargs: Any) -> None:
        """Record a step in the history."""
        self.history.append({
            "node": node.value,
            "iteration": self.iteration,
            "timestamp": time.time(),
            **kwargs,
        })


# ---------------------------------------------------------------------------
# node functions
# ---------------------------------------------------------------------------

def _node_perceive(state: AgentState, parser: PuzzleParser) -> AgentState:
    """Perceive: parse the puzzle if not already parsed."""
    state.current_node = Node.PERCEIVE
    state.record(Node.PERCEIVE)

    if state.puzzle is not None:
        return state

    raw = state.metadata.get("raw_puzzle")
    puzzle_id = state.metadata.get("puzzle_id", "unknown")
    if raw is None:
        state.error = "No raw_puzzle in metadata"
        state.current_node = Node.FAILED
        return state

    try:
        state.puzzle = parser.parse(raw, puzzle_id=puzzle_id)
        state.record(Node.PERCEIVE, puzzle_id=puzzle_id)
    except Exception as exc:
        state.error = f"Parse error: {exc}"
        state.current_node = Node.FAILED
        logger.error("perceive_error: %s", exc)

    return state


def _node_reason(state: AgentState, hypothesizer: RuleHypothesizer) -> AgentState:
    """Reason: generate hypotheses about transformation rules."""
    state.current_node = Node.REASON
    state.record(Node.REASON)

    if state.puzzle is None:
        state.error = "No puzzle to reason about"
        state.current_node = Node.FAILED
        return state

    try:
        state.hypothesis_set = state.hypothesis_set or hypothesizer.hypothesize(state.puzzle)
        top = state.hypothesis_set.top()
        state.record(
            Node.REASON,
            top_hypothesis=top.name if top else None,
            confidence=top.confidence if top else 0.0,
        )
    except Exception as exc:
        state.error = f"Hypothesis error: {exc}"
        state.current_node = Node.FAILED
        logger.error("reason_error: %s", exc)

    return state


def _node_plan(state: AgentState, selector: StrategySelector) -> AgentState:
    """Plan: select the best solving strategy."""
    state.current_node = Node.PLAN
    state.record(Node.PLAN)

    if state.hypothesis_set is None:
        state.error = "No hypotheses to plan from"
        state.current_node = Node.FAILED
        return state

    try:
        state.strategy_result = selector.select(state.hypothesis_set)
        state.record(
            Node.PLAN,
            strategy=state.strategy_result.strategy.name,
            confidence=state.strategy_result.confidence,
        )
    except Exception as exc:
        state.error = f"Strategy selection error: {exc}"
        state.current_node = Node.FAILED
        logger.error("plan_error: %s", exc)

    return state


def _node_act(state: AgentState, generator: SolutionGenerator) -> AgentState:
    """Act: generate candidate solutions."""
    state.current_node = Node.ACT
    state.record(Node.ACT)

    if state.puzzle is None or state.hypothesis_set is None or state.strategy_result is None:
        state.error = "Missing puzzle, hypotheses, or strategy"
        state.current_node = Node.FAILED
        return state

    try:
        state.solution = generator.generate(
            state.puzzle, state.hypothesis_set, state.strategy_result
        )
        state.record(
            Node.ACT,
            candidates=len(state.solution.candidates),
            strategy=state.solution.strategy,
        )
    except Exception as exc:
        state.error = f"Generation error: {exc}"
        state.current_node = Node.FAILED
        logger.error("act_error: %s", exc)

    return state


def _node_evaluate(state: AgentState, verifier: SolutionVerifier) -> AgentState:
    """Evaluate: verify the solution against expected outputs."""
    state.current_node = Node.EVALUATE
    state.record(Node.EVALUATE)

    if state.solution is None or state.puzzle is None:
        state.error = "No solution or puzzle to evaluate"
        state.current_node = Node.FAILED
        return state

    try:
        state.verification = verifier.verify(state.solution, state.puzzle)
        state.record(
            Node.EVALUATE,
            all_passed=state.verification.all_passed,
            avg_accuracy=state.verification.average_accuracy,
        )

        if state.verification.all_passed:
            state.current_node = Node.DONE
            state.done = True
    except Exception as exc:
        state.error = f"Verification error: {exc}"
        state.current_node = Node.FAILED
        logger.error("evaluate_error: %s", exc)

    return state


def _node_diagnose(state: AgentState) -> AgentState:
    """Diagnose: analyze why the solution failed."""
    state.current_node = Node.DIAGNOSE
    state.record(Node.DIAGNOSE)

    if state.verification is None:
        state.error = "No verification to diagnose"
        state.current_node = Node.FAILED
        return state

    # analyze failures
    failures = [
        r for r in state.verification.results if not r.passed
    ]
    diagnoses: list[str] = []
    for f in failures:
        if not f.shape_match:
            diagnoses.append(f"test_{f.test_index}: shape mismatch")
        elif f.cell_accuracy < 0.5:
            diagnoses.append(f"test_{f.test_index}: low accuracy ({f.cell_accuracy:.2f})")
        else:
            diagnoses.append(f"test_{f.test_index}: near-miss ({f.cell_accuracy:.2f})")

    state.record(Node.DIAGNOSE, diagnoses=diagnoses)
    state.metadata["diagnoses"] = diagnoses

    return state


def _node_revise(state: AgentState) -> AgentState:
    """Revise: update state for another iteration."""
    state.current_node = Node.REVISE
    state.record(Node.REVISE)

    state.iteration += 1

    # Clear solution and verification to force re-generation
    state.solution = None
    state.verification = None

    # If we have diagnoses, try to adjust hypotheses
    diagnoses = state.metadata.get("diagnoses", [])
    if diagnoses and state.hypothesis_set:
        # Re-rank hypotheses: demote the top one that failed
        hyps = state.hypothesis_set.hypotheses
        if len(hyps) > 1:
            # move top hypothesis to end
            top = hyps.pop(0)
            hyps.append(top)
            state.hypothesis_set.hypotheses = hyps
            state.record(Node.REVISE, action="demoted_top_hypothesis", hypothesis=top.name)

    return state


# ---------------------------------------------------------------------------
# engine
# ---------------------------------------------------------------------------

class AVOPISAgingEngine:
    """ARC-AGI-3 solving engine with cyclic state graph.

    Orchestrates the full perceive -> reason -> plan -> act -> evaluate ->
    diagnose -> revise loop. The engine runs the loop until the solution
    passes verification or max_iterations is reached.
    """

    def __init__(
        self,
        parser: Optional[PuzzleParser] = None,
        hypothesizer: Optional[RuleHypothesizer] = None,
        selector: Optional[StrategySelector] = None,
        generator: Optional[SolutionGenerator] = None,
        verifier: Optional[SolutionVerifier] = None,
        max_iterations: int = 5,
    ) -> None:
        self.parser = parser or PuzzleParser()
        self.hypothesizer = hypothesizer or RuleHypothesizer()
        self.selector = selector or StrategySelector()
        self.generator = generator or SolutionGenerator()
        self.verifier = verifier or SolutionVerifier()
        self.max_iterations = max_iterations
        self._run_count = 0

    def solve(self, raw_puzzle: dict[str, Any], puzzle_id: str = "unknown") -> AgentState:
        """Solve a single ARC-AGI-3 puzzle.

        Args:
            raw_puzzle: the raw puzzle JSON dict.
            puzzle_id: identifier for logging correlation. If "unknown", extracted
                       from raw_puzzle["id"] if present.

        Returns:
            The final AgentState with solution and verification.
        """
        self._run_count += 1
        if puzzle_id == "unknown" and isinstance(raw_puzzle, dict) and "id" in raw_puzzle:
            puzzle_id = raw_puzzle["id"]
        logger.info("solve_start puzzle_id=%s run_id=%d", puzzle_id, self._run_count)

        state = AgentState(
            max_iterations=self.max_iterations,
            metadata={"raw_puzzle": raw_puzzle, "puzzle_id": puzzle_id},
        )

        # run the state graph loop
        while not state.done and state.current_node != Node.FAILED:
            if state.iteration >= state.max_iterations:
                state.metadata["terminated"] = "max_iterations_reached"
                break

            state = self._step(state)

        logger.info(
            "solve_done puzzle_id=%s done=%s iterations=%d",
            puzzle_id, state.done, state.iteration,
        )
        return state

    def _step(self, state: AgentState) -> AgentState:
        """Execute one step of the state graph based on current node."""
        node = state.current_node

        if node == Node.PERCEIVE:
            state = _node_perceive(state, self.parser)
            if state.current_node != Node.FAILED:
                state.current_node = Node.REASON

        elif node == Node.REASON:
            state = _node_reason(state, self.hypothesizer)
            if state.current_node != Node.FAILED:
                state.current_node = Node.PLAN

        elif node == Node.PLAN:
            state = _node_plan(state, self.selector)
            if state.current_node != Node.FAILED:
                state.current_node = Node.ACT

        elif node == Node.ACT:
            state = _node_act(state, self.generator)
            if state.current_node != Node.FAILED:
                state.current_node = Node.EVALUATE

        elif node == Node.EVALUATE:
            state = _node_evaluate(state, self.verifier)
            if state.current_node == Node.DONE:
                return state
            if state.current_node != Node.FAILED:
                state.current_node = Node.DIAGNOSE

        elif node == Node.DIAGNOSE:
            state = _node_diagnose(state)
            if state.current_node != Node.FAILED:
                state.current_node = Node.REVISE

        elif node == Node.REVISE:
            state = _node_revise(state)
            if state.current_node != Node.FAILED:
                # loop back to reason/plan/act
                state.current_node = Node.REASON

        return state

    def solve_batch(
        self,
        puzzles: list[tuple[dict[str, Any], str]],
    ) -> list[AgentState]:
        """Solve multiple puzzles."""
        return [self.solve(raw, pid) for raw, pid in puzzles]

    @property
    def run_count(self) -> int:
        return self._run_count
