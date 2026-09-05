"""Tests for SolutionVerifier."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from benchmarks.solvers.arc_agi_3.puzzle_parser import ExamplePair, Grid, Puzzle
from benchmarks.solvers.arc_agi_3.solution_generator import Candidate, Solution
from benchmarks.solvers.arc_agi_3.solution_verifier import (
    SolutionVerifier,
)


def _pair(inp, out):
    return ExamplePair(input_grid=Grid.from_raw(inp), output_grid=Grid.from_raw(out))


class TestSolutionVerifier:
    def test_verify_exact_match(self):
        verifier = SolutionVerifier()
        p = Puzzle(puzzle_id="test")
        p.test = [_pair([[1, 2], [3, 4]], [[1, 2], [3, 4]])]
        sol = Solution(puzzle_id="test")
        sol.candidates = [Candidate(grid=Grid.from_raw([[1, 2], [3, 4]]), strategy="test")]
        result = verifier.verify(sol, p)
        assert result.all_passed is True
        assert result.results[0].exact_match is True
        assert result.results[0].cell_accuracy == 1.0

    def test_verify_shape_mismatch(self):
        verifier = SolutionVerifier()
        p = Puzzle(puzzle_id="test")
        p.test = [_pair([[1, 2], [3, 4]], [[1, 2, 3], [4, 5, 6]])]
        sol = Solution(puzzle_id="test")
        sol.candidates = [Candidate(grid=Grid.from_raw([[1, 2], [3, 4]]), strategy="test")]
        result = verifier.verify(sol, p)
        assert result.all_passed is False
        assert result.results[0].shape_match is False

    def test_verify_partial_match(self):
        verifier = SolutionVerifier()
        p = Puzzle(puzzle_id="test")
        p.test = [_pair([[1, 2], [3, 4]], [[1, 2], [3, 5]])]
        sol = Solution(puzzle_id="test")
        sol.candidates = [Candidate(grid=Grid.from_raw([[1, 2], [3, 4]]), strategy="test")]
        result = verifier.verify(sol, p)
        assert result.results[0].cell_accuracy == 0.75

    def test_verify_all_passed_false_when_any_fail(self):
        verifier = SolutionVerifier()
        p = Puzzle(puzzle_id="test")
        p.test = [
            _pair([[1, 2], [3, 4]], [[1, 2], [3, 4]]),
            _pair([[5, 6], [7, 8]], [[5, 6], [7, 0]]),
        ]
        sol = Solution(puzzle_id="test")
        sol.candidates = [
            Candidate(grid=Grid.from_raw([[1, 2], [3, 4]]), strategy="test"),
            Candidate(grid=Grid.from_raw([[5, 6], [7, 8]]), strategy="test"),
        ]
        result = verifier.verify(sol, p)
        assert result.all_passed is False
        assert result.any_passed is True

    def test_verify_color_match(self):
        verifier = SolutionVerifier()
        p = Puzzle(puzzle_id="test")
        p.test = [_pair([[1, 2], [3, 4]], [[5, 6], [7, 8]])]
        sol = Solution(puzzle_id="test")
        sol.candidates = [Candidate(grid=Grid.from_raw([[1, 2], [3, 4]]), strategy="test")]
        result = verifier.verify(sol, p)
        assert result.results[0].color_match is False

    def test_verify_color_palette_match(self):
        verifier = SolutionVerifier()
        p = Puzzle(puzzle_id="test")
        p.test = [_pair([[1, 2], [3, 4]], [[1, 2], [3, 4]])]
        sol = Solution(puzzle_id="test")
        sol.candidates = [Candidate(grid=Grid.from_raw([[1, 2], [3, 4]]), strategy="test")]
        result = verifier.verify(sol, p)
        assert result.results[0].color_match is True

    def test_verify_partial_credit_mode(self):
        verifier = SolutionVerifier(partial_credit=True, exact_match_threshold=0.75)
        p = Puzzle(puzzle_id="test")
        p.test = [_pair([[1, 2], [3, 4]], [[1, 2], [3, 5]])]
        sol = Solution(puzzle_id="test")
        sol.candidates = [Candidate(grid=Grid.from_raw([[1, 2], [3, 4]]), strategy="test")]
        result = verifier.verify(sol, p)
        assert result.results[0].passed is True  # 0.75 >= 0.75

    def test_verify_partial_credit_below_threshold(self):
        verifier = SolutionVerifier(partial_credit=True, exact_match_threshold=0.9)
        p = Puzzle(puzzle_id="test")
        p.test = [_pair([[1, 2], [3, 4]], [[1, 2], [3, 5]])]
        sol = Solution(puzzle_id="test")
        sol.candidates = [Candidate(grid=Grid.from_raw([[1, 2], [3, 4]]), strategy="test")]
        result = verifier.verify(sol, p)
        assert result.results[0].passed is False  # 0.75 < 0.9

    def test_verify_average_accuracy(self):
        verifier = SolutionVerifier()
        p = Puzzle(puzzle_id="test")
        p.test = [
            _pair([[1, 2], [3, 4]], [[1, 2], [3, 4]]),
            _pair([[5, 6], [7, 8]], [[5, 6], [7, 0]]),
        ]
        sol = Solution(puzzle_id="test")
        sol.candidates = [
            Candidate(grid=Grid.from_raw([[1, 2], [3, 4]]), strategy="test"),
            Candidate(grid=Grid.from_raw([[5, 6], [7, 8]]), strategy="test"),
        ]
        result = verifier.verify(sol, p)
        assert result.average_accuracy == 0.875  # (1.0 + 0.75) / 2

    def test_verify_count(self):
        verifier = SolutionVerifier()
        p = Puzzle(puzzle_id="test")
        p.test = [_pair([[1]], [[1]])]
        sol = Solution(puzzle_id="test")
        sol.candidates = [Candidate(grid=Grid.from_raw([[1]]), strategy="test")]
        verifier.verify(sol, p)
        verifier.verify(sol, p)
        assert verifier.verification_count == 2

    def test_verify_batch(self):
        verifier = SolutionVerifier()
        p1 = Puzzle(puzzle_id="test1")
        p1.test = [_pair([[1]], [[1]])]
        p2 = Puzzle(puzzle_id="test2")
        p2.test = [_pair([[2]], [[2]])]
        sol1 = Solution(puzzle_id="test1")
        sol1.candidates = [Candidate(grid=Grid.from_raw([[1]]), strategy="test")]
        sol2 = Solution(puzzle_id="test2")
        sol2.candidates = [Candidate(grid=Grid.from_raw([[2]]), strategy="test")]
        results = verifier.verify_batch([sol1, sol2], [p1, p2])
        assert len(results) == 2
        assert results[0].all_passed is True
        assert results[1].all_passed is True

    def test_verify_batch_mismatched_lengths(self):
        verifier = SolutionVerifier()
        with pytest.raises(ValueError, match="solutions count"):
            verifier.verify_batch([], [Puzzle(puzzle_id="x")])

    def test_verify_result_metadata(self):
        verifier = SolutionVerifier()
        p = Puzzle(puzzle_id="test")
        p.test = [_pair([[1, 2], [3, 4]], [[1, 2], [3, 4]])]
        sol = Solution(puzzle_id="test")
        sol.candidates = [Candidate(grid=Grid.from_raw([[1, 2], [3, 4]]), strategy="test")]
        result = verifier.verify(sol, p)
        assert result.metadata["num_test_pairs"] == 1
        assert result.metadata["num_candidates"] == 1
