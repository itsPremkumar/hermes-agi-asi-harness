"""Tests for ARC-AGI-3 Core Engine."""

import pytest

from arc_agi_3.arc_agi_3_engine import (
    Grid,
    CellType,
    RuleHypothesis,
    Strategy,
    Solution,
    VerificationResult,
    RuleHypothesizer,
    StrategySelector,
    SolutionGenerator,
    SolutionVerifier,
    Engine,
)


class TestGrid:
    def test_create(self):
        grid = Grid(3, 3)
        assert grid.width == 3
        assert grid.height == 3
        assert len(grid.cells) == 3

    def test_get_set(self):
        grid = Grid(3, 3)
        grid.set(1, 1, CellType.FILLED.value)
        assert grid.get(1, 1) == CellType.FILLED.value

    def test_get_out_of_bounds(self):
        grid = Grid(3, 3)
        assert grid.get(5, 5) == CellType.BLOCKED.value

    def test_clone(self):
        grid = Grid(3, 3)
        grid.set(0, 0, CellType.FILLED.value)
        clone = grid.clone()
        assert clone.get(0, 0) == CellType.FILLED.value
        assert clone is not grid

    def test_equals(self):
        grid1 = Grid(2, 2)
        grid2 = Grid(2, 2)
        assert grid1.equals(grid2)
        grid2.set(0, 0, 1)
        assert not grid1.equals(grid2)

    def test_count_filled(self):
        grid = Grid(2, 2)
        grid.set(0, 0, 1)
        grid.set(1, 1, 1)
        assert grid.count_filled() == 2


class TestRuleHypothesizer:
    def test_create(self):
        hypothesizer = RuleHypothesizer()
        assert hypothesizer is not None

    def test_hypothesize_copy(self):
        hypothesizer = RuleHypothesizer()
        grid = Grid(2, 2)
        hypotheses = hypothesizer.hypothesize(grid, grid)
        assert any(h.name == "copy" for h in hypotheses)

    def test_hypothesize_fill_all(self):
        hypothesizer = RuleHypothesizer()
        input_grid = Grid(2, 2)
        output_grid = Grid(2, 2)
        for y in range(2):
            for x in range(2):
                output_grid.set(x, y, 1)
        hypotheses = hypothesizer.hypothesize(input_grid, output_grid)
        assert any(h.name == "fill_all" for h in hypotheses)

    def test_hypothesize_empty(self):
        hypothesizer = RuleHypothesizer()
        input_grid = Grid(2, 2)
        output_grid = Grid(2, 2)
        hypotheses = hypothesizer.hypothesize(input_grid, output_grid)
        assert len(hypotheses) >= 1


class TestStrategySelector:
    def test_create(self):
        selector = StrategySelector()
        assert selector is not None

    def test_select_copy(self):
        selector = StrategySelector()
        hypotheses = [RuleHypothesis(name="copy", confidence=0.9)]
        strategy = selector.select(hypotheses)
        assert strategy is not None
        assert strategy.name == "direct_copy"

    def test_select_empty(self):
        selector = StrategySelector()
        strategy = selector.select([])
        assert strategy is None


class TestSolutionGenerator:
    def test_create(self):
        generator = SolutionGenerator()
        assert generator is not None

    def test_generate_copy(self):
        generator = SolutionGenerator()
        grid = Grid(2, 2)
        strategy = Strategy(name="direct_copy")
        solution = generator.generate(grid, strategy, [])
        assert solution.grid is not None
        assert solution.grid.equals(grid)

    def test_generate_fill_all(self):
        generator = SolutionGenerator()
        grid = Grid(2, 2)
        strategy = Strategy(name="fill_all")
        solution = generator.generate(grid, strategy, [])
        assert solution.grid.count_filled() == 4

    def test_generate_invert(self):
        generator = SolutionGenerator()
        grid = Grid(2, 2)
        grid.set(0, 0, 1)
        strategy = Strategy(name="invert")
        solution = generator.generate(grid, strategy, [])
        assert solution.grid.get(0, 0) == 0
        assert solution.grid.get(1, 1) == 1


class TestSolutionVerifier:
    def test_create(self):
        verifier = SolutionVerifier()
        assert verifier is not None

    def test_verify_match(self):
        verifier = SolutionVerifier()
        grid = Grid(2, 2)
        solution = Solution(grid=grid.clone())
        expected = grid.clone()
        result = verifier.verify(solution, expected)
        assert result.passed is True
        assert result.score == 1.0

    def test_verify_mismatch(self):
        verifier = SolutionVerifier()
        grid = Grid(2, 2)
        solution = Solution(grid=grid.clone())
        expected = Grid(2, 2)
        expected.set(0, 0, 1)
        result = verifier.verify(solution, expected)
        assert result.passed is False

    def test_verify_no_grid(self):
        verifier = SolutionVerifier()
        solution = Solution(grid=None)
        result = verifier.verify(solution)
        assert result.passed is False


class TestEngine:
    def test_create(self):
        engine = Engine()
        assert engine is not None

    def test_solve_copy(self):
        engine = Engine()
        grid = Grid(2, 2)
        solution = engine.solve(grid, grid)
        assert solution.valid is True
        assert solution.score == 1.0

    def test_solve_fill(self):
        engine = Engine()
        input_grid = Grid(2, 2)
        output_grid = Grid(2, 2)
        for y in range(2):
            for x in range(2):
                output_grid.set(x, y, 1)
        solution = engine.solve(input_grid, output_grid)
        assert solution.valid is True

    def test_solve_no_expected(self):
        engine = Engine()
        grid = Grid(2, 2)
        solution = engine.solve(grid)
        assert solution.grid is not None

    def test_solve_batch(self):
        engine = Engine()
        problems = [
            (Grid(2, 2), Grid(2, 2)),
            (Grid(3, 3), Grid(3, 3)),
        ]
        solutions = engine.solve_batch(problems)
        assert len(solutions) == 2
