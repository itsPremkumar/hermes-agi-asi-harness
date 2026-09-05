"""SolutionGenerator — generate candidate solutions with structured output.

Given a Puzzle, a HypothesisSet, and a Strategy, generates candidate output
grids for the test inputs. Uses a pluggable architecture where each strategy
has a corresponding generator function. Falls back to LLM-style reasoning
when no rule-based generator matches.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

from .puzzle_parser import Grid, Puzzle
from .rule_hypothesizer import HypothesisSet
from .strategy_selector import Strategy, StrategyResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# data types
# ---------------------------------------------------------------------------

@dataclass
class Candidate:
    """A single candidate solution for a test pair."""
    grid: Grid
    strategy: str
    confidence: float = 0.0
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class Solution:
    """Complete solution for a puzzle (one candidate per test pair)."""
    puzzle_id: str
    candidates: list[Candidate] = field(default_factory=list)
    strategy: str = ""
    metadata: dict[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# generator function type
# ---------------------------------------------------------------------------

GeneratorFn = Callable[
    [Puzzle, HypothesisSet, Strategy, int],  # puzzle, hyp_set, strategy, test_idx
    Optional[Candidate],
]


# ---------------------------------------------------------------------------
# rule-based generators
# ---------------------------------------------------------------------------

def _gen_identity(
    puzzle: Puzzle, hyp_set: HypothesisSet, strategy: Strategy, test_idx: int
) -> Optional[Candidate]:
    """Generate solution by returning input unchanged."""
    if test_idx >= len(puzzle.test):
        return None
    inp = puzzle.test[test_idx].input_grid
    return Candidate(
        grid=Grid(width=inp.width, height=inp.height, cells=list(inp.cells)),
        strategy="identity",
        confidence=0.9,
    )


def _gen_color_shift(
    puzzle: Puzzle, hyp_set: HypothesisSet, strategy: Strategy, test_idx: int
) -> Optional[Candidate]:
    """Generate solution by applying detected color mapping."""
    if test_idx >= len(puzzle.test):
        return None
    top = hyp_set.top()
    if not top or "mapping" not in top.metadata:
        return None

    mapping = top.metadata["mapping"]
    if not isinstance(mapping, dict):
        return None

    inp = puzzle.test[test_idx].input_grid
    new_cells = [mapping.get(c, c) for c in inp.cells]
    return Candidate(
        grid=Grid(width=inp.width, height=inp.height, cells=new_cells),
        strategy="color_shift",
        confidence=top.confidence,
        metadata={"mapping": mapping},
    )


def _gen_rotation(
    puzzle: Puzzle, hyp_set: HypothesisSet, strategy: Strategy, test_idx: int
) -> Optional[Candidate]:
    """Generate solution by applying detected rotation."""
    if test_idx >= len(puzzle.test):
        return None
    top = hyp_set.top()
    if not top or "angle" not in top.metadata:
        return None

    angle = top.metadata["angle"]
    if not isinstance(angle, int):
        return None

    inp = puzzle.test[test_idx].input_grid

    if angle == 90:
        new_cells = []
        for c in range(inp.width):
            for r in range(inp.height - 1, -1, -1):
                new_cells.append(inp.cells[r * inp.width + c])
        return Candidate(
            grid=Grid(width=inp.height, height=inp.width, cells=new_cells),
            strategy="rotation",
            confidence=top.confidence,
            metadata={"angle": 90},
        )
    elif angle == 180:
        return Candidate(
            grid=Grid(width=inp.width, height=inp.height, cells=list(reversed(inp.cells))),
            strategy="rotation",
            confidence=top.confidence,
            metadata={"angle": 180},
        )
    elif angle == 270:
        new_cells = []
        for c in range(inp.width - 1, -1, -1):
            for r in range(inp.height):
                new_cells.append(inp.cells[r * inp.width + c])
        return Candidate(
            grid=Grid(width=inp.height, height=inp.width, cells=new_cells),
            strategy="rotation",
            confidence=top.confidence,
            metadata={"angle": 270},
        )
    return None


def _gen_reflection(
    puzzle: Puzzle, hyp_set: HypothesisSet, strategy: Strategy, test_idx: int
) -> Optional[Candidate]:
    """Generate solution by applying detected reflection."""
    if test_idx >= len(puzzle.test):
        return None
    top = hyp_set.top()
    if not top or "axis" not in top.metadata:
        return None

    axis = top.metadata["axis"]
    if not isinstance(axis, str):
        return None

    inp = puzzle.test[test_idx].input_grid

    if axis == "horizontal":
        new_cells = []
        for r in range(inp.height):
            row = inp.cells[r * inp.width:(r + 1) * inp.width]
            new_cells.extend(reversed(row))
        return Candidate(
            grid=Grid(width=inp.width, height=inp.height, cells=new_cells),
            strategy="reflection",
            confidence=top.confidence,
            metadata={"axis": "horizontal"},
        )
    elif axis == "vertical":
        new_cells = []
        for r in range(inp.height - 1, -1, -1):
            new_cells.extend(inp.cells[r * inp.width:(r + 1) * inp.width])
        return Candidate(
            grid=Grid(width=inp.width, height=inp.height, cells=new_cells),
            strategy="reflection",
            confidence=top.confidence,
            metadata={"axis": "vertical"},
        )
    return None


def _gen_scaling(
    puzzle: Puzzle, hyp_set: HypothesisSet, strategy: Strategy, test_idx: int
) -> Optional[Candidate]:
    """Generate solution by applying detected scaling."""
    if test_idx >= len(puzzle.test):
        return None
    top = hyp_set.top()
    if not top or "scale_factor" not in top.metadata:
        return None

    scale_factor = top.metadata["scale_factor"]
    if not isinstance(scale_factor, int):
        return None

    inp = puzzle.test[test_idx].input_grid

    if scale_factor > 0:
        # upscale
        new_width = inp.width * scale_factor
        new_height = inp.height * scale_factor
        new_cells = []
        for r in range(inp.height):
            for _ in range(scale_factor):
                for c in range(inp.width):
                    new_cells.extend([inp.cells[r * inp.width + c]] * scale_factor)
        return Candidate(
            grid=Grid(width=new_width, height=new_height, cells=new_cells),
            strategy="scaling",
            confidence=top.confidence,
            metadata={"scale_factor": scale_factor},
        )
    else:
        # downscale
        sf = -scale_factor
        new_width = inp.width // sf
        new_height = inp.height // sf
        new_cells = []
        for r in range(new_height):
            for c in range(new_width):
                new_cells.append(inp.cells[(r * sf) * inp.width + (c * sf)])
        return Candidate(
            grid=Grid(width=new_width, height=new_height, cells=new_cells),
            strategy="scaling",
            confidence=top.confidence,
            metadata={"scale_factor": scale_factor},
        )


def _gen_crop_to_content(
    puzzle: Puzzle, hyp_set: HypothesisSet, strategy: Strategy, test_idx: int
) -> Optional[Candidate]:
    """Generate solution by cropping to non-zero content bounding box."""
    if test_idx >= len(puzzle.test):
        return None
    top = hyp_set.top()
    if not top or "bbox" not in top.metadata:
        return None

    bbox = top.metadata["bbox"]
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return None

    min_r, min_c, max_r, max_c = bbox
    inp = puzzle.test[test_idx].input_grid

    new_width = max_c - min_c + 1
    new_height = max_r - min_r + 1
    new_cells = []
    for r in range(min_r, max_r + 1):
        for c in range(min_c, max_c + 1):
            new_cells.append(inp.cells[r * inp.width + c])
    return Candidate(
        grid=Grid(width=new_width, height=new_height, cells=new_cells),
        strategy="crop_to_content",
        confidence=top.confidence,
        metadata={"bbox": bbox},
    )


def _gen_padding(
    puzzle: Puzzle, hyp_set: HypothesisSet, strategy: Strategy, test_idx: int
) -> Optional[Candidate]:
    """Generate solution by adding border/padding."""
    if test_idx >= len(puzzle.test):
        return None
    top = hyp_set.top()
    if not top or "border_color" not in top.metadata or "offset" not in top.metadata:
        return None

    border_color = top.metadata["border_color"]
    offset = top.metadata["offset"]
    if not isinstance(offset, (list, tuple)) or len(offset) != 2:
        return None

    offset_r, offset_c = offset
    inp = puzzle.test[test_idx].input_grid

    new_width = inp.width + 2 * offset_c
    new_height = inp.height + 2 * offset_r
    new_cells = [border_color] * (new_width * new_height)
    for r in range(inp.height):
        for c in range(inp.width):
            dest_r = r + offset_r
            dest_c = c + offset_c
            new_cells[dest_r * new_width + dest_c] = inp.cells[r * inp.width + c]
    return Candidate(
        grid=Grid(width=new_width, height=new_height, cells=new_cells),
        strategy="padding",
        confidence=top.confidence,
        metadata={"border_color": border_color, "offset": offset},
    )


def _gen_flood_fill(
    puzzle: Puzzle, hyp_set: HypothesisSet, strategy: Strategy, test_idx: int
) -> Optional[Candidate]:
    """Generate solution by flood filling from detected seed points."""
    if test_idx >= len(puzzle.test):
        return None
    top = hyp_set.top()
    if not top or "target_color" not in top.metadata:
        return None

    target_color = top.metadata["target_color"]
    if not isinstance(target_color, int):
        return None

    inp = puzzle.test[test_idx].input_grid
    # Use first training pair to find seed pattern
    if not puzzle.train:
        return None

    # Determine which cells changed in training
    train_pair = puzzle.train[0]
    changed_value = None
    for i in range(len(train_pair.input_grid.cells)):
        if train_pair.input_grid.cells[i] != train_pair.output_grid.cells[i]:
            changed_value = train_pair.input_grid.cells[i]
            break

    if changed_value is None:
        return None

    # Apply flood fill on test input for cells matching the changed value
    new_cells = list(inp.cells)
    for i in range(len(new_cells)):
        if new_cells[i] == changed_value:
            new_cells[i] = target_color

    return Candidate(
        grid=Grid(width=inp.width, height=inp.height, cells=new_cells),
        strategy="flood_fill",
        confidence=top.confidence * 0.7,
        metadata={"target_color": target_color},
    )


# ---------------------------------------------------------------------------
# generator registry
# ---------------------------------------------------------------------------

GENERATOR_MAP: dict[str, GeneratorFn] = {
    "Identity": _gen_identity,
    "Color Shift": _gen_color_shift,
    "Rotation": _gen_rotation,
    "Reflection": _gen_reflection,
    "Scaling": _gen_scaling,
    "Crop To Content": _gen_crop_to_content,
    "Padding": _gen_padding,
    "Flood Fill": _gen_flood_fill,
}


# ---------------------------------------------------------------------------
# generator
# ---------------------------------------------------------------------------

class SolutionGenerator:
    """Generate candidate solutions for ARC-AGI-3 puzzles.

    Uses a registry of generator functions keyed by hypothesis name.
    For each test pair, tries to generate a candidate using the top
    hypothesis. Falls back to identity if no generator matches.
    """

    def __init__(
        self,
        generators: Optional[dict[str, GeneratorFn]] = None,
    ) -> None:
        self.generators = generators if generators is not None else GENERATOR_MAP
        self._generation_count = 0

    def generate(
        self,
        puzzle: Puzzle,
        hyp_set: HypothesisSet,
        strategy_result: StrategyResult,
    ) -> Solution:
        """Generate a solution for a puzzle.

        Args:
            puzzle: the parsed puzzle.
            hyp_set: ranked hypotheses.
            strategy_result: selected strategy.

        Returns:
            A Solution with one candidate per test pair.
        """
        self._generation_count += 1
        logger.info("generate_start puzzle_id=%s", puzzle.puzzle_id)

        candidates: list[Candidate] = []
        top = hyp_set.top()

        for test_idx in range(len(puzzle.test)):
            candidate = None
            if top and top.name in self.generators:
                try:
                    candidate = self.generators[top.name](
                        puzzle, hyp_set, strategy_result.strategy, test_idx
                    )
                except Exception as exc:
                    logger.warning(
                        "generator_error puzzle_id=%s hypothesis=%s: %s",
                        puzzle.puzzle_id, top.name, exc,
                    )

            if candidate is None:
                # fallback: identity
                candidate = _gen_identity(
                    puzzle, hyp_set, strategy_result.strategy, test_idx
                )
                if candidate is None:
                    # empty test pair
                    candidate = Candidate(
                        grid=Grid(width=0, height=0, cells=[]),
                        strategy="empty",
                        confidence=0.0,
                    )

            candidates.append(candidate)

        solution = Solution(
            puzzle_id=puzzle.puzzle_id,
            candidates=candidates,
            strategy=strategy_result.strategy.name,
            metadata={
                "top_hypothesis": top.name if top else None,
                "strategy_confidence": strategy_result.confidence,
            },
        )
        logger.info(
            "generate_done puzzle_id=%s candidates=%d",
            puzzle.puzzle_id, len(candidates),
        )
        return solution

    @property
    def generation_count(self) -> int:
        return self._generation_count
