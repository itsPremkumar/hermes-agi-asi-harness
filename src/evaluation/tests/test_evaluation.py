"""Tests for Full Evaluation Suite."""

import os
import sys
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from evaluation.evaluation_suite import (
    EvaluationSuite, EvalResult, EvalReport, EvalCategory,
    build_default_evaluation_suite,
)
from benchmark.human_eval_benchmark import HumanEvalBenchmark
from benchmark.mbpp_benchmark import MBPPBenchmark
from benchmark.hellaswag_benchmark import HellaSwagBenchmark
from benchmark.boolq_benchmark import BoolQBenchmark
from benchmark.swe_bench_pro_benchmark import SWEBenchPro


class TestEvalResult:
    def test_create(self):
        result = EvalResult(
            benchmark="test", category="code",
            total=100, passed=80, failed=20, score=0.8,
        )
        assert result.benchmark == "test"
        assert result.category == "code"
        assert result.total == 100
        assert result.passed == 80
        assert result.score == 0.8


class TestEvalReport:
    def test_create(self):
        report = EvalReport(
            timestamp=time.time(),
            overall_score=0.75,
            total_problems=1000,
            total_passed=750,
            total_failed=250,
            category_scores={"code": 0.8, "reasoning": 0.7},
            results=[],
        )
        assert report.overall_score == 0.75
        assert report.total_problems == 1000


class TestEvaluationSuite:
    def test_create(self):
        suite = EvaluationSuite()
        assert suite.get_benchmark_names() == []

    def test_register_benchmark(self):
        suite = EvaluationSuite()
        bench = HumanEvalBenchmark()
        suite.register_benchmark("HumanEval", bench, "code")
        assert "HumanEval" in suite.get_benchmark_names()

    def test_run_all_benchmarks(self):
        suite = EvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "code")
        results = suite.run_all_benchmarks()
        assert len(results) == 1
        assert results[0].benchmark == "HumanEval"

    def test_run_all_benchmarks_multiple(self):
        suite = EvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "code")
        suite.register_benchmark("MBPP", MBPPBenchmark(), "code")
        results = suite.run_all_benchmarks()
        assert len(results) == 2

    def test_get_overall_score(self):
        suite = EvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "code")
        suite.run_all_benchmarks()
        score = suite.get_overall_score()
        assert 0.0 <= score <= 1.0

    def test_get_overall_score_empty(self):
        suite = EvaluationSuite()
        assert suite.get_overall_score() == 0.0

    def test_get_category_scores(self):
        suite = EvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "code")
        suite.register_benchmark("HellaSwag", HellaSwagBenchmark(), "reasoning")
        suite.run_all_benchmarks()
        scores = suite.get_category_scores()
        assert "code" in scores
        assert "reasoning" in scores

    def test_get_category_scores_empty(self):
        suite = EvaluationSuite()
        assert suite.get_category_scores() == {}

    def test_generate_report(self):
        suite = EvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "code")
        suite.run_all_benchmarks()
        report = suite.generate_report()
        assert isinstance(report, EvalReport)
        assert report.total_problems > 0

    def test_generate_report_empty(self):
        suite = EvaluationSuite()
        report = suite.generate_report()
        assert report.total_problems == 0
        assert report.overall_score == 0.0

    def test_get_results(self):
        suite = EvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "code")
        suite.run_all_benchmarks()
        results = suite.get_results()
        assert len(results) == 1

    def test_get_reports(self):
        suite = EvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "code")
        suite.run_all_benchmarks()
        suite.generate_report()
        reports = suite.get_reports()
        assert len(reports) == 1

    def test_clear(self):
        suite = EvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "code")
        suite.run_all_benchmarks()
        suite.clear()
        assert suite.get_results() == []


class TestDefaultEvaluationSuite:
    def test_build(self):
        suite = build_default_evaluation_suite()
        assert len(suite.get_benchmark_names()) >= 3

    def test_run_all_default(self):
        suite = build_default_evaluation_suite()
        results = suite.run_all_benchmarks()
        assert len(results) >= 3

    def test_overall_score_default(self):
        suite = build_default_evaluation_suite()
        suite.run_all_benchmarks()
        score = suite.get_overall_score()
        assert 0.0 <= score <= 1.0

    def test_category_scores_default(self):
        suite = build_default_evaluation_suite()
        suite.run_all_benchmarks()
        scores = suite.get_category_scores()
        assert len(scores) >= 1

    def test_generate_report_default(self):
        suite = build_default_evaluation_suite()
        suite.run_all_benchmarks()
        report = suite.generate_report()
        assert report.total_problems > 0
        assert report.overall_score >= 0.0


class TestEvaluationIntegration:
    def test_full_pipeline(self):
        suite = build_default_evaluation_suite()
        results = suite.run_all_benchmarks()
        assert len(results) >= 3

        overall = suite.get_overall_score()
        assert 0.0 <= overall <= 1.0

        categories = suite.get_category_scores()
        assert len(categories) >= 1

        report = suite.generate_report()
        assert report.total_problems > 0
        assert len(report.results) >= 3

    def test_multiple_benchmark_types(self):
        suite = EvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "code")
        suite.register_benchmark("MBPP", MBPPBenchmark(), "code")
        suite.register_benchmark("HellaSwag", HellaSwagBenchmark(), "reasoning")
        suite.register_benchmark("BoolQ", BoolQBenchmark(), "reasoning")
        suite.register_benchmark("SWE-bench Pro", SWEBenchPro(), "code")

        results = suite.run_all_benchmarks()
        assert len(results) == 5

        categories = suite.get_category_scores()
        assert "code" in categories
        assert "reasoning" in categories

    def test_report_metadata(self):
        suite = build_default_evaluation_suite()
        suite.run_all_benchmarks()
        report = suite.generate_report()
        assert "num_benchmarks" in report.metadata
        assert "benchmarks" in report.metadata

    def test_report_timestamp(self):
        suite = build_default_evaluation_suite()
        suite.run_all_benchmarks()
        report = suite.generate_report()
        assert report.timestamp > 0

    def test_results_have_duration(self):
        suite = build_default_evaluation_suite()
        results = suite.run_all_benchmarks()
        for result in results:
            assert result.duration_ms >= 0

    def test_category_score_average(self):
        suite = EvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "code")
        suite.register_benchmark("MBPP", MBPPBenchmark(), "code")
        suite.run_all_benchmarks()
        scores = suite.get_category_scores()
        assert "code" in scores
        # Code category should have average of HumanEval and MBPP scores

    def test_overall_score_calculation(self):
        suite = EvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "code")
        suite.run_all_benchmarks()
        score = suite.get_overall_score()
        # Should be between 0 and 1
        assert 0.0 <= score <= 1.0

    def test_clear_results(self):
        suite = build_default_evaluation_suite()
        suite.run_all_benchmarks()
        assert len(suite.get_results()) > 0
        suite.clear()
        assert len(suite.get_results()) == 0

    def test_multiple_runs(self):
        suite = build_default_evaluation_suite()
        suite.run_all_benchmarks()
        suite.run_all_benchmarks()
        # Results should be replaced, not duplicated
        assert len(suite.get_results()) >= 3

    def test_report_results_match(self):
        suite = build_default_evaluation_suite()
        suite.run_all_benchmarks()
        report = suite.generate_report()
        assert len(report.results) == len(suite.get_results())

    def test_total_passed_equals_sum(self):
        suite = build_default_evaluation_suite()
        suite.run_all_benchmarks()
        report = suite.generate_report()
        total_passed = sum(r.passed for r in report.results)
        assert report.total_passed == total_passed

    def test_total_failed_equals_sum(self):
        suite = build_default_evaluation_suite()
        suite.run_all_benchmarks()
        report = suite.generate_report()
        total_failed = sum(r.failed for r in report.results)
        assert report.total_failed == total_failed

    def test_total_problems_equals_sum(self):
        suite = build_default_evaluation_suite()
        suite.run_all_benchmarks()
        report = suite.generate_report()
        total = sum(r.total for r in report.results)
        assert report.total_problems == total


class TestEvaluationExtended:
    def test_multiple_categories(self):
        suite = EvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "code")
        suite.register_benchmark("MBPP", MBPPBenchmark(), "code")
        suite.register_benchmark("HellaSwag", HellaSwagBenchmark(), "reasoning")
        suite.register_benchmark("BoolQ", BoolQBenchmark(), "reasoning")
        suite.run_all_benchmarks()
        scores = suite.get_category_scores()
        assert len(scores) == 2

    def test_benchmark_result_fields(self):
        suite = build_default_evaluation_suite()
        results = suite.run_all_benchmarks()
        for result in results:
            assert hasattr(result, 'benchmark')
            assert hasattr(result, 'category')
            assert hasattr(result, 'total')
            assert hasattr(result, 'passed')
            assert hasattr(result, 'failed')
            assert hasattr(result, 'score')
            assert hasattr(result, 'duration_ms')

    def test_report_fields(self):
        suite = build_default_evaluation_suite()
        suite.run_all_benchmarks()
        report = suite.generate_report()
        assert hasattr(report, 'timestamp')
        assert hasattr(report, 'overall_score')
        assert hasattr(report, 'total_problems')
        assert hasattr(report, 'total_passed')
        assert hasattr(report, 'total_failed')
        assert hasattr(report, 'category_scores')
        assert hasattr(report, 'results')

    def test_register_multiple_categories(self):
        suite = EvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "code")
        suite.register_benchmark("HellaSwag", HellaSwagBenchmark(), "reasoning")
        suite.register_benchmark("SWE-bench Pro", SWEBenchPro(), "code")
        assert len(suite.get_benchmark_names()) == 3

    def test_run_all_returns_eval_results(self):
        suite = build_default_evaluation_suite()
        results = suite.run_all_benchmarks()
        for result in results:
            assert isinstance(result, EvalResult)

    def test_generate_report_returns_eval_report(self):
        suite = build_default_evaluation_suite()
        suite.run_all_benchmarks()
        report = suite.generate_report()
        assert isinstance(report, EvalReport)

    def test_overall_score_after_multiple_runs(self):
        suite = build_default_evaluation_suite()
        suite.run_all_benchmarks()
        score1 = suite.get_overall_score()
        suite.run_all_benchmarks()
        score2 = suite.get_overall_score()
        assert score1 == score2

    def test_category_scores_after_multiple_runs(self):
        suite = build_default_evaluation_suite()
        suite.run_all_benchmarks()
        scores1 = suite.get_category_scores()
        suite.run_all_benchmarks()
        scores2 = suite.get_category_scores()
        assert scores1 == scores2

    def test_get_reports_multiple(self):
        suite = build_default_evaluation_suite()
        suite.run_all_benchmarks()
        suite.generate_report()
        suite.generate_report()
        assert len(suite.get_reports()) == 2

    def test_clear_does_not_affect_reports(self):
        suite = build_default_evaluation_suite()
        suite.run_all_benchmarks()
        suite.generate_report()
        suite.clear()
        assert len(suite.get_reports()) == 1

    def test_total_equals_passed_plus_failed(self):
        suite = build_default_evaluation_suite()
        suite.run_all_benchmarks()
        report = suite.generate_report()
        assert report.total_problems == report.total_passed + report.total_failed

    def test_each_result_total_equals_passed_plus_failed(self):
        suite = build_default_evaluation_suite()
        results = suite.run_all_benchmarks()
        for result in results:
            assert result.total == result.passed + result.failed

    def test_score_between_0_and_1(self):
        suite = build_default_evaluation_suite()
        results = suite.run_all_benchmarks()
        for result in results:
            assert 0.0 <= result.score <= 1.0

    def test_benchmark_names_unique(self):
        suite = EvaluationSuite()
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "code")
        suite.register_benchmark("HumanEval2", HumanEvalBenchmark(), "code")
        names = suite.get_benchmark_names()
        assert len(names) == len(set(names))

    def test_eval_category_enum(self):
        assert EvalCategory.CODE.value == "code"
        assert EvalCategory.REASONING.value == "reasoning"
        assert EvalCategory.SAFETY.value == "safety"
        assert EvalCategory.GENERAL.value == "general"

    def test_result_defaults(self):
        result = EvalResult(
            benchmark="test", category="code",
            total=0, passed=0, failed=0, score=0.0,
        )
        assert result.duration_ms == 0.0
        assert result.details == {}

    def test_report_defaults(self):
        report = EvalReport(
            timestamp=0.0, overall_score=0.0,
            total_problems=0, total_passed=0, total_failed=0,
            category_scores={}, results=[],
        )
        assert report.metadata == {}
