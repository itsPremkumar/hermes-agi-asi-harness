"""PuzzleParser — parse ARC-AGI-3 training/test examples into structured format.

Converts raw ARC-AGI-3 puzzle JSON into a Puzzle dataclass with typed grids,
color palettes, and example pairs (input/output) for the solver pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# data types
# ---------------------------------------------------------------------------

@dataclass
class Grid:
    """A single 2D ARC-AGI-3 grid.

    Cells are integers 0-9 mapping to colors.  ``width`` and ``height``
    describe the bounding box; ``cells`` is a flat row-major list.
    """
    width: int
    height: int
    cells: list[int] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: list[list[int]]) -> "Grid":
        """Convert a 2D list of ints into a Grid."""
        if not raw:
            return cls(width=0, height=0, cells=[])
        height = len(raw)
        width = max((len(row) for row in raw), default=0)
        cells = []
        for row in raw:
            # pad ragged rows with 0
            padded = row + [0] * (width - len(row))
            cells.extend(padded[:width])
        return cls(width=width, height=height, cells=cells)

    def to_raw(self) -> list[list[int]]:
        """Convert back to a 2D list of ints."""
        if self.height == 0:
            return []
        return [
            self.cells[i * self.width:(i + 1) * self.width]
            for i in range(self.height)
        ]

    def color_palette(self) -> set[int]:
        """Return the set of distinct colors (non-zero) in the grid."""
        return {c for c in self.cells if c != 0}


@dataclass
class ExamplePair:
    """A single training/test pair with input grid and expected output grid."""
    input_grid: Grid
    output_grid: Grid


@dataclass
class Puzzle:
    """Structured representation of one ARC-AGI-3 puzzle."""
    puzzle_id: str
    train: list[ExamplePair] = field(default_factory=list)
    test: list[ExamplePair] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# parser
# ---------------------------------------------------------------------------

class PuzzleParseError(Exception):
    """Raised when a puzzle cannot be parsed."""


class PuzzleParser:
    """Parse ARC-AGI-3 puzzle JSON into :class:`Puzzle` objects.

    The parser validates the schema, normalises ragged grids, and logs
    each step with the puzzle_id for correlation.
    """

    def __init__(self) -> None:
        self._parse_count = 0

    def parse(self, raw: dict[str, Any], puzzle_id: str = "unknown") -> Puzzle:
        """Parse a raw ARC-AGI-3 puzzle dict into a Puzzle.

        Args:
            raw: the puzzle JSON dict (must have ``train`` and ``test`` keys,
                 each a list of ``{"input": [[...]], "output": [[...]]}``).
            puzzle_id: identifier used in log correlation.

        Returns:
            A structured :class:`Puzzle`.

        Raises:
            PuzzleParseError: if required keys are missing or grids are invalid.
        """
        self._parse_count += 1
        logger.info("parse_start puzzle_id=%s count=%d", puzzle_id, self._parse_count)

        if not isinstance(raw, dict):
            raise PuzzleParseError(
                f"puzzle_id={puzzle_id}: expected dict, got {type(raw).__name__}"
            )

        required = ("train", "test")
        for key in required:
            if key not in raw:
                raise PuzzleParseError(
                    f"puzzle_id={puzzle_id}: missing required key '{key}'"
                )

        try:
            train = self._parse_examples(raw["train"], puzzle_id, "train")
            test = self._parse_examples(raw["test"], puzzle_id, "test")
        except (TypeError, ValueError) as exc:
            raise PuzzleParseError(
                f"puzzle_id={puzzle_id}: example parse error: {exc}"
            ) from exc

        puzzle = Puzzle(
            puzzle_id=puzzle_id,
            train=train,
            test=test,
            metadata={
                k: v for k, v in raw.items()
                if k not in required and k != "id"
            },
        )
        logger.info(
            "parse_done puzzle_id=%s train_pairs=%d test_pairs=%d",
            puzzle_id, len(train), len(test),
        )
        return puzzle

    def _parse_examples(
        self,
        examples: Any,
        puzzle_id: str,
        split: str,
    ) -> list[ExamplePair]:
        """Parse a list of example pairs for one split."""
        if not isinstance(examples, list):
            raise PuzzleParseError(
                f"puzzle_id={puzzle_id} split={split}: expected list, got {type(examples).__name__}"
            )
        pairs: list[ExamplePair] = []
        for idx, ex in enumerate(examples):
            if not isinstance(ex, dict):
                raise PuzzleParseError(
                    f"puzzle_id={puzzle_id} split={split} idx={idx}: "
                    f"expected dict, got {type(ex).__name__}"
                )
            if "input" not in ex or "output" not in ex:
                raise PuzzleParseError(
                    f"puzzle_id={puzzle_id} split={split} idx={idx}: "
                    f"missing 'input' or 'output'"
                )
            try:
                input_grid = Grid.from_raw(ex["input"])
                output_grid = Grid.from_raw(ex["output"])
            except (TypeError, ValueError) as exc:
                raise PuzzleParseError(
                    f"puzzle_id={puzzle_id} split={split} idx={idx}: grid error: {exc}"
                ) from exc
            pairs.append(ExamplePair(input_grid=input_grid, output_grid=output_grid))
        return pairs

    @property
    def parse_count(self) -> int:
        """Return the number of puzzles successfully parsed."""
        return self._parse_count
