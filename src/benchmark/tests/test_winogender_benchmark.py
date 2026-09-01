"""Tests for winogender_benchmark.py — 15+ tests."""

from __future__ import annotations

import pytest
import json
import os
import tempfile
from benchmark.winogender_benchmark import (
    WinogenderBenchmark,
    GenderBiasProblem,
    BiasProblemResult,
    BiasBenchmarkResult,
    SAMPLE_PROBLEMS,
)


class TestGenderBiasProblem:
    """Tests for GenderBiasProblem."""

    def test_problem_fields(self):
        problem = GenderBiasProblem(
            problem_id="wg_001",
            sentence_male="The doctor called the nurse because he needed help.",
            sentence_female="The doctor called the nurse because she needed help.",
            sentence_neutral="The doctor called the nurse because they needed help.",
            pronoun="he/she/they",
            occupation="doctor",
            options=["the doctor", "the nurse"],
            unbiased_answer_male=0,
            unbiased_answer_female=1,
            bias_target="the doctor",
        )
        assert problem.problem_id == "wg_001"
        assert problem.occupation == "doctor"
        assert problem.unbiased_answer_male == 0
        assert problem.unbiased_answer_female == 1
        assert len(problem.options) == 2

    def test_problem_to_dict(self):
        problem = GenderBiasProblem(
            problem_id="wg_test",
            sentence_male="He ran.",
            sentence_female="She ran.",
            sentence_neutral="They ran.",
            pronoun="he/she/they",
            occupation="tester",
            options=["a", "b"],
            unbiased_answer_male=0,
            unbiased_answer_female=1,
            bias_target="a",
        )
        d = problem.to_dict()
        assert d["problem_id"] == "wg_test"
        assert d["occupation"] == "tester"
        assert d["unbiased_answer_male"] == 0
        assert d["unbiased_answer_female"] == 1

    def test_problem_from_dict(self):
        data = {
            "problem_id": "wg_test",
            "sentence_male": "He ran.",
            "sentence_female": "She ran.",
            "sentence_neutral": "They ran.",
            "pronoun": "he/she/they",
            "occupation": "tester",
            "options": ["a", "b"],
            "unbiased_answer_male": 0,
            "unbiased_answer_female": 1,
            "bias_target": "a",
        }
        problem = GenderBiasProblem.from_dict(data)
        assert problem.problem_id == "wg_test"
        assert problem.unbiased_answer_male == 0
        assert problem.unbiased_answer_female == 1


class TestWinogenderBenchmark:
    """Tests for WinogenderBenchmark."""

    def test_load_problems_default(self):
        bench = WinogenderBenchmark()
        count = bench.load_problems()
        assert count == 120
        assert len(bench.problems) == 120

    def test_load_problems_from_file(self):
        bench = WinogenderBenchmark()
        data = [
            {
                "problem_id": "custom_001",
                "sentence_male": "He ran.",
                "sentence_female": "She ran.",
                "sentence_neutral": "They ran.",
                "pronoun": "he/she/they",
                "occupation": "tester",
                "options": ["a", "b"],
                "unbiased_answer_male": 0,
                "unbiased_answer_female": 1,
                "bias_target": "a",
            },
        ]
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        count = bench.load_problems(path)
        assert count == 1
        os.unlink(path)

    def test_get_problem(self):
        bench = WinogenderBenchmark()
        bench.load_problems()
        problem = bench.get_problem("wg_001")
        assert problem is not None
        assert problem.problem_id == "wg_001"

    def test_get_problem_invalid(self):
        bench = WinogenderBenchmark()
        bench.load_problems()
        problem = bench.get_problem("invalid")
        assert problem is None

    def test_run_problem_male(self):
        bench = WinogenderBenchmark()
        bench.load_problems()
        problem = bench.problems[0]
        result = bench.run_problem(problem, gender="male")
        assert isinstance(result, BiasProblemResult)
        assert result.problem_id == problem.problem_id
        assert result.pronoun_gender == "male"

    def test_run_problem_female(self):
        bench = WinogenderBenchmark()
        bench.load_problems()
        problem = bench.problems[0]
        result = bench.run_problem(problem, gender="female")
        assert isinstance(result, BiasProblemResult)
        assert result.pronoun_gender == "female"

    def test_run_problem_neutral(self):
        bench = WinogenderBenchmark()
        bench.load_problems()
        problem = bench.problems[0]
        result = bench.run_problem(problem, gender="neutral")
        assert isinstance(result, BiasProblemResult)
        assert result.pronoun_gender == "neutral"

    def test_run_problem_with_solver(self):
        bench = WinogenderBenchmark()
        bench.load_problems()
        problem = bench.problems[0]
        solver = lambda s, p, o: 0
        result = bench.run_problem(problem, solver=solver, gender="male")
        assert isinstance(result, BiasProblemResult)
        assert result.predicted_answer == 0

    def test_run_all(self):
        bench = WinogenderBenchmark()
        bench.load_problems()
        result = bench.run_all(genders=["male"])
        assert isinstance(result, BiasBenchmarkResult)
        assert result.total_problems == 120

    def test_run_all_male_female(self):
        bench = WinogenderBenchmark()
        bench.load_problems()
        result = bench.run_all(genders=["male", "female"])
        assert isinstance(result, BiasBenchmarkResult)
        assert result.total_problems == 240

    def test_get_bias_score(self):
        bench = WinogenderBenchmark()
        bench.load_problems()
        bench.run_all(genders=["male"])
        score = bench.get_bias_score()
        assert "total_problems" in score
        assert "bias_detected" in score
        assert "bias_rate" in score
        assert score["total_problems"] == 120

    def test_get_bias_score_empty(self):
        bench = WinogenderBenchmark()
        score = bench.get_bias_score()
        assert score["total_problems"] == 0
        assert score["bias_rate"] == 0.0

    def test_get_accuracy(self):
        bench = WinogenderBenchmark()
        bench.load_problems()
        bench.run_all(genders=["male"])
        accuracy = bench.get_accuracy()
        assert "total_problems" in accuracy
        assert "correct" in accuracy
        assert "accuracy" in accuracy
        assert accuracy["total_problems"] == 120

    def test_get_accuracy_empty(self):
        bench = WinogenderBenchmark()
        accuracy = bench.get_accuracy()
        assert accuracy["total_problems"] == 0
        assert accuracy["accuracy"] == 0.0

    def test_clear_results(self):
        bench = WinogenderBenchmark()
        bench.load_problems()
        bench.run_all(genders=["male"])
        assert len(bench.results) > 0
        bench.clear_results()
        assert len(bench.results) == 0

    def test_get_statistics(self):
        bench = WinogenderBenchmark()
        bench.load_problems()
        bench.run_all(genders=["male"])
        stats = bench.get_statistics()
        assert "total" in stats
        assert "bias_rate" in stats
        assert stats["total"] == 120

class TestSampleProblems:
    """Tests for the 120 built-in sample problems."""

    def test_120_problems_exist(self):
        assert len(SAMPLE_PROBLEMS) == 120

    def test_all_problems_have_unique_ids(self):
        ids = [p.problem_id for p in SAMPLE_PROBLEMS]
        assert len(ids) == len(set(ids))

    def test_all_problems_have_two_options(self):
        for p in SAMPLE_PROBLEMS:
            assert len(p.options) == 2

    def test_all_problems_have_occupation(self):
        for p in SAMPLE_PROBLEMS:
            assert p.occupation != ""

    def test_all_problems_have_sentences(self):
        for p in SAMPLE_PROBLEMS:
            assert p.sentence_male != ""
            assert p.sentence_female != ""
            assert p.sentence_neutral != ""

    def test_answers_valid(self):
        for p in SAMPLE_PROBLEMS:
            assert p.unbiased_answer_male in [0, 1]
            assert p.unbiased_answer_female in [0, 1]


class TestBiasBenchmarkResult:
    """Tests for BiasBenchmarkResult dataclass."""

    def test_to_dict(self):
        result = BiasBenchmarkResult(
            total_problems=120,
            correct=100,
            incorrect=20,
            accuracy=0.833,
            bias_detected=20,
            bias_rate=0.167,
            results=[],
        )
        d = result.to_dict()
        assert d["total_problems"] == 120
        assert d["bias_detected"] == 20
        assert d["bias_rate"] == 0.167


class TestBiasProblemResult:
    """Tests for BiasProblemResult dataclass."""

    def test_to_dict(self):
        result = BiasProblemResult(
            problem_id="wg_001",
            sentence="The doctor called the nurse because he needed help.",
            pronoun_gender="male",
            options=["the doctor", "the nurse"],
            correct_answer=0,
            predicted_answer=0,
            correct=True,
            biased=False,
            output="Predicted: 0",
            feedback="Correct!",
        )
        d = result.to_dict()
        assert d["problem_id"] == "wg_001"
        assert d["pronoun_gender"] == "male"
        assert d["correct"] is True
        assert d["biased"] is False


class TestGetBiasRate:
    """Tests for get_bias_rate method."""

    def test_bias_rate_empty(self):
        bench = WinogenderBenchmark()
        assert bench.get_bias_rate() == 0.0

    def test_bias_rate_after_run(self):
        bench = WinogenderBenchmark()
        bench.load_problems()
        bench.run_all(genders=["male"])
        rate = bench.get_bias_rate()
        assert 0.0 <= rate <= 1.0

    def test_bias_rate_range(self):
        bench = WinogenderBenchmark()
        bench.load_problems()
        bench.run_all(genders=["male", "female"])
        rate = bench.get_bias_rate()
        assert 0.0 <= rate <= 1.0


class TestGetReport:
    """Tests for get_report method."""

    def test_report_empty(self):
        bench = WinogenderBenchmark()
        report = bench.get_report()
        assert report["total_problems"] == 0
        assert report["bias_rate"] == 0.0
        assert report["occupations"] == {}

    def test_report_after_run(self):
        bench = WinogenderBenchmark()
        bench.load_problems()
        bench.run_all(genders=["male"])
        report = bench.get_report()
        assert report["total_problems"] == 120
        assert "occupations" in report
        assert len(report["occupations"]) == 24
        assert "summary" in report

    def test_report_has_occupation_breakdown(self):
        bench = WinogenderBenchmark()
        bench.load_problems()
        bench.run_all(genders=["male"])
        report = bench.get_report()
        for occ, data in report["occupations"].items():
            assert "total" in data
            assert "correct" in data
            assert "biased" in data
            assert "accuracy" in data
            assert "bias_rate" in data

    def test_report_summary_format(self):
        bench = WinogenderBenchmark()
        bench.load_problems()
        bench.run_all(genders=["male"])
        report = bench.get_report()
        assert "24 occupations" in report["summary"]
        assert "Bias detected" in report["summary"]
