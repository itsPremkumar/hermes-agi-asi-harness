"""Tests for Full Evaluation Suite."""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from benchmark.full_evaluation_suite import (
    EvalCategory,
    EvalReport,
    EvalResult,
    FullEvaluationSuite,
    build_default_full_evaluation_suite,
)
from benchmark.hellaswag_benchmark import HellaSwagBenchmark
from benchmark.human_eval_benchmark import HumanEvalBenchmark
from benchmark.mbpp_benchmark import MBPPBenchmark


class TestEvalResult:
    def test_create(self):
        result = EvalResult(benchmark="test", category="coding", total=100, passed=80, failed=20, score=0.8, duration_ms=10.0)
        assert result.benchmark == "test"
        assert result.score == 0.8

    def test_default_duration(self):
        result = EvalResult(benchmark="test", category="coding", total=0, passed=0, failed=0, score=0.0)
        assert result.duration_ms == 0.0


class TestEvalReport:
    def test_create(self):
        report = EvalReport(timestamp=time.time(), overall_score=75.0, total_problems=1000, total_passed=750, total_failed=250, category_scores={"coding": 80.0}, benchmark_scores={"HE": 75.0}, improvements=[], results=[])
        assert report.overall_score == 75.0


class TestFullEvaluationSuite:
    def test_create(self):
        suite = FullEvaluationSuite()
        assert suite.get_benchmark_names() == []

    def test_register_benchmark(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        assert "HumanEval" in suite.get_benchmark_names()

    def test_run_all_benchmarks(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        results = suite.run_all_benchmarks()
        assert len(results) == 1

    def test_get_overall_score(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.run_all_benchmarks()
        score = suite.get_overall_score()
        assert 0 <= score <= 100

    def test_get_overall_score_empty(self):
        suite = FullEvaluationSuite()
        assert suite.get_overall_score() == 0.0

    def test_get_category_scores(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.register_benchmark("HellaSwag", HellaSwagBenchmark(), "reasoning")
        suite.run_all_benchmarks()
        scores = suite.get_category_scores()
        assert "coding" in scores
        assert "reasoning" in scores

    def test_get_benchmark_scores(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.run_all_benchmarks()
        scores = suite.get_benchmark_scores()
        assert "HumanEval" in scores

    def test_get_improvements(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.run_all_benchmarks()
        improvements = suite.get_improvements()
        assert isinstance(improvements, list)

    def test_generate_report(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.run_all_benchmarks()
        report = suite.generate_report()
        assert isinstance(report, EvalReport)
        assert report.total_problems > 0

    def test_generate_report_empty(self):
        suite = FullEvaluationSuite()
        report = suite.generate_report()
        assert report.total_problems == 0

    def test_get_results(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.run_all_benchmarks()
        assert len(suite.get_results()) == 1

    def test_get_reports(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.run_all_benchmarks()
        suite.generate_report()
        assert len(suite.get_reports()) == 1

    def test_clear(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.run_all_benchmarks()
        suite.clear()
        assert suite.get_results() == []

    def test_multiple_benchmarks(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.register_benchmark("MBPP", MBPPBenchmark(), "coding")
        suite.register_benchmark("HellaSwag", HellaSwagBenchmark(), "reasoning")
        results = suite.run_all_benchmarks()
        assert len(results) == 3

    def test_run_all_returns_eval_results(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        results = suite.run_all_benchmarks()
        for result in results:
            assert isinstance(result, EvalResult)

    def test_category_score_scaling(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.run_all_benchmarks()
        scores = suite.get_category_scores()
        for score in scores.values():
            assert 0 <= score <= 100

    def test_benchmark_score_scaling(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.run_all_benchmarks()
        scores = suite.get_benchmark_scores()
        for score in scores.values():
            assert 0 <= score <= 100

    def test_overall_score_scaling(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.run_all_benchmarks()
        score = suite.get_overall_score()
        assert 0 <= score <= 100

    def test_report_metadata(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.run_all_benchmarks()
        report = suite.generate_report()
        assert "num_benchmarks" in report.metadata
        assert "benchmarks" in report.metadata

    def test_report_improvements(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.run_all_benchmarks()
        report = suite.generate_report()
        assert isinstance(report.improvements, list)

    def test_report_benchmark_scores(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.run_all_benchmarks()
        report = suite.generate_report()
        assert isinstance(report.benchmark_scores, dict)

    def test_report_category_scores(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.run_all_benchmarks()
        report = suite.generate_report()
        assert isinstance(report.category_scores, dict)

    def test_total_equals_passed_plus_failed(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.run_all_benchmarks()
        report = suite.generate_report()
        assert report.total_problems == report.total_passed + report.total_failed

    def test_each_result_total_equals_sum(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        results = suite.run_all_benchmarks()
        for result in results:
            assert result.total == result.passed + result.failed

    def test_score_between_0_and_1(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        results = suite.run_all_benchmarks()
        for result in results:
            assert 0.0 <= result.score <= 1.0

    def test_report_timestamp(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.run_all_benchmarks()
        report = suite.generate_report()
        assert report.timestamp > 0

    def test_multiple_runs_replace(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.run_all_benchmarks()
        suite.run_all_benchmarks()
        assert len(suite.get_results()) == 1

    def test_clear_does_not_affect_reports(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.run_all_benchmarks()
        suite.generate_report()
        suite.clear()
        assert len(suite.get_reports()) == 1

    def test_get_reports_multiple(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.run_all_benchmarks()
        suite.generate_report()
        suite.generate_report()
        assert len(suite.get_reports()) == 2

    def test_results_have_duration(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        results = suite.run_all_benchmarks()
        for result in results:
            assert result.duration_ms >= 0

    def test_report_results_match(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.run_all_benchmarks()
        report = suite.generate_report()
        assert len(report.results) == len(suite.get_results())

    def test_eval_category_enum(self):
        assert EvalCategory.REASONING.value == "reasoning"
        assert EvalCategory.CODING.value == "coding"
        assert EvalCategory.MATH.value == "math"
        assert EvalCategory.LANGUAGE.value == "language"
        assert EvalCategory.BIAS.value == "bias"
        assert EvalCategory.SAFETY.value == "safety"

    def test_stats_after_clear(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.run_all_benchmarks()
        suite.clear()
        assert suite.get_overall_score() == 0.0

    def test_improvements_high_priority(self):
        suite = FullEvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "coding")
        suite.run_all_benchmarks()
        improvements = suite.get_improvements()
        for imp in improvements:
            assert "benchmark" in imp
            assert "priority" in imp
            assert "recommendation" in imp


class TestDefaultFullEvaluationSuite:
    def test_build(self):
        suite = build_default_full_evaluation_suite()
        assert len(suite.get_benchmark_names()) >= 5

    def test_run_all_default(self):
        suite = build_default_full_evaluation_suite()
        results = suite.run_all_benchmarks()
        assert len(results) >= 5

    def test_overall_score_default(self):
        suite = build_default_full_evaluation_suite()
        suite.run_all_benchmarks()
        score = suite.get_overall_score()
        assert 0 <= score <= 100

    def test_category_scores_default(self):
        suite = build_default_full_evaluation_suite()
        suite.run_all_benchmarks()
        scores = suite.get_category_scores()
        assert len(scores) >= 1

    def test_benchmark_scores_default(self):
        suite = build_default_full_evaluation_suite()
        suite.run_all_benchmarks()
        scores = suite.get_benchmark_scores()
        assert len(scores) >= 5

    def test_generate_report_default(self):
        suite = build_default_full_evaluation_suite()
        suite.run_all_benchmarks()
        report = suite.generate_report()
        assert report.total_problems > 0

    def test_improvements_default(self):
        suite = build_default_full_evaluation_suite()
        suite.run_all_benchmarks()
        improvements = suite.get_improvements()
        assert isinstance(improvements, list)

    def test_full_pipeline(self):
        suite = build_default_full_evaluation_suite()
        results = suite.run_all_benchmarks()
        assert len(results) >= 5
        overall = suite.get_overall_score()
        assert 0 <= overall <= 100
        categories = suite.get_category_scores()
        assert len(categories) >= 1
        benchmarks = suite.get_benchmark_scores()
        assert len(benchmarks) >= 5
        improvements = suite.get_improvements()
        assert isinstance(improvements, list)
        report = suite.generate_report()
        assert report.total_problems > 0

    def test_all_benchmarks_registered(self):
        suite = build_default_full_evaluation_suite()
        names = suite.get_benchmark_names()
        expected = ["HumanEval", "MBPP", "HellaSwag", "BoolQ", "PIQA", "OpenBookQA", "SIQA", "SWE-bench Pro"]
        for name in expected:
            assert name in names

    def test_category_coverage(self):
        suite = build_default_full_evaluation_suite()
        suite.run_all_benchmarks()
        categories = suite.get_category_scores()
        assert "coding" in categories
        assert "reasoning" in categories

    def test_report_has_all_fields(self):
        suite = build_default_full_evaluation_suite()
        suite.run_all_benchmarks()
        report = suite.generate_report()
        assert hasattr(report, 'timestamp')
        assert hasattr(report, 'overall_score')
        assert hasattr(report, 'total_problems')
        assert hasattr(report, 'total_passed')
        assert hasattr(report, 'total_failed')
        assert hasattr(report, 'category_scores')
        assert hasattr(report, 'benchmark_scores')
        assert hasattr(report, 'improvements')
        assert hasattr(report, 'results')

    def test_improvements_have_required_fields(self):
        suite = build_default_full_evaluation_suite()
        suite.run_all_benchmarks()
        improvements = suite.get_improvements()
        for imp in improvements:
            assert "benchmark" in imp
            assert "category" in imp
            assert "current_score" in imp
            assert "priority" in imp
            assert "recommendation" in imp

    def test_benchmark_scores_all_present(self):
        suite = build_default_full_evaluation_suite()
        suite.run_all_benchmarks()
        scores = suite.get_benchmark_scores()
        for name in suite.get_benchmark_names():
            assert name in scores
