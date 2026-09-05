"""Tests for SolutionGenerator."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from benchmarks.solvers.arc_agi_3.puzzle_parser import ExamplePair, Grid, Puzzle
from benchmarks.solvers.arc_agi_3.rule_hypothesizer import Hypothesis, HypothesisSet
from benchmarks.solvers.arc_agi_3.solution_generator import (
    GENERATOR_MAP,
    SolutionGenerator,
    _gen_color_shift,
    _gen_crop_to_content,
    _gen_flood_fill,
    _gen_identity,
    _gen_padding,
    _gen_reflection,
    _gen_rotation,
    _gen_scaling,
)
from benchmarks.solvers.arc_agi_3.strategy_selector import STRATEGY_RULE_BASED, StrategyResult


def _pair(inp, out):
    return ExamplePair(input_grid=Grid.from_raw(inp), output_grid=Grid.from_raw(out))


def _puzzle_with_test(puzzle_id="test"):
    p = Puzzle(puzzle_id=puzzle_id)
    p.test = [_pair([[1, 2], [3, 4]], [[1, 2], [3, 4]])]
    return p


def _hyp_set(name="Identity", confidence=0.9):
    hs = HypothesisSet(puzzle_id="test")
    hs.hypotheses = [Hypothesis(name=name, description="test", confidence=confidence)]
    return hs


class TestGeneratorFunctions:
    def test_gen_identity(self):
        p = _puzzle_with_test()
        hs = _hyp_set("Identity")
        result = _gen_identity(p, hs, STRATEGY_RULE_BASED, 0)
        assert result is not None
        assert result.grid.cells == [1, 2, 3, 4]
        assert result.strategy == "identity"

    def test_gen_color_shift(self):
        p = _puzzle_with_test()
        hs = _hyp_set("Color Shift")
        hs.top().metadata["mapping"] = {1: 2, 2: 3, 3: 4, 4: 5}
        result = _gen_color_shift(p, hs, STRATEGY_RULE_BASED, 0)
        assert result is not None
        assert result.grid.cells == [2, 3, 4, 5]

    def test_gen_rotation_90(self):
        p = _puzzle_with_test()
        hs = _hyp_set("Rotation")
        hs.top().metadata["angle"] = 90
        result = _gen_rotation(p, hs, STRATEGY_RULE_BASED, 0)
        assert result is not None
        assert result.grid.cells == [3, 1, 4, 2]

    def test_gen_rotation_180(self):
        p = _puzzle_with_test()
        hs = _hyp_set("Rotation")
        hs.top().metadata["angle"] = 180
        result = _gen_rotation(p, hs, STRATEGY_RULE_BASED, 0)
        assert result is not None
        assert result.grid.cells == [4, 3, 2, 1]

    def test_gen_rotation_270(self):
        p = _puzzle_with_test()
        hs = _hyp_set("Rotation")
        hs.top().metadata["angle"] = 270
        result = _gen_rotation(p, hs, STRATEGY_RULE_BASED, 0)
        assert result is not None
        assert result.grid.cells == [2, 4, 1, 3]

    def test_gen_reflection_horizontal(self):
        p = _puzzle_with_test()
        hs = _hyp_set("Reflection")
        hs.top().metadata["axis"] = "horizontal"
        result = _gen_reflection(p, hs, STRATEGY_RULE_BASED, 0)
        assert result is not None
        assert result.grid.cells == [2, 1, 4, 3]

    def test_gen_reflection_vertical(self):
        p = _puzzle_with_test()
        hs = _hyp_set("Reflection")
        hs.top().metadata["axis"] = "vertical"
        result = _gen_reflection(p, hs, STRATEGY_RULE_BASED, 0)
        assert result is not None
        assert result.grid.cells == [3, 4, 1, 2]

    def test_gen_scaling_up(self):
        p = _puzzle_with_test()
        hs = _hyp_set("Scaling")
        hs.top().metadata["scale_factor"] = 2
        result = _gen_scaling(p, hs, STRATEGY_RULE_BASED, 0)
        assert result is not None
        assert result.grid.width == 4
        assert result.grid.height == 4

    def test_gen_scaling_down(self):
        p = _puzzle_with_test()
        hs = _hyp_set("Scaling")
        hs.top().metadata["scale_factor"] = -2
        result = _gen_scaling(p, hs, STRATEGY_RULE_BASED, 0)
        assert result is not None
        assert result.grid.width == 1
        assert result.grid.height == 1

    def test_gen_crop_to_content(self):
        p = _puzzle_with_test()
        hs = _hyp_set("Crop To Content")
        hs.top().metadata["bbox"] = (0, 0, 1, 1)
        result = _gen_crop_to_content(p, hs, STRATEGY_RULE_BASED, 0)
        assert result is not None
        assert result.grid.width == 2
        assert result.grid.height == 2

    def test_gen_padding(self):
        p = _puzzle_with_test()
        hs = _hyp_set("Padding")
        hs.top().metadata["border_color"] = 0
        hs.top().metadata["offset"] = (1, 1)
        result = _gen_padding(p, hs, STRATEGY_RULE_BASED, 0)
        assert result is not None
        assert result.grid.width == 4
        assert result.grid.height == 4

    def test_gen_flood_fill(self):
        p = Puzzle(puzzle_id="ff_test")
        p.train = [_pair([[1, 1, 1], [1, 0, 1], [1, 1, 1]],
                        [[2, 2, 2], [2, 0, 2], [2, 2, 2]])]
        p.test = [_pair([[1, 1, 1], [1, 0, 1], [1, 1, 1]],
                        [[2, 2, 2], [2, 0, 2], [2, 2, 2]])]
        hs = _hyp_set("Flood Fill")
        hs.top().metadata["target_color"] = 2
        result = _gen_flood_fill(p, hs, STRATEGY_RULE_BASED, 0)
        assert result is not None
        assert result.grid.cells == [2, 2, 2, 2, 0, 2, 2, 2, 2]

    def test_gen_identity_out_of_range(self):
        p = _puzzle_with_test()
        hs = _hyp_set("Identity")
        result = _gen_identity(p, hs, STRATEGY_RULE_BASED, 5)
        assert result is None


class TestSolutionGenerator:
    def test_generate_identity(self):
        gen = SolutionGenerator()
        p = _puzzle_with_test()
        hs = _hyp_set("Identity")
        sr = StrategyResult(strategy=STRATEGY_RULE_BASED, confidence=0.95)
        sol = gen.generate(p, hs, sr)
        assert sol.puzzle_id == "test"
        assert len(sol.candidates) == 1
        assert sol.candidates[0].grid.cells == [1, 2, 3, 4]

    def test_generate_fallback_to_identity(self):
        gen = SolutionGenerator()
        p = _puzzle_with_test()
        hs = _hyp_set("Unknown Transformation")
        sr = StrategyResult(strategy=STRATEGY_RULE_BASED, confidence=0.5)
        sol = gen.generate(p, hs, sr)
        assert sol.puzzle_id == "test"
        assert len(sol.candidates) == 1
        # should fallback to identity
        assert sol.candidates[0].grid.cells == [1, 2, 3, 4]

    def test_generate_multiple_test_pairs(self):
        gen = SolutionGenerator()
        p = Puzzle(puzzle_id="multi_test")
        p.test = [
            _pair([[1, 2], [3, 4]], [[1, 2], [3, 4]]),
            _pair([[5, 6], [7, 8]], [[5, 6], [7, 8]]),
        ]
        hs = _hyp_set("Identity")
        sr = StrategyResult(strategy=STRATEGY_RULE_BASED, confidence=0.95)
        sol = gen.generate(p, hs, sr)
        assert len(sol.candidates) == 2

    def test_generate_strategy_field(self):
        gen = SolutionGenerator()
        p = _puzzle_with_test()
        hs = _hyp_set("Identity")
        sr = StrategyResult(strategy=STRATEGY_RULE_BASED, confidence=0.95)
        sol = gen.generate(p, hs, sr)
        assert sol.strategy == "rule_based"

    def test_generate_count(self):
        gen = SolutionGenerator()
        p = _puzzle_with_test()
        hs = _hyp_set("Identity")
        sr = StrategyResult(strategy=STRATEGY_RULE_BASED, confidence=0.95)
        gen.generate(p, hs, sr)
        gen.generate(p, hs, sr)
        assert gen.generation_count == 2

    def test_generator_map_has_expected_keys(self):
        expected = {
            "Identity", "Color Shift", "Rotation", "Reflection",
            "Scaling", "Crop To Content", "Padding", "Flood Fill",
        }
        assert set(GENERATOR_MAP.keys()) == expected

    def test_solution_metadata(self):
        gen = SolutionGenerator()
        p = _puzzle_with_test()
        hs = _hyp_set("Identity")
        sr = StrategyResult(strategy=STRATEGY_RULE_BASED, confidence=0.95)
        sol = gen.generate(p, hs, sr)
        assert sol.metadata["top_hypothesis"] == "Identity"
        assert sol.metadata["strategy_confidence"] == 0.95
