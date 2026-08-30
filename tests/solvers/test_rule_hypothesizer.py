"""Tests for RuleHypothesizer."""
import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from harness.solvers.arc_agi_3.puzzle_parser import Grid, Puzzle, ExamplePair, PuzzleParser
from harness.solvers.arc_agi_3.rule_hypothesizer import (
    RuleHypothesizer,
    Hypothesis,
    HypothesisSet,
    _detect_identity,
    _detect_color_shift,
    _detect_rotation,
    _detect_reflection,
    _detect_scaling,
    _detect_flood_fill,
    _detect_crop_to_content,
    _detect_padding,
)


def _make_puzzle(puzzle_id="test"):
    return Puzzle(puzzle_id=puzzle_id)


def _pair(inp, out):
    return ExamplePair(input_grid=Grid.from_raw(inp), output_grid=Grid.from_raw(out))


class TestDetectors:
    def test_detect_identity_match(self):
        inp = Grid.from_raw([[1, 2], [3, 4]])
        out = Grid.from_raw([[1, 2], [3, 4]])
        matched, conf, meta = _detect_identity(inp, out)
        assert matched is True
        assert conf > 0.9

    def test_detect_identity_no_match(self):
        inp = Grid.from_raw([[1, 2], [3, 4]])
        out = Grid.from_raw([[1, 2], [3, 5]])
        matched, conf, meta = _detect_identity(inp, out)
        assert matched is False

    def test_detect_color_shift_match(self):
        inp = Grid.from_raw([[1, 2], [3, 0]])
        out = Grid.from_raw([[2, 3], [4, 0]])
        matched, conf, meta = _detect_color_shift(inp, out)
        assert matched is True
        assert "mapping" in meta

    def test_detect_color_shift_no_match(self):
        inp = Grid.from_raw([[1, 2], [3, 4]])
        out = Grid.from_raw([[1, 2], [3, 5]])
        matched, conf, meta = _detect_color_shift(inp, out)
        assert matched is False

    def test_detect_color_shift_identity_not_shift(self):
        inp = Grid.from_raw([[1, 2], [3, 4]])
        out = Grid.from_raw([[1, 2], [3, 4]])
        matched, conf, meta = _detect_color_shift(inp, out)
        assert matched is False  # identity mapping is not a color shift

    def test_detect_rotation_90(self):
        inp = Grid.from_raw([[1, 2], [3, 4]])
        out = Grid.from_raw([[3, 1], [4, 2]])
        matched, conf, meta = _detect_rotation(inp, out)
        assert matched is True
        assert meta["angle"] == 90

    def test_detect_rotation_180(self):
        inp = Grid.from_raw([[1, 2], [3, 4]])
        out = Grid.from_raw([[4, 3], [2, 1]])
        matched, conf, meta = _detect_rotation(inp, out)
        assert matched is True
        assert meta["angle"] == 180

    def test_detect_rotation_270(self):
        inp = Grid.from_raw([[1, 2], [3, 4]])
        out = Grid.from_raw([[2, 4], [1, 3]])
        matched, conf, meta = _detect_rotation(inp, out)
        assert matched is True
        assert meta["angle"] == 270

    def test_detect_rotation_no_match(self):
        inp = Grid.from_raw([[1, 2], [3, 4]])
        out = Grid.from_raw([[1, 2], [3, 5]])
        matched, conf, meta = _detect_rotation(inp, out)
        assert matched is False

    def test_detect_reflection_horizontal(self):
        inp = Grid.from_raw([[1, 2], [3, 4]])
        out = Grid.from_raw([[2, 1], [4, 3]])
        matched, conf, meta = _detect_reflection(inp, out)
        assert matched is True
        assert meta["axis"] == "horizontal"

    def test_detect_reflection_vertical(self):
        inp = Grid.from_raw([[1, 2], [3, 4]])
        out = Grid.from_raw([[3, 4], [1, 2]])
        matched, conf, meta = _detect_reflection(inp, out)
        assert matched is True
        assert meta["axis"] == "vertical"

    def test_detect_reflection_no_match(self):
        inp = Grid.from_raw([[1, 2], [3, 4]])
        out = Grid.from_raw([[1, 2], [3, 5]])
        matched, conf, meta = _detect_reflection(inp, out)
        assert matched is False

    def test_detect_scaling_up(self):
        inp = Grid.from_raw([[1, 2], [3, 4]])
        out = Grid.from_raw([[1, 1, 2, 2], [1, 1, 2, 2], [3, 3, 4, 4], [3, 3, 4, 4]])
        matched, conf, meta = _detect_scaling(inp, out)
        assert matched is True
        assert meta["scale_factor"] == 2

    def test_detect_scaling_down(self):
        inp = Grid.from_raw([[1, 1, 2, 2], [1, 1, 2, 2], [3, 3, 4, 4], [3, 3, 4, 4]])
        out = Grid.from_raw([[1, 2], [3, 4]])
        matched, conf, meta = _detect_scaling(inp, out)
        assert matched is True
        assert meta["scale_factor"] == -2

    def test_detect_scaling_no_match(self):
        inp = Grid.from_raw([[1, 2], [3, 4]])
        out = Grid.from_raw([[1, 2], [3, 5]])
        matched, conf, meta = _detect_scaling(inp, out)
        assert matched is False

    def test_detect_flood_fill(self):
        inp = Grid.from_raw([[1, 1, 1], [1, 0, 1], [1, 1, 1]])
        out = Grid.from_raw([[2, 2, 2], [2, 0, 2], [2, 2, 2]])
        matched, conf, meta = _detect_flood_fill(inp, out)
        assert matched is True
        assert meta["target_color"] == 2

    def test_detect_crop_to_content(self):
        inp = Grid.from_raw([[0, 0, 0], [0, 1, 2], [0, 3, 4]])
        out = Grid.from_raw([[1, 2], [3, 4]])
        matched, conf, meta = _detect_crop_to_content(inp, out)
        assert matched is True

    def test_detect_padding(self):
        inp = Grid.from_raw([[1, 2], [3, 4]])
        out = Grid.from_raw([[0, 0, 0, 0], [0, 1, 2, 0], [0, 3, 4, 0], [0, 0, 0, 0]])
        matched, conf, meta = _detect_padding(inp, out)
        assert matched is True


class TestRuleHypothesizer:
    def test_hypothesize_identity(self):
        h = RuleHypothesizer()
        puzzle = _make_puzzle("identity_test")
        puzzle.train = [_pair([[1, 2], [3, 4]], [[1, 2], [3, 4]])]
        result = h.hypothesize(puzzle)
        assert len(result.hypotheses) > 0
        assert result.top().name == "Identity"

    def test_hypothesize_color_shift(self):
        h = RuleHypothesizer()
        puzzle = _make_puzzle("cs_test")
        puzzle.train = [_pair([[1, 2], [3, 0]], [[2, 3], [4, 0]])]
        result = h.hypothesize(puzzle)
        names = [hyp.name for hyp in result.hypotheses]
        assert "Color Shift" in names

    def test_hypothesize_rotation_90(self):
        h = RuleHypothesizer()
        puzzle = _make_puzzle("rot_test")
        puzzle.train = [_pair([[1, 2], [3, 4]], [[3, 1], [4, 2]])]
        result = h.hypothesize(puzzle)
        names = [hyp.name for hyp in result.hypotheses]
        assert "Rotation" in names

    def test_hypothesize_empty_train(self):
        h = RuleHypothesizer()
        puzzle = _make_puzzle("empty_test")
        puzzle.train = []
        result = h.hypothesize(puzzle)
        assert len(result.hypotheses) == 0

    def test_hypothesize_top_returns_highest_confidence(self):
        h = RuleHypothesizer()
        puzzle = _make_puzzle("top_test")
        puzzle.train = [_pair([[1, 2], [3, 4]], [[1, 2], [3, 4]])]
        result = h.hypothesize(puzzle)
        top = result.top()
        if result.hypotheses:
            for hyp in result.hypotheses:
                assert top.confidence >= hyp.confidence

    def test_hypothesize_sorted_by_confidence(self):
        h = RuleHypothesizer()
        puzzle = _make_puzzle("sorted_test")
        puzzle.train = [_pair([[1, 2], [3, 4]], [[1, 2], [3, 4]])]
        result = h.hypothesize(puzzle)
        sorted_hyps = result.sorted_by_confidence()
        for i in range(len(sorted_hyps) - 1):
            assert sorted_hyps[i].confidence >= sorted_hyps[i + 1].confidence

    def test_hypothesize_multiple_examples(self):
        h = RuleHypothesizer()
        puzzle = _make_puzzle("multi_test")
        puzzle.train = [
            _pair([[1, 2], [3, 4]], [[1, 2], [3, 4]]),
            _pair([[5, 6], [7, 8]], [[5, 6], [7, 8]]),
        ]
        result = h.hypothesize(puzzle)
        assert len(result.hypotheses) > 0

    def test_hypothesize_count(self):
        h = RuleHypothesizer()
        puzzle = _make_puzzle("count_test")
        puzzle.train = [_pair([[1]], [[2]])]
        h.hypothesize(puzzle)
        h.hypothesize(puzzle)
        assert h.hypothesis_count == 2

    def test_hypothesis_post_init_clamps_confidence(self):
        hyp = Hypothesis(name="test", description="test", confidence=1.5)
        assert hyp.confidence == 1.0
        hyp2 = Hypothesis(name="test", description="test", confidence=-0.5)
        assert hyp2.confidence == 0.0
