"""benchmark.py — ARC-AGI-3 evaluation harness.

Provides a benchmark runner that evaluates the AVOPISAging engine on a
dataset of ARC-AGI-3 puzzles. Collects metrics (pass rate, accuracy,
timing) and supports multiple benchmark modes.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .engine import AgentState, AVOPISAgingEngine
from .puzzle_parser import PuzzleParser
from .rule_hypothesizer import RuleHypothesizer
from .strategy_selector import StrategySelector
from .solution_generator import SolutionGenerator
from .solution_verifier import SolutionVerifier

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# data types
# ---------------------------------------------------------------------------

@dataclass
class PuzzleResult:
    """Result for a single puzzle in the benchmark."""
    puzzle_id: str
    passed: bool = False
    accuracy: float = 0.0
    iterations: int = 0
    solve_time: float = 0.0
    strategy: str = ""
    error: Optional[str] = None


@dataclass
class BenchmarkReport:
    """Complete benchmark report."""
    results: list[PuzzleResult] = field(default_factory=list)
    total_puzzles: int = 0
    passed_count: int = 0
    failed_count: int = 0
    average_accuracy: float = 0.0
    total_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        if self.total_puzzles == 0:
            return 0.0
        return self.passed_count / self.total_puzzles


# ---------------------------------------------------------------------------
# benchmark
# ---------------------------------------------------------------------------

class ARCAGI3Benchmark:
    """ARC-AGI-3 evaluation harness.

    Runs the AVOPISAging engine on a dataset of puzzles and collects
    aggregate metrics.
    """

    def __init__(
        self,
        engine: Optional[AVOPISAgingEngine] = None,
        max_iterations: int = 5,
    ) -> None:
        self.engine = engine or AVOPISAgingEngine(max_iterations=max_iterations)
        self._run_count = 0

    def run(
        self,
        puzzles: list[dict[str, Any]],
    ) -> BenchmarkReport:
        """Run the benchmark on a list of puzzles.

        Args:
            puzzles: list of raw puzzle dicts. Each dict may contain an
                     "id" key for identification.

        Returns:
            A BenchmarkReport with results and aggregate metrics.
        """
        self._run_count += 1
        logger.info("benchmark_start puzzles=%d run_id=%d", len(puzzles), self._run_count)

        start_time = time.time()
        results: list[PuzzleResult] = []

        for idx, raw in enumerate(puzzles):
            puzzle_id = raw.get("id", f"puzzle_{idx}")
            puzzle_start = time.time()

            try:
                state = self.engine.solve(raw, puzzle_id=puzzle_id)
                puzzle_time = time.time() - puzzle_start

                passed = state.done and (
                    state.verification.all_passed if state.verification else False
                )
                accuracy = (
                    state.verification.average_accuracy if state.verification else 0.0
                )
                strategy = (
                    state.strategy_result.strategy.name if state.strategy_result else ""
                )

                results.append(PuzzleResult(
                    puzzle_id=puzzle_id,
                    passed=passed,
                    accuracy=accuracy,
                    iterations=state.iteration,
                    solve_time=puzzle_time,
                    strategy=strategy,
                    error=state.error,
                ))
            except Exception as exc:
                logger.error("benchmark_error puzzle_id=%s: %s", puzzle_id, exc)
                results.append(PuzzleResult(
                    puzzle_id=puzzle_id,
                    passed=False,
                    solve_time=time.time() - puzzle_start,
                    error=str(exc),
                ))

        total_time = time.time() - start_time
        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count
        avg_accuracy = (
            sum(r.accuracy for r in results) / len(results) if results else 0.0
        )

        report = BenchmarkReport(
            results=results,
            total_puzzles=len(results),
            passed_count=passed_count,
            failed_count=failed_count,
            average_accuracy=avg_accuracy,
            total_time=total_time,
            metadata={
                "run_id": self._run_count,
                "max_iterations": self.engine.max_iterations,
            },
        )

        logger.info(
            "benchmark_done pass_rate=%.2f avg_accuracy=%.3f total_time=%.2f",
            report.pass_rate, report.average_accuracy, report.total_time,
        )
        return report

    @property
    def run_count(self) -> int:
        return self._run_count


# ---------------------------------------------------------------------------
# sample dataset for testing
# ---------------------------------------------------------------------------

def get_sample_puzzles() -> list[dict[str, Any]]:
    """Return a small sample dataset of ARC-AGI-3 puzzles for testing.

    These are simplified puzzles covering common transformations:
    identity, color shift, rotation, reflection, scaling, crop, padding.
    """
    return [
        {
            "id": "identity_001",
            "train": [
                {"input": [[1, 2], [3, 4]], "output": [[1, 2], [3, 4]]},
                {"input": [[5, 6], [7, 8]], "output": [[5, 6], [7, 8]]},
            ],
            "test": [
                {"input": [[9, 0], [1, 2]], "output": [[9, 0], [1, 2]]},
            ],
        },
        {
            "id": "color_shift_001",
            "train": [
                {"input": [[1, 2], [3, 0]], "output": [[2, 3], [4, 0]]},
                {"input": [[0, 1], [2, 3]], "output": [[0, 2], [3, 4]]},
            ],
            "test": [
                {"input": [[1, 0], [0, 2]], "output": [[2, 0], [0, 3]]},
            ],
        },
        {
            "id": "rotation_90_001",
            "train": [
                {"input": [[1, 2], [3, 4]], "output": [[3, 1], [4, 2]]},
                {"input": [[5, 6], [7, 8]], "output": [[7, 5], [8, 6]]},
            ],
            "test": [
                {"input": [[1, 0], [0, 2]], "output": [[0, 1], [2, 0]]},
            ],
        },
        {
            "id": "rotation_180_001",
            "train": [
                {"input": [[1, 2], [3, 4]], "output": [[4, 3], [2, 1]]},
                {"input": [[5, 6], [7, 8]], "output": [[8, 7], [6, 5]]},
            ],
            "test": [
                {"input": [[1, 2], [3, 0]], "output": [[0, 3], [2, 1]]},
            ],
        },
        {
            "id": "rotation_270_001",
            "train": [
                {"input": [[1, 2], [3, 4]], "output": [[2, 4], [1, 3]]},
                {"input": [[5, 6], [7, 8]], "output": [[6, 8], [5, 7]]},
            ],
            "test": [
                {"input": [[1, 2], [3, 0]], "output": [[2, 0], [1, 3]]},
            ],
        },
        {
            "id": "reflection_h_001",
            "train": [
                {"input": [[1, 2], [3, 4]], "output": [[2, 1], [4, 3]]},
                {"input": [[5, 6], [7, 8]], "output": [[6, 5], [8, 7]]},
            ],
            "test": [
                {"input": [[1, 0], [2, 3]], "output": [[0, 1], [3, 2]]},
            ],
        },
        {
            "id": "reflection_v_001",
            "train": [
                {"input": [[1, 2], [3, 4]], "output": [[3, 4], [1, 2]]},
                {"input": [[5, 6], [7, 8]], "output": [[7, 8], [5, 6]]},
            ],
            "test": [
                {"input": [[1, 2], [0, 3]], "output": [[0, 3], [1, 2]]},
            ],
        },
        {
            "id": "scaling_up_001",
            "train": [
                {"input": [[1, 2], [3, 4]], "output": [[1, 1, 2, 2], [1, 1, 2, 2], [3, 3, 4, 4], [3, 3, 4, 4]]},
                {"input": [[5, 6], [7, 8]], "output": [[5, 5, 6, 6], [5, 5, 6, 6], [7, 7, 8, 8], [7, 7, 8, 8]]},
            ],
            "test": [
                {"input": [[1, 0], [0, 2]], "output": [[1, 1, 0, 0], [1, 1, 0, 0], [0, 0, 2, 2], [0, 0, 2, 2]]},
            ],
        },
        {
            "id": "crop_001",
            "train": [
                {"input": [[0, 0, 0], [0, 1, 2], [0, 3, 4]], "output": [[1, 2], [3, 4]]},
                {"input": [[0, 0, 0, 0], [0, 5, 6, 0], [0, 7, 8, 0], [0, 0, 0, 0]], "output": [[5, 6], [7, 8]]},
            ],
            "test": [
                {"input": [[0, 0, 0], [0, 1, 0], [0, 0, 2]], "output": [[1, 0], [0, 2]]},
            ],
        },
        {
            "id": "padding_001",
            "train": [
                {"input": [[1, 2], [3, 4]], "output": [[0, 0, 0, 0], [0, 1, 2, 0], [0, 3, 4, 0], [0, 0, 0, 0]]},
                {"input": [[5, 6], [7, 8]], "output": [[0, 0, 0, 0], [0, 5, 6, 0], [0, 7, 8, 0], [0, 0, 0, 0]]},
            ],
            "test": [
                {"input": [[1, 0], [0, 2]], "output": [[0, 0, 0, 0], [0, 1, 0, 0], [0, 0, 2, 0], [0, 0, 0, 0]]},
            ],
        },
    ]
