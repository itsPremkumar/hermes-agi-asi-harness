"""Tests for MBPP Benchmark."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from benchmark.mbpp_benchmark import MBPPBenchmark, ProblemStatus


class TestMBPPBenchmark:
    def test_create(self):
        bench = MBPPBenchmark()
        assert bench.count() == 0

    def test_load_default(self):
        bench = MBPPBenchmark()
        count = bench.load_problems()
        assert count == 974

    def test_load_custom(self):
        bench = MBPPBenchmark()
        custom = [{"id": "C1", "prompt": "p", "entry_point": "f"}]
        assert bench.load_problems(custom) == 1

    def test_run_problem(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        result = bench.run_problem("MBPP_1", "def square(n): return n * n")
        assert result.status == ProblemStatus.PASSED

    def test_run_problem_not_found(self):
        bench = MBPPBenchmark()
        result = bench.run_problem("nonexistent")
        assert result.status == ProblemStatus.ERROR

    def test_run_problem_syntax_error(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        result = bench.run_problem("MBPP_1", "def square(:")
        assert result.status == ProblemStatus.FAILED

    def test_set_solution(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        bench.set_solution("MBPP_1", "def square(n): return n * n")
        result = bench.run_problem("MBPP_1")
        assert result.status == ProblemStatus.PASSED

    def test_run_all(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        results = bench.run_all()
        assert len(results) == 974

    def test_get_pass_rate(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        bench.run_all()
        rate = bench.get_pass_rate()
        assert rate["total"] == 974

    def test_get_pass_rate_empty(self):
        bench = MBPPBenchmark()
        rate = bench.get_pass_rate()
        assert rate["total"] == 0

    def test_get_result(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        bench.run_problem("MBPP_1", "def square(n): return n * n")
        result = bench.get_result("MBPP_1")
        assert result is not None

    def test_clear_results(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        bench.run_all()
        bench.clear_results()
        assert bench.get_pass_rate()["total"] == 0

    def test_count(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        assert bench.count() == 974

    def test_problem_metadata(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        problem = bench.get_problem("MBPP_1")
        assert "difficulty" in problem.metadata

    def test_problem_has_prompt(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        problem = bench.get_problem("MBPP_1")
        assert len(problem.prompt) > 0

    def test_list_problems(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        assert len(bench.list_problems()) == 974

    def test_result_duration(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        result = bench.run_problem("MBPP_1", "def square(n): return n * n")
        assert result.duration_ms >= 0

    def test_full_pipeline(self):
        bench = MBPPBenchmark()
        assert bench.load_problems() == 974
        results = bench.run_all()
        assert len(results) == 974
        rate = bench.get_pass_rate()
        assert rate["total"] == 974

    def test_multiple_problems(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        for i in range(1, 11):
            bench.run_problem(f"MBPP_{i}")
        rate = bench.get_pass_rate()
        assert rate["total"] == 10

    def test_different_difficulties(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        easy = bench.get_problem("MBPP_1")
        medium = bench.get_problem("MBPP_300")
        hard = bench.get_problem("MBPP_700")
        assert easy.metadata["difficulty"] == "easy"
        assert medium.metadata["difficulty"] == "medium"
        assert hard.metadata["difficulty"] == "hard"

    def test_categories(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        categories = set()
        for pid in bench.list_problems()[:20]:
            problem = bench.get_problem(pid)
            categories.add(problem.metadata["category"])
        assert len(categories) > 0

    def test_entry_points(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        entry_points = set()
        for pid in bench.list_problems()[:50]:
            problem = bench.get_problem(pid)
            entry_points.add(problem.entry_point)
        assert len(entry_points) > 10

    def test_pass_rate_after_clear(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        bench.run_all()
        assert bench.get_pass_rate()["total"] == 974
        bench.clear_results()
        assert bench.get_pass_rate()["total"] == 0

    def test_problem_status(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        problem = bench.get_problem("MBPP_1")
        assert problem.status == ProblemStatus.PENDING

    def test_custom_solution(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        result = bench.run_problem("MBPP_1", "def square(n): return n * n")
        assert result.solution == "def square(n): return n * n"

    def test_result_has_solution(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        result = bench.run_problem("MBPP_1", "def square(n): return n * n")
        assert len(result.solution) > 0

    def test_run_problem_with_override(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        bench.set_solution("MBPP_1", "def square(n): return 0")
        result = bench.run_problem("MBPP_1", "def square(n): return n * n")
        assert result.solution == "def square(n): return n * n"

    def test_multiple_runs(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        for _ in range(3):
            result = bench.run_problem("MBPP_1", "def square(n): return n * n")
            assert result.status == ProblemStatus.PASSED

    def test_problem_with_test_code(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        problem = bench.get_problem("MBPP_1")
        assert len(problem.test_code) > 0

    def test_result_output(self):
        bench = MBPPBenchmark()
        bench.load_problems()
        result = bench.run_problem("MBPP_1", "def square(n): return n * n")
        assert result.output == "Executed successfully"

    def test_error_message_on_not_found(self):
        bench = MBPPBenchmark()
        result = bench.run_problem("nonexistent")
        assert "not found" in result.error
