"""Tests for AVOPISAgingEngine."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from benchmarks.solvers.arc_agi_3.engine import (
    AgentState,
    AVOPISAgingEngine,
    Node,
    _node_act,
    _node_diagnose,
    _node_evaluate,
    _node_perceive,
    _node_plan,
    _node_reason,
    _node_revise,
)
from benchmarks.solvers.arc_agi_3.puzzle_parser import Puzzle, PuzzleParser
from benchmarks.solvers.arc_agi_3.rule_hypothesizer import HypothesisSet, RuleHypothesizer
from benchmarks.solvers.arc_agi_3.solution_generator import SolutionGenerator
from benchmarks.solvers.arc_agi_3.solution_verifier import SolutionVerifier
from benchmarks.solvers.arc_agi_3.strategy_selector import StrategySelector


class TestAgentState:
    def test_default_state(self):
        state = AgentState()
        assert state.current_node == Node.PERCEIVE
        assert state.iteration == 0
        assert state.done is False
        assert state.puzzle is None

    def test_record(self):
        state = AgentState()
        state.record(Node.PERCEIVE, foo="bar")
        assert len(state.history) == 1
        assert state.history[0]["node"] == "perceive"
        assert state.history[0]["foo"] == "bar"

    def test_run_id_auto_generated(self):
        state = AgentState()
        assert len(state.run_id) == 8


class TestNodeFunctions:
    def test_node_perceive_parses_puzzle(self):
        parser = PuzzleParser()
        state = AgentState()
        state.metadata["raw_puzzle"] = {
            "train": [{"input": [[1, 2], [3, 4]], "output": [[1, 2], [3, 4]]}],
            "test": [{"input": [[5, 6], [7, 8]], "output": [[5, 6], [7, 8]]}],
        }
        state.metadata["puzzle_id"] = "test"
        result = _node_perceive(state, parser)
        assert result.puzzle is not None
        assert result.puzzle.puzzle_id == "test"

    def test_node_perceive_no_raw_puzzle(self):
        parser = PuzzleParser()
        state = AgentState()
        result = _node_perceive(state, parser)
        assert result.current_node == Node.FAILED

    def test_node_reason_generates_hypotheses(self):
        h = RuleHypothesizer()
        state = AgentState()
        state.puzzle = Puzzle(puzzle_id="test")
        state.puzzle.train = []
        result = _node_reason(state, h)
        # empty train means no hypotheses, but no failure
        assert result.current_node != Node.FAILED

    def test_node_reason_no_puzzle(self):
        h = RuleHypothesizer()
        state = AgentState()
        result = _node_reason(state, h)
        assert result.current_node == Node.FAILED

    def test_node_plan_selects_strategy(self):
        selector = StrategySelector()
        state = AgentState()
        state.hypothesis_set = HypothesisSet(puzzle_id="test")
        result = _node_plan(state, selector)
        assert result.strategy_result is not None

    def test_node_plan_no_hypotheses(self):
        selector = StrategySelector()
        state = AgentState()
        result = _node_plan(state, selector)
        assert result.current_node == Node.FAILED

    def test_node_act_generates_solution(self):
        gen = SolutionGenerator()
        state = AgentState()
        state.puzzle = Puzzle(puzzle_id="test")
        state.puzzle.test = []
        state.hypothesis_set = HypothesisSet(puzzle_id="test")
        state.strategy_result = MagicMock()
        result = _node_act(state, gen)
        # empty test means no solution, but no failure
        assert result.current_node != Node.FAILED

    def test_node_act_missing_prerequisites(self):
        gen = SolutionGenerator()
        state = AgentState()
        result = _node_act(state, gen)
        assert result.current_node == Node.FAILED

    def test_node_evaluate_verifies(self):
        verifier = SolutionVerifier()
        state = AgentState()
        state.puzzle = Puzzle(puzzle_id="test")
        state.puzzle.test = []
        state.solution = MagicMock()
        state.solution.candidates = []
        result = _node_evaluate(state, verifier)
        assert result.verification is not None

    def test_node_diagnose_with_verification(self):
        state = AgentState()
        state.verification = MagicMock()
        state.verification.results = []
        result = _node_diagnose(state)
        assert result.current_node != Node.FAILED

    def test_node_revise_increments_iteration(self):
        state = AgentState()
        state.iteration = 0
        result = _node_revise(state)
        assert result.iteration == 1


class TestAVOPISAgingEngine:
    def _make_raw_puzzle(self):
        return {
            "id": "identity_test",
            "train": [
                {"input": [[1, 2], [3, 4]], "output": [[1, 2], [3, 4]]},
            ],
            "test": [
                {"input": [[5, 6], [7, 8]], "output": [[5, 6], [7, 8]]},
            ],
        }

    def test_solve_identity_puzzle(self):
        engine = AVOPISAgingEngine()
        state = engine.solve(self._make_raw_puzzle(), puzzle_id="identity_test")
        assert state.done is True
        assert state.verification.all_passed is True

    def test_solve_sets_puzzle(self):
        engine = AVOPISAgingEngine()
        state = engine.solve(self._make_raw_puzzle())
        assert state.puzzle is not None
        assert state.puzzle.puzzle_id == "identity_test"

    def test_solve_sets_hypotheses(self):
        engine = AVOPISAgingEngine()
        state = engine.solve(self._make_raw_puzzle())
        assert state.hypothesis_set is not None

    def test_solve_sets_strategy(self):
        engine = AVOPISAgingEngine()
        state = engine.solve(self._make_raw_puzzle())
        assert state.strategy_result is not None

    def test_solve_sets_solution(self):
        engine = AVOPISAgingEngine()
        state = engine.solve(self._make_raw_puzzle())
        assert state.solution is not None

    def test_solve_sets_verification(self):
        engine = AVOPISAgingEngine()
        state = engine.solve(self._make_raw_puzzle())
        assert state.verification is not None

    def test_solve_run_id_present(self):
        engine = AVOPISAgingEngine()
        state = engine.solve(self._make_raw_puzzle())
        assert len(state.run_id) == 8

    def test_solve_history_recorded(self):
        engine = AVOPISAgingEngine()
        state = engine.solve(self._make_raw_puzzle())
        assert len(state.history) > 0

    def test_solve_max_iterations(self):
        engine = AVOPISAgingEngine(max_iterations=1)
        state = engine.solve(self._make_raw_puzzle())
        # should either succeed or terminate at max_iterations
        assert state.iteration <= engine.max_iterations

    def test_solve_count(self):
        engine = AVOPISAgingEngine()
        engine.solve(self._make_raw_puzzle())
        engine.solve(self._make_raw_puzzle())
        assert engine.run_count == 2

    def test_solve_batch(self):
        engine = AVOPISAgingEngine()
        puzzles = [
            (self._make_raw_puzzle(), "p1"),
            (self._make_raw_puzzle(), "p2"),
        ]
        states = engine.solve_batch(puzzles)
        assert len(states) == 2

    def test_solve_invalid_puzzle(self):
        engine = AVOPISAgingEngine()
        state = engine.solve({"invalid": "puzzle"}, puzzle_id="bad")
        # should handle gracefully
        assert state.current_node == Node.FAILED or state.iteration <= engine.max_iterations
