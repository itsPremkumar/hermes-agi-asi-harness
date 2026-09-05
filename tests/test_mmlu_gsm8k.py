"""Tests for MMLU and GSM8K benchmarks."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks.gsm8k_benchmark import GSM8KBenchmark, GSM8KQuestion
from benchmarks.mmlu_benchmark import MMLUBenchmark, MMLUCategory, MMLUQuestion


class TestMMLUBenchmark(unittest.TestCase):
    def setUp(self):
        self.benchmark = MMLUBenchmark("/tmp/mmlu_test")

    def test_add_question(self):
        q = MMLUQuestion("q1", "What is 2+2?", ["A. 3", "B. 4", "C. 5", "D. 6"], "B", MMLUCategory.STEM, "math")
        self.benchmark.add_question(q)
        self.assertEqual(len(self.benchmark._questions), 1)

    def test_evaluate_correct(self):
        q = MMLUQuestion("q1", "What is 2+2?", ["A. 3", "B. 4", "C. 5", "D. 6"], "B", MMLUCategory.STEM, "math")
        self.benchmark.add_question(q)
        self.assertTrue(self.benchmark.evaluate("q1", "B"))

    def test_evaluate_incorrect(self):
        q = MMLUQuestion("q1", "What is 2+2?", ["A. 3", "B. 4", "C. 5", "D. 6"], "B", MMLUCategory.STEM, "math")
        self.benchmark.add_question(q)
        self.assertFalse(self.benchmark.evaluate("q1", "A"))

    def test_evaluate_not_found(self):
        self.assertFalse(self.benchmark.evaluate("nonexistent", "A"))

    def test_generate_synthetic_questions(self):
        questions = self.benchmark.generate_synthetic_questions(10)
        self.assertEqual(len(questions), 10)
        self.assertEqual(len(self.benchmark._questions), 10)

    def test_run_benchmark(self):
        self.benchmark.generate_synthetic_questions(10)
        results = self.benchmark.run_benchmark()
        self.assertEqual(results["total"], 10)
        self.assertIn("accuracy", results)

    def test_get_stats(self):
        self.benchmark.generate_synthetic_questions(10)
        stats = self.benchmark.get_stats()
        self.assertEqual(stats["total_questions"], 10)
        self.assertIn("categories", stats)

    def test_load_questions_nonexistent_dir(self):
        benchmark = MMLUBenchmark("/nonexistent/path")
        questions = benchmark.load_questions()
        self.assertEqual(len(questions), 0)


class TestGSM8KBenchmark(unittest.TestCase):
    def setUp(self):
        self.benchmark = GSM8KBenchmark("/tmp/gsm8k_test")

    def test_add_question(self):
        q = GSM8KQuestion("q1", "What is 2+2?", 4.0)
        self.benchmark.add_question(q)
        self.assertEqual(len(self.benchmark._questions), 1)

    def test_evaluate_correct(self):
        q = GSM8KQuestion("q1", "What is 2+2?", 4.0)
        self.benchmark.add_question(q)
        self.assertTrue(self.benchmark.evaluate("q1", 4.0))

    def test_evaluate_with_tolerance(self):
        q = GSM8KQuestion("q1", "What is 2+2?", 4.0)
        self.benchmark.add_question(q)
        self.assertTrue(self.benchmark.evaluate("q1", 4.005))

    def test_evaluate_incorrect(self):
        q = GSM8KQuestion("q1", "What is 2+2?", 4.0)
        self.benchmark.add_question(q)
        self.assertFalse(self.benchmark.evaluate("q1", 5.0))

    def test_evaluate_not_found(self):
        self.assertFalse(self.benchmark.evaluate("nonexistent", 4.0))

    def test_generate_synthetic_questions(self):
        questions = self.benchmark.generate_synthetic_questions(10)
        self.assertEqual(len(questions), 10)
        self.assertEqual(len(self.benchmark._questions), 10)

    def test_run_benchmark(self):
        self.benchmark.generate_synthetic_questions(10)
        results = self.benchmark.run_benchmark()
        self.assertEqual(results["total"], 10)
        self.assertIn("accuracy", results)

    def test_get_stats(self):
        self.benchmark.generate_synthetic_questions(10)
        stats = self.benchmark.get_stats()
        self.assertEqual(stats["total_questions"], 10)

    def test_load_questions_nonexistent_dir(self):
        benchmark = GSM8KBenchmark("/nonexistent/path")
        questions = benchmark.load_questions()
        self.assertEqual(len(questions), 0)


if __name__ == "__main__":
    unittest.main()
