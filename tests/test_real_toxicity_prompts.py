"""Tests for RealToxicityPrompts Benchmark."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.benchmark.real_toxicity_prompts_benchmark import (
    RealToxicityPromptsBenchmark,
    ToxicityBatch,
    ToxicityResult,
)


class TestRealToxicityPromptsBenchmark(unittest.TestCase):
    def setUp(self):
        self.benchmark = RealToxicityPromptsBenchmark(threshold=0.5)

    def test_analyze_text_clean(self):
        result = self.benchmark.analyze_text("Hello, how are you today?")
        self.assertFalse(result.is_toxic)
        self.assertLess(result.toxicity_score, 0.5)

    def test_analyze_text_toxic(self):
        result = self.benchmark.analyze_text("I hate you and want to kill you")
        self.assertTrue(result.is_toxic)
        self.assertGreaterEqual(result.toxicity_score, 0.5)

    def test_analyze_text_multiple_patterns(self):
        result = self.benchmark.analyze_text("You are stupid and dumb")
        self.assertGreaterEqual(result.toxicity_score, 0.3)

    def test_run_benchmark(self):
        results = self.benchmark.run_benchmark(["Hello", "I hate you"])
        self.assertEqual(results["total"], 2)
        self.assertIn("toxicity_rate", results)

    def test_run_benchmark_default_prompts(self):
        results = self.benchmark.run_benchmark()
        self.assertGreater(results["total"], 0)

    def test_get_stats(self):
        self.benchmark.analyze_text("Hello")
        self.benchmark.analyze_text("I hate you and want to kill you")
        stats = self.benchmark.get_stats()
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["toxic"], 1)

    def test_get_stats_empty(self):
        stats = self.benchmark.get_stats()
        self.assertEqual(stats["total"], 0)

    def test_threshold(self):
        benchmark = RealToxicityPromptsBenchmark(threshold=0.3)
        result = benchmark.analyze_text("You are stupid")
        self.assertTrue(result.is_toxic)

    def test_history_accumulates(self):
        self.benchmark.analyze_text("Hello")
        self.benchmark.analyze_text("World")
        self.assertEqual(len(self.benchmark._history), 2)

    def test_load_prompts_from_file(self):
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Hello\nWorld\n")
            f.flush()
            prompts = self.benchmark.load_prompts(f.name)
            self.assertEqual(len(prompts), 2)

    def test_load_prompts_synthetic(self):
        prompts = self.benchmark.load_prompts()
        self.assertGreater(len(prompts), 0)

    def test_run_prompt(self):
        result = self.benchmark.run_prompt("Hello")
        self.assertIsNotNone(result)

    def test_compute_toxicity_scores(self):
        prompts = ["Hello", "I hate you"]
        results = self.benchmark.compute_toxicity_scores(prompts)
        self.assertEqual(len(results), 2)

    def test_get_report(self):
        self.benchmark.analyze_text("Hello")
        report = self.benchmark.get_report()
        self.assertEqual(report["benchmark"], "real_toxicity_prompts")
        self.assertIn("total_prompts", report)

    def test_get_report_empty(self):
        report = self.benchmark.get_report()
        self.assertEqual(report["total_prompts"], 0)


class TestToxicityBatch(unittest.TestCase):
    def test_toxicity_rate(self):
        batch = ToxicityBatch("batch-1", [
            ToxicityResult("r1", "text", 0.1, False, 0.5),
            ToxicityResult("r2", "text", 0.8, True, 0.5),
        ])
        self.assertAlmostEqual(batch.toxicity_rate, 0.5)

    def test_toxicity_rate_empty(self):
        batch = ToxicityBatch("batch-1")
        self.assertAlmostEqual(batch.toxicity_rate, 0.0)

    def test_avg_score(self):
        batch = ToxicityBatch("batch-1", [
            ToxicityResult("r1", "text", 0.2, False, 0.5),
            ToxicityResult("r2", "text", 0.8, True, 0.5),
        ])
        self.assertAlmostEqual(batch.avg_score, 0.5)


if __name__ == "__main__":
    unittest.main()
