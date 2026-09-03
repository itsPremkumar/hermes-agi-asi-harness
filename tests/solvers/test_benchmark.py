"""Tests for ARCAGI3Benchmark."""
import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from harness.solvers.arc_agi_3.benchmark import (
    ARCAGI3Benchmark,
    BenchmarkReport,
    PuzzleResult,
    get_sample_puzzles,
)
from harness.solvers.arc_agi_3.engine import AVOPISAgingEngine


class TestPuzzleResult:
    def test_default(self):
        pr = PuzzleResult(puzzle_id="test")
        assert pr.puzzle_id == "test"
        assert pr.passed is False
        assert pr.accuracy == 0.0


class TestBenchmarkReport:
    def test_pass_rate_empty(self):
        report = BenchmarkReport()
        assert report.pass_rate == 0.0

    def test_pass_rate_with_results(self):
        report = BenchmarkReport(
            results=[
                PuzzleResult(puzzle_id="p1", passed=True),
                PuzzleResult(puzzle_id="p2", passed=False),
                PuzzleResult(puzzle_id="p3", passed=True),
            ],
            total_puzzles=3,
            passed_count=2,
            failed_count=1,
        )
        assert report.pass_rate == 2 / 3

    def test_pass_rate_all_pass(self):
        report = BenchmarkReport(
            results=[PuzzleResult(puzzle_id="p1", passed=True)],
            total_puzzles=1,
            passed_count=1,
            failed_count=0,
        )
        assert report.pass_rate == 1.0

    def test_pass_rate_all_fail(self):
        report = BenchmarkReport(
            results=[PuzzleResult(puzzle_id="p1", passed=False)],
            total_puzzles=1,
            passed_count=0,
            failed_count=1,
        )
        assert report.pass_rate == 0.0


class TestGetSamplePuzzles:
    def test_returns_list(self):
        puzzles = get_sample_puzzles()
        assert isinstance(puzzles, list)
        assert len(puzzles) > 0

    def test_each_has_id(self):
        puzzles = get_sample_puzzles()
        for p in puzzles:
            assert "id" in p

    def test_each_has_train_and_test(self):
        puzzles = get_sample_puzzles()
        for p in puzzles:
            assert "train" in p
            assert "test" in p

    def test_each_train_has_input_output(self):
        puzzles = get_sample_puzzles()
        for p in puzzles:
            for ex in p["train"]:
                assert "input" in ex
                assert "output" in ex

    def test_each_test_has_input_output(self):
        puzzles = get_sample_puzzles()
        for p in puzzles:
            for ex in p["test"]:
                assert "input" in ex
                assert "output" in ex

    def test_contains_identity_puzzle(self):
        puzzles = get_sample_puzzles()
        ids = [p["id"] for p in puzzles]
        assert "identity_001" in ids

    def test_contains_rotation_puzzles(self):
        puzzles = get_sample_puzzles()
        ids = [p["id"] for p in puzzles]
        assert "rotation_90_001" in ids
        assert "rotation_180_001" in ids
        assert "rotation_270_001" in ids


class TestARCAGI3Benchmark:
    def test_run_with_identity_puzzle(self):
        benchmark = ARCAGI3Benchmark()
        puzzles = [
            {
                "id": "identity_test",
                "train": [{"input": [[1, 2], [3, 4]], "output": [[1, 2], [3, 4]]}],
                "test": [{"input": [[5, 6], [7, 8]], "output": [[5, 6], [7, 8]]}],
            }
        ]
        report = benchmark.run(puzzles)
        assert report.total_puzzles == 1
        assert report.passed_count == 1

    def test_run_with_color_shift_puzzle(self):
        benchmark = ARCAGI3Benchmark()
        puzzles = [
            {
                "id": "cs_test",
                "train": [{"input": [[1, 2], [3, 0]], "output": [[2, 3], [4, 0]]}],
                "test": [{"input": [[1, 0], [0, 2]], "output": [[2, 0], [0, 3]]}],
            }
        ]
        report = benchmark.run(puzzles)
        assert report.total_puzzles == 1
        assert report.passed_count == 1

    def test_run_with_rotation_puzzle(self):
        benchmark = ARCAGI3Benchmark()
        puzzles = [
            {
                "id": "rot_test",
                "train": [{"input": [[1, 2], [3, 4]], "output": [[3, 1], [4, 2]]}],
                "test": [{"input": [[1, 0], [0, 2]], "output": [[0, 1], [2, 0]]}],
            }
        ]
        report = benchmark.run(puzzles)
        assert report.total_puzzles == 1
        assert report.passed_count == 1

    def test_run_empty_puzzles(self):
        benchmark = ARCAGI3Benchmark()
        report = benchmark.run([])
        assert report.total_puzzles == 0
        assert report.pass_rate == 0.0

    def test_run_multiple_puzzles(self):
        benchmark = ARCAGI3Benchmark()
        puzzles = [
            {
                "id": "p1",
                "train": [{"input": [[1, 2], [3, 4]], "output": [[1, 2], [3, 4]]}],
                "test": [{"input": [[5, 6], [7, 8]], "output": [[5, 6], [7, 8]]}],
            },
            {
                "id": "p2",
                "train": [{"input": [[1, 2], [3, 4]], "output": [[3, 1], [4, 2]]}],
                "test": [{"input": [[1, 0], [0, 2]], "output": [[0, 1], [2, 0]]}],
            },
        ]
        report = benchmark.run(puzzles)
        assert report.total_puzzles == 2
        assert report.passed_count == 2

    def test_run_with_sample_puzzles(self):
        benchmark = ARCAGI3Benchmark()
        puzzles = get_sample_puzzles()
        report = benchmark.run(puzzles)
        assert report.total_puzzles == len(puzzles)
        # identity and rotation puzzles should pass
        assert report.passed_count >= 1

    def test_run_count(self):
        benchmark = ARCAGI3Benchmark()
        benchmark.run([])
        benchmark.run([])
        assert benchmark.run_count == 2

    def test_run_returns_results_list(self):
        benchmark = ARCAGI3Benchmark()
        puzzles = [
            {
                "id": "p1",
                "train": [{"input": [[1, 2], [3, 4]], "output": [[1, 2], [3, 4]]}],
                "test": [{"input": [[5, 6], [7, 8]], "output": [[5, 6], [7, 8]]}],
            }
        ]
        report = benchmark.run(puzzles)
        assert len(report.results) == 1
        assert report.results[0].puzzle_id == "p1"

    def test_run_timing_recorded(self):
        benchmark = ARCAGI3Benchmark()
        puzzles = [
            {
                "id": "p1",
                "train": [{"input": [[1, 2], [3, 4]], "output": [[1, 2], [3, 4]]}],
                "test": [{"input": [[5, 6], [7, 8]], "output": [[5, 6], [7, 8]]}],
            }
        ]
        report = benchmark.run(puzzles)
        # Timing may be 0.0 on very fast systems; just verify it's recorded (>= 0)
        assert report.total_time >= 0
        assert report.results[0].solve_time >= 0

    def test_run_with_custom_engine(self):
        engine = AVOPISAgingEngine(max_iterations=3)
        benchmark = ARCAGI3Benchmark(engine=engine)
        puzzles = [
            {
                "id": "p1",
                "train": [{"input": [[1, 2], [3, 4]], "output": [[1, 2], [3, 4]]}],
                "test": [{"input": [[5, 6], [7, 8]], "output": [[5, 6], [7, 8]]}],
            }
        ]
        report = benchmark.run(puzzles)
        assert report.passed_count == 1

    def test_run_handles_invalid_puzzle_gracefully(self):
        benchmark = ARCAGI3Benchmark()
        puzzles = [{"invalid": "puzzle"}]
        report = benchmark.run(puzzles)
        assert report.total_puzzles == 1
        assert report.failed_count == 1
