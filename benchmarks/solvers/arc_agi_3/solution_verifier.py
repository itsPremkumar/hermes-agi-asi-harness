"""SolutionVerifier — verify solutions against examples using evaluation.

Given a Solution and the original Puzzle, verifies each candidate against
the expected output grid. Uses a pluggable verification approach with
exact-match scoring and partial-credit metrics.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from .puzzle_parser import Grid, Puzzle
from .solution_generator import Candidate, Solution

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# data types
# ---------------------------------------------------------------------------

@dataclass
class VerificationResult:
    """Result of verifying a single candidate."""
    test_index: int
    passed: bool
    exact_match: bool = False
    cell_accuracy: float = 0.0  # fraction of cells matching
    shape_match: bool = False
    color_match: bool = False
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class SolutionVerification:
    """Complete verification result for a solution."""
    puzzle_id: str
    results: list[VerificationResult] = field(default_factory=list)
    all_passed: bool = False
    any_passed: bool = False
    average_accuracy: float = 0.0
    metadata: dict[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# verifier
# ---------------------------------------------------------------------------

class SolutionVerifier:
    """Verify candidate solutions against expected outputs.

    Supports exact-match verification (default) and partial-credit
    scoring based on cell-level accuracy.
    """

    def __init__(
        self,
        exact_match_threshold: float = 1.0,
        partial_credit: bool = False,
    ) -> None:
        self.exact_match_threshold = exact_match_threshold
        self.partial_credit = partial_credit
        self._verification_count = 0

    def verify(self, solution: Solution, puzzle: Puzzle) -> SolutionVerification:
        """Verify a solution against the puzzle's test pairs.

        Args:
            solution: the generated solution.
            puzzle: the original puzzle with expected outputs.

        Returns:
            A SolutionVerification with per-candidate results.
        """
        self._verification_count += 1
        logger.info("verify_start puzzle_id=%s", puzzle.puzzle_id)

        results: list[VerificationResult] = []
        for idx, candidate in enumerate(solution.candidates):
            if idx >= len(puzzle.test):
                break
            expected = puzzle.test[idx].output_grid
            result = self._verify_candidate(candidate, expected, idx)
            results.append(result)

        all_passed = all(r.passed for r in results) if results else False
        any_passed = any(r.passed for r in results) if results else False
        avg_accuracy = (
            sum(r.cell_accuracy for r in results) / len(results)
            if results else 0.0
        )

        verification = SolutionVerification(
            puzzle_id=puzzle.puzzle_id,
            results=results,
            all_passed=all_passed,
            any_passed=any_passed,
            average_accuracy=avg_accuracy,
            metadata={
                "strategy": solution.strategy,
                "num_test_pairs": len(puzzle.test),
                "num_candidates": len(solution.candidates),
            },
        )
        logger.info(
            "verify_done puzzle_id=%s all_passed=%s avg_accuracy=%.3f",
            puzzle.puzzle_id, all_passed, avg_accuracy,
        )
        return verification

    def _verify_candidate(
        self,
        candidate: Candidate,
        expected: Grid,
        test_index: int,
    ) -> VerificationResult:
        """Verify a single candidate against the expected output."""
        actual = candidate.grid

        # shape match
        shape_match = actual.width == expected.width and actual.height == expected.height

        # color palette match
        color_match = actual.color_palette() == expected.color_palette()

        # cell-level accuracy
        if shape_match:
            total_cells = len(expected.cells)
            if total_cells == 0:
                cell_accuracy = 1.0
            else:
                matching = sum(
                    1 for a, e in zip(actual.cells, expected.cells) if a == e
                )
                cell_accuracy = matching / total_cells
        else:
            # different shape - compute accuracy on overlapping region
            min_w = min(actual.width, expected.width)
            min_h = min(actual.height, expected.height)
            if min_w == 0 or min_h == 0:
                cell_accuracy = 0.0
            else:
                matching = 0
                for r in range(min_h):
                    for c in range(min_w):
                        if actual.cells[r * actual.width + c] == expected.cells[r * expected.width + c]:
                            matching += 1
                total_cells = max(len(actual.cells), len(expected.cells))
                cell_accuracy = matching / total_cells if total_cells > 0 else 0.0

        exact_match = shape_match and cell_accuracy == 1.0

        # passed if exact match or partial credit above threshold
        if self.partial_credit:
            passed = cell_accuracy >= self.exact_match_threshold
        else:
            passed = exact_match

        return VerificationResult(
            test_index=test_index,
            passed=passed,
            exact_match=exact_match,
            cell_accuracy=cell_accuracy,
            shape_match=shape_match,
            color_match=color_match,
            metadata={
                "actual_shape": (actual.width, actual.height),
                "expected_shape": (expected.width, expected.height),
            },
        )

    def verify_batch(
        self,
        solutions: list[Solution],
        puzzles: list[Puzzle],
    ) -> list[SolutionVerification]:
        """Verify multiple solutions."""
        if len(solutions) != len(puzzles):
            raise ValueError(
                f"solutions count ({len(solutions)}) != puzzles count ({len(puzzles)})"
            )
        return [self.verify(s, p) for s, p in zip(solutions, puzzles)]

    @property
    def verification_count(self) -> int:
        return self._verification_count
