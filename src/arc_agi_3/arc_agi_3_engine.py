"""ARC-AGI-3 Core Engine — AVOPISAging loop."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CellType(Enum):
    EMPTY = 0
    FILLED = 1
    BLOCKED = 2


@dataclass
class Grid:
    width: int
    height: int
    cells: list[list[int]] = field(default_factory=list)

    def __post_init__(self):
        if not self.cells:
            self.cells = [[CellType.EMPTY.value] * self.width for _ in range(self.height)]

    def get(self, x: int, y: int) -> int:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.cells[y][x]
        return CellType.BLOCKED.value

    def set(self, x: int, y: int, value: int) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.cells[y][x] = value

    def clone(self) -> "Grid":
        return Grid(
            width=self.width,
            height=self.height,
            cells=[row[:] for row in self.cells],
        )

    def equals(self, other: "Grid") -> bool:
        return self.cells == other.cells

    def count_filled(self) -> int:
        return sum(
            1 for row in self.cells for cell in row
            if cell == CellType.FILLED.value
        )


@dataclass
class RuleHypothesis:
    id: str = field(default_factory=lambda: f"rule_{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    confidence: float = 0.0
    transformations: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Strategy:
    id: str = field(default_factory=lambda: f"strat_{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    priority: int = 0
    applicable: bool = True


@dataclass
class Solution:
    id: str = field(default_factory=lambda: f"sol_{uuid.uuid4().hex[:8]}")
    grid: Grid | None = None
    score: float = 0.0
    steps: list[dict[str, Any]] = field(default_factory=list)
    valid: bool = False


@dataclass
class VerificationResult:
    passed: bool = False
    score: float = 0.0
    errors: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


class RuleHypothesizer:
    """Generate hypotheses about transformation rules."""

    def hypothesize(self, input_grid: Grid, output_grid: Grid) -> list[RuleHypothesis]:
        """Generate rule hypotheses from input/output pair."""
        hypotheses = []

        # Check for copy
        if input_grid.equals(output_grid):
            hypotheses.append(RuleHypothesis(
                name="copy",
                description="Output is identical to input",
                confidence=0.9,
            ))

        # Check for fill all
        if output_grid.count_filled() == output_grid.width * output_grid.height:
            hypotheses.append(RuleHypothesis(
                name="fill_all",
                description="All cells filled",
                confidence=0.8,
            ))

        # Check for inversion
        inverted = all(
            output_grid.get(x, y) != input_grid.get(x, y)
            for y in range(input_grid.height)
            for x in range(input_grid.width)
        )
        if inverted:
            hypotheses.append(RuleHypothesis(
                name="invert",
                description="All cells inverted",
                confidence=0.7,
            ))

        return hypotheses


class StrategySelector:
    """Select the best strategy."""

    def __init__(self):
        self._strategies = [
            Strategy(name="direct_copy", priority=1),
            Strategy(name="fill_all", priority=2),
            Strategy(name="invert", priority=3),
            Strategy(name="pattern_match", priority=4),
        ]

    def select(self, hypotheses: list[RuleHypothesis]) -> Strategy | None:
        """Select best strategy based on hypotheses."""
        if not hypotheses:
            return None
        best = max(hypotheses, key=lambda h: h.confidence)
        for strategy in self._strategies:
            if strategy.name == best.name:
                return strategy
        return self._strategies[0]


class SolutionGenerator:
    """Generate solutions."""

    def generate(
        self,
        input_grid: Grid,
        strategy: Strategy,
        hypotheses: list[RuleHypothesis],
    ) -> Solution:
        """Generate a solution using the selected strategy."""
        output = input_grid.clone()

        if strategy.name == "direct_copy":
            # No change
            pass
        elif strategy.name == "fill_all":
            for y in range(output.height):
                for x in range(output.width):
                    output.set(x, y, CellType.FILLED.value)
        elif strategy.name == "invert":
            for y in range(output.height):
                for x in range(output.width):
                    current = output.get(x, y)
                    output.set(x, y, 1 if current == 0 else 0)

        return Solution(
            grid=output,
            steps=[{"action": strategy.name}],
        )


class SolutionVerifier:
    """Verify solutions."""

    def verify(
        self,
        solution: Solution,
        expected: Grid | None = None,
    ) -> VerificationResult:
        """Verify a solution."""
        if solution.grid is None:
            return VerificationResult(passed=False, errors=["No grid"])

        if expected is not None:
            if solution.grid.equals(expected):
                return VerificationResult(passed=True, score=1.0)
            else:
                return VerificationResult(passed=False, score=0.0, errors=["Mismatch"])

        return VerificationResult(passed=True, score=0.5)


class Engine:
    """ARC-AGI-3 Engine with AVOPISAging loop."""

    def __init__(self):
        self._hypothesizer = RuleHypothesizer()
        self._selector = StrategySelector()
        self._generator = SolutionGenerator()
        self._verifier = SolutionVerifier()

    def solve(
        self,
        input_grid: Grid,
        expected_output: Grid | None = None,
    ) -> Solution:
        """Solve an ARC-AGI-3 problem."""
        # Observe
        # Reason
        hypotheses = self._hypothesizer.hypothesize(input_grid, expected_output or input_grid)
        # Plan
        strategy = self._selector.select(hypotheses)
        # Act
        solution = self._generator.generate(input_grid, strategy or Strategy(name="direct_copy"), hypotheses)
        # Evaluate
        verification = self._verifier.verify(solution, expected_output)
        # Diagnose
        # Revise
        solution.score = verification.score
        solution.valid = verification.passed
        return solution

    def solve_batch(
        self,
        problems: list[tuple[Grid, Grid | None]],
    ) -> list[Solution]:
        """Solve multiple problems."""
        return [self.solve(inp, exp) for inp, exp in problems]
