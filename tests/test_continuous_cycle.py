"""Tests for Continuous Improvement Cycle — ≥40 tests."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.daily_improvement.continuous_cycle import (
    BenchmarkScore,
    ContinuousCycle,
    CycleStage,
    Improvement,
    ProgressEntry,
    Weakness,
)


class TestBenchmarkScore(unittest.TestCase):
    def test_score_creation(self):
        score = BenchmarkScore(benchmark="mmlu", score=0.8, target=1.0)
        self.assertEqual(score.benchmark, "mmlu")
        self.assertEqual(score.score, 0.8)
        self.assertEqual(score.target, 1.0)

    def test_gap(self):
        score = BenchmarkScore(benchmark="mmlu", score=0.7, target=1.0)
        self.assertAlmostEqual(score.gap, 0.3)

    def test_gap_zero(self):
        score = BenchmarkScore(benchmark="mmlu", score=1.0, target=1.0)
        self.assertAlmostEqual(score.gap, 0.0)

    def test_percent(self):
        score = BenchmarkScore(benchmark="mmlu", score=0.8, target=1.0)
        self.assertAlmostEqual(score.percent, 80.0)

    def test_percent_zero_target(self):
        score = BenchmarkScore(benchmark="mmlu", score=0.8, target=0.0)
        self.assertAlmostEqual(score.percent, 0.0)


class TestContinuousCycle(unittest.TestCase):
    def setUp(self):
        self.cycle = ContinuousCycle()

    def test_add_benchmark(self):
        self.cycle.add_benchmark("mmlu", 1.0)
        self.assertIn("mmlu", self.cycle._benchmarks)

    def test_run_evaluation(self):
        self.cycle.add_benchmark("mmlu", 1.0)
        scores = self.cycle.run_evaluation()
        self.assertEqual(len(scores), 1)
        self.assertEqual(scores[0].benchmark, "mmlu")

    def test_run_evaluation_multiple(self):
        self.cycle.add_benchmark("mmlu", 1.0)
        self.cycle.add_benchmark("gsm8k", 0.9)
        scores = self.cycle.run_evaluation()
        self.assertEqual(len(scores), 2)

    def test_analyze_weaknesses(self):
        scores = [BenchmarkScore("mmlu", 0.5, 1.0)]
        weaknesses = self.cycle.analyze_weaknesses(scores)
        self.assertGreater(len(weaknesses), 0)

    def test_analyze_weaknesses_no_gap(self):
        scores = [BenchmarkScore("mmlu", 1.0, 1.0)]
        weaknesses = self.cycle.analyze_weaknesses(scores)
        self.assertEqual(len(weaknesses), 0)

    def test_generate_improvements(self):
        weaknesses = [Weakness("mmlu", "perf", "gap", 0.5)]
        improvements = self.cycle.generate_improvements(weaknesses)
        self.assertEqual(len(improvements), 1)

    def test_generate_improvements_empty(self):
        improvements = self.cycle.generate_improvements([])
        self.assertEqual(len(improvements), 0)

    def test_implement_changes(self):
        improvements = [Improvement("imp-1", "mmlu", "fix", 0.1)]
        applied = self.cycle.implement_changes(improvements)
        self.assertEqual(len(applied), 1)
        self.assertTrue(applied[0].applied)

    def test_verify_improvement(self):
        improvements = [Improvement("imp-1", "mmlu", "fix", 0.1, applied=True)]
        self.assertTrue(self.cycle.verify_improvement(improvements))

    def test_verify_improvement_not_applied(self):
        improvements = [Improvement("imp-1", "mmlu", "fix", 0.1, applied=False)]
        self.assertFalse(self.cycle.verify_improvement(improvements))

    def test_record_progress(self):
        scores = [BenchmarkScore("mmlu", 0.8, 1.0)]
        entry = self.cycle.record_progress(scores)
        self.assertIsNotNone(entry)
        self.assertEqual(len(self.cycle._progress), 1)

    def test_record_progress_empty(self):
        entry = self.cycle.record_progress([])
        self.assertEqual(entry.benchmark, "")

    def test_main_loop(self):
        self.cycle.add_benchmark("mmlu", 1.0)
        results = self.cycle.main_loop(max_cycles=3)
        self.assertEqual(len(results), 3)

    def test_main_loop_stages(self):
        self.cycle.add_benchmark("mmlu", 1.0)
        results = self.cycle.main_loop(max_cycles=2)
        for result in results:
            self.assertEqual(result.stage, CycleStage.RECORDING)

    def test_get_stats(self):
        self.cycle.add_benchmark("mmlu", 1.0)
        self.cycle.run_evaluation()
        stats = self.cycle.get_stats()
        self.assertEqual(stats["benchmarks"], 1)
        self.assertEqual(stats["scores_recorded"], 1)


class TestWeakness(unittest.TestCase):
    def test_weakness_creation(self):
        w = Weakness("mmlu", "perf", "gap", 0.5)
        self.assertEqual(w.benchmark, "mmlu")
        self.assertEqual(w.category, "perf")
        self.assertEqual(w.severity, 0.5)


class TestImprovement(unittest.TestCase):
    def test_improvement_creation(self):
        imp = Improvement("imp-1", "mmlu", "fix", 0.1)
        self.assertEqual(imp.improvement_id, "imp-1")
        self.assertFalse(imp.applied)

    def test_improvement_applied(self):
        imp = Improvement("imp-1", "mmlu", "fix", 0.1, applied=True)
        self.assertTrue(imp.applied)


class TestIntegration(unittest.TestCase):
    def test_full_cycle(self):
        cycle = ContinuousCycle()
        cycle.add_benchmark("mmlu", 1.0)
        cycle.add_benchmark("gsm8k", 0.9)
        results = cycle.main_loop(max_cycles=2)
        self.assertEqual(len(results), 2)
        stats = cycle.get_stats()
        self.assertEqual(stats["benchmarks"], 2)

    def test_multiple_cycles_accumulate(self):
        cycle = ContinuousCycle()
        cycle.add_benchmark("mmlu", 1.0)
        cycle.main_loop(max_cycles=3)
        self.assertEqual(len(cycle._scores), 3)

    def test_improvements_accumulate(self):
        cycle = ContinuousCycle()
        cycle.add_benchmark("mmlu", 1.0)
        cycle.main_loop(max_cycles=3)
        self.assertGreater(len(cycle._improvements), 0)


class TestContinuousCycleEdgeCases(unittest.TestCase):
    def setUp(self):
        self.cycle = ContinuousCycle()

    def test_main_loop_zero_cycles(self):
        self.cycle.add_benchmark("mmlu", 1.0)
        results = self.cycle.main_loop(max_cycles=0)
        self.assertEqual(len(results), 0)

    def test_run_evaluation_no_benchmarks(self):
        scores = self.cycle.run_evaluation()
        self.assertEqual(len(scores), 0)

    def test_analyze_weaknesses_multiple(self):
        scores = [
            BenchmarkScore("mmlu", 0.5, 1.0),
            BenchmarkScore("gsm8k", 0.3, 0.9),
        ]
        weaknesses = self.cycle.analyze_weaknesses(scores)
        self.assertEqual(len(weaknesses), 2)

    def test_analyze_weaknesses_perfect_score(self):
        scores = [BenchmarkScore("mmlu", 1.0, 1.0)]
        weaknesses = self.cycle.analyze_weaknesses(scores)
        self.assertEqual(len(weaknesses), 0)

    def test_generate_improvements_multiple(self):
        weaknesses = [
            Weakness("mmlu", "perf", "gap", 0.5),
            Weakness("gsm8k", "acc", "gap", 0.3),
        ]
        improvements = self.cycle.generate_improvements(weaknesses)
        self.assertEqual(len(improvements), 2)

    def test_implement_changes_multiple(self):
        improvements = [
            Improvement("imp-1", "mmlu", "fix", 0.1),
            Improvement("imp-2", "gsm8k", "fix", 0.2),
        ]
        applied = self.cycle.implement_changes(improvements)
        self.assertEqual(len(applied), 2)
        for a in applied:
            self.assertTrue(a.applied)

    def test_implement_changes_empty(self):
        applied = self.cycle.implement_changes([])
        self.assertEqual(len(applied), 0)

    def test_verify_improvement_mixed(self):
        improvements = [
            Improvement("imp-1", "mmlu", "fix", 0.1, applied=True),
            Improvement("imp-2", "gsm8k", "fix", 0.1, applied=False),
        ]
        self.assertFalse(self.cycle.verify_improvement(improvements))

    def test_verify_improvement_empty(self):
        self.assertTrue(self.cycle.verify_improvement([]))

    def test_get_stats_initial(self):
        stats = self.cycle.get_stats()
        self.assertEqual(stats["benchmarks"], 0)
        self.assertEqual(stats["cycles_completed"], 0)

    def test_gap_negative(self):
        """Score above target should give negative gap."""
        score = BenchmarkScore("mmlu", 1.2, 1.0)
        self.assertAlmostEqual(score.gap, -0.2)

    def test_percent_over_100(self):
        score = BenchmarkScore("mmlu", 1.5, 1.0)
        self.assertAlmostEqual(score.percent, 150.0)

    def test_progress_entry(self):
        entry = ProgressEntry(
            timestamp=1000.0,
            benchmark="all",
            score=0.8,
            target=1.0,
            improvement=0.1,
        )
        self.assertEqual(entry.benchmark, "all")
        self.assertAlmostEqual(entry.improvement, 0.1)

    def test_main_loop_single_cycle(self):
        self.cycle.add_benchmark("mmlu", 1.0)
        results = self.cycle.main_loop(max_cycles=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].cycle_id, "cycle-0")


if __name__ == "__main__":
    unittest.main()
