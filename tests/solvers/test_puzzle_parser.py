"""Tests for PuzzleParser."""
import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from harness.solvers.arc_agi_3.puzzle_parser import (
    Grid,
    Puzzle,
    PuzzleParser,
    PuzzleParseError,
    ExamplePair,
)


class TestGrid:
    def test_from_raw_basic(self):
        raw = [[1, 2], [3, 4]]
        g = Grid.from_raw(raw)
        assert g.width == 2
        assert g.height == 2
        assert g.cells == [1, 2, 3, 4]

    def test_from_raw_empty(self):
        g = Grid.from_raw([])
        assert g.width == 0
        assert g.height == 0
        assert g.cells == []

    def test_from_raw_ragged(self):
        raw = [[1, 2, 3], [4, 5]]
        g = Grid.from_raw(raw)
        assert g.width == 3
        assert g.height == 2
        assert g.cells == [1, 2, 3, 4, 5, 0]

    def test_to_raw_roundtrip(self):
        raw = [[1, 2], [3, 4]]
        g = Grid.from_raw(raw)
        assert g.to_raw() == raw

    def test_to_raw_empty(self):
        g = Grid(width=0, height=0, cells=[])
        assert g.to_raw() == []

    def test_color_palette(self):
        g = Grid.from_raw([[0, 1, 2], [0, 3, 0]])
        assert g.color_palette() == {1, 2, 3}

    def test_color_palette_empty(self):
        g = Grid.from_raw([[0, 0], [0, 0]])
        assert g.color_palette() == set()

    def test_color_palette_single(self):
        g = Grid.from_raw([[5]])
        assert g.color_palette() == {5}


class TestPuzzleParser:
    def _make_raw(self, puzzle_id="test_001"):
        return {
            "id": puzzle_id,
            "train": [
                {"input": [[1, 2], [3, 4]], "output": [[5, 6], [7, 8]]},
                {"input": [[0, 1], [2, 3]], "output": [[4, 5], [6, 7]]},
            ],
            "test": [
                {"input": [[9, 0], [1, 2]], "output": [[3, 4], [5, 6]]},
            ],
        }

    def test_parse_basic(self):
        parser = PuzzleParser()
        raw = self._make_raw()
        puzzle = parser.parse(raw, puzzle_id="test_001")
        assert puzzle.puzzle_id == "test_001"
        assert len(puzzle.train) == 2
        assert len(puzzle.test) == 1

    def test_parse_train_grids(self):
        parser = PuzzleParser()
        raw = self._make_raw()
        puzzle = parser.parse(raw, puzzle_id="test_001")
        assert puzzle.train[0].input_grid.cells == [1, 2, 3, 4]
        assert puzzle.train[0].output_grid.cells == [5, 6, 7, 8]

    def test_parse_test_grids(self):
        parser = PuzzleParser()
        raw = self._make_raw()
        puzzle = parser.parse(raw, puzzle_id="test_001")
        assert puzzle.test[0].input_grid.cells == [9, 0, 1, 2]
        assert puzzle.test[0].output_grid.cells == [3, 4, 5, 6]

    def test_parse_metadata(self):
        parser = PuzzleParser()
        raw = self._make_raw()
        raw["difficulty"] = "easy"
        puzzle = parser.parse(raw, puzzle_id="test_001")
        assert puzzle.metadata["difficulty"] == "easy"

    def test_parse_missing_train(self):
        parser = PuzzleParser()
        raw = {"test": [{"input": [[1]], "output": [[2]]}]}
        with pytest.raises(PuzzleParseError, match="missing required key 'train'"):
            parser.parse(raw, puzzle_id="test")

    def test_parse_missing_test(self):
        parser = PuzzleParser()
        raw = {"train": [{"input": [[1]], "output": [[2]]}]}
        with pytest.raises(PuzzleParseError, match="missing required key 'test'"):
            parser.parse(raw, puzzle_id="test")

    def test_parse_not_dict(self):
        parser = PuzzleParser()
        with pytest.raises(PuzzleParseError, match="expected dict"):
            parser.parse("not a dict", puzzle_id="test")

    def test_parse_example_missing_input(self):
        parser = PuzzleParser()
        raw = {"train": [{"output": [[1]]}], "test": [{"input": [[1]], "output": [[2]]}]}
        with pytest.raises(PuzzleParseError, match="missing 'input' or 'output'"):
            parser.parse(raw, puzzle_id="test")

    def test_parse_example_missing_output(self):
        parser = PuzzleParser()
        raw = {"train": [{"input": [[1]]}], "test": [{"input": [[1]], "output": [[2]]}]}
        with pytest.raises(PuzzleParseError, match="missing 'input' or 'output'"):
            parser.parse(raw, puzzle_id="test")

    def test_parse_train_not_list(self):
        parser = PuzzleParser()
        raw = {"train": "not a list", "test": [{"input": [[1]], "output": [[2]]}]}
        with pytest.raises(PuzzleParseError, match="expected list"):
            parser.parse(raw, puzzle_id="test")

    def test_parse_test_not_list(self):
        parser = PuzzleParser()
        raw = {"train": [{"input": [[1]], "output": [[2]]}], "test": "not a list"}
        with pytest.raises(PuzzleParseError, match="expected list"):
            parser.parse(raw, puzzle_id="test")

    def test_parse_count(self):
        parser = PuzzleParser()
        raw = self._make_raw()
        parser.parse(raw, puzzle_id="test_001")
        parser.parse(raw, puzzle_id="test_002")
        assert parser.parse_count == 2

    def test_parse_empty_train(self):
        parser = PuzzleParser()
        raw = {"train": [], "test": [{"input": [[1]], "output": [[2]]}]}
        puzzle = parser.parse(raw, puzzle_id="test")
        assert len(puzzle.train) == 0

    def test_parse_single_cell(self):
        parser = PuzzleParser()
        raw = {"train": [{"input": [[5]], "output": [[7]]}], "test": [{"input": [[3]], "output": [[9]]}]}
        puzzle = parser.parse(raw, puzzle_id="test")
        assert puzzle.train[0].input_grid.cells == [5]
        assert puzzle.train[0].output_grid.cells == [7]
