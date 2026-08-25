"""Tests for src/reflexion_eval/bench.py."""
from __future__ import annotations

import json

import pytest

from reflexion_eval.bench import (
    BenchmarkResult,
    _comb,
    load_suite,
    pass_at_k,
    run_benchmark,
)
from reflexion_eval.evaluator import Rubric
from reflexion_eval.loop import Task


# ---------------------------------------------------------------------------
# pass_at_k math
# ---------------------------------------------------------------------------
class TestPassAtK:
    def test_all_pass_is_one(self):
        assert pass_at_k(n=3, c=3, k=1) == 1.0

    def test_none_pass_is_zero(self):
        assert pass_at_k(n=3, c=0, k=1) == 0.0

    def test_k_larger_than_n_returns_zero(self):
        assert pass_at_k(n=2, c=1, k=3) == 0.0

    def test_k_zero_returns_zero(self):
        assert pass_at_k(n=3, c=1, k=0) == 0.0

    def test_k_equals_n_with_one_fail(self):
        # n=3, c=2, k=3 -> 1 - C(1,3)/C(3,3) = 1 - 0/1 = 1.0
        result = pass_at_k(n=3, c=2, k=3)
        assert result == 1.0

    def test_known_value(self):
        # n=4, c=2, k=2 -> 1 - C(2,2)/C(4,2) = 1 - 1/6 = 5/6
        result = pass_at_k(n=4, c=2, k=2)
        expected = 1.0 - 1.0 / 6.0
        assert result == pytest.approx(expected)

    def test_k_equals_one(self):
        # pass@1 = c/n
        result = pass_at_k(n=10, c=3, k=1)
        assert result == pytest.approx(0.3)


class TestComb:
    def test_basic(self):
        assert _comb(5, 2) == 10.0

    def test_k_zero(self):
        assert _comb(5, 0) == 1.0

    def test_k_n(self):
        assert _comb(5, 5) == 1.0

    def test_k_gt_n(self):
        assert _comb(5, 7) == 0.0

    def test_negative_k(self):
        assert _comb(5, -1) == 0.0


# ---------------------------------------------------------------------------
# load_suite
# ---------------------------------------------------------------------------
class TestLoadSuite:
    def test_loads_yaml_files(self, tmp_path):
        task_yaml = """
id: t_load_test
description: "test task"
rubric:
  name: "TestRubric"
  pass_threshold: 0.5
  criteria:
    - ["c", "d"]
max_iterations: 2
"""
        (tmp_path / "task_1.yaml").write_text(task_yaml)
        tasks = load_suite(str(tmp_path))
        assert len(tasks) == 1
        assert tasks[0].id == "t_load_test"
        assert tasks[0].description == "test task"
        assert tasks[0].rubric.name == "TestRubric"
        assert tasks[0].rubric.pass_threshold == 0.5
        assert tasks[0].rubric.criteria == [("c", "d")]
        assert tasks[0].max_iterations == 2

    def test_loads_yml_extension(self, tmp_path):
        (tmp_path / "task_1.yml").write_text(
            "id: t_yml\ndescription: y\nsrubric:\n  name: R\n  criteria:\n    - [\"a\", \"b\"]\n  pass_threshold: 0.5\n"
        )
        # Fix the typo in the YAML
        (tmp_path / "task_1.yml").write_text(
            'id: t_yml\ndescription: y\nrubric:\n  name: R\n  criteria:\n    - ["a", "b"]\n  pass_threshold: 0.5\n'
        )
        tasks = load_suite(str(tmp_path))
        assert len(tasks) == 1
        assert tasks[0].id == "t_yml"

    def test_loads_multiple_files(self, tmp_path):
        for i in range(3):
            (tmp_path / f"task_{i}.yaml").write_text(
                f'id: t{i}\ndescription: d{i}\nrubric:\n  name: R\n  criteria:\n    - [\"c\", \"d\"]\n  pass_threshold: 0.5\n'
            )
        tasks = load_suite(str(tmp_path))
        assert len(tasks) == 3

    def test_empty_dir(self, tmp_path):
        tasks = load_suite(str(tmp_path))
        assert tasks == []

    def test_loads_list_of_tasks(self, tmp_path):
        yaml_content = """
- id: t_a
  description: "task a"
  rubric:
    name: "R"
    criteria:
      - ["c", "d"]
    pass_threshold: 0.5
- id: t_b
  description: "task b"
  rubric:
    name: "R"
    criteria:
      - ["c", "d"]
    pass_threshold: 0.5
"""
        (tmp_path / "multi.yaml").write_text(yaml_content)
        tasks = load_suite(str(tmp_path))
        assert len(tasks) == 2
        assert tasks[0].id == "t_a"
        assert tasks[1].id == "t_b"


# ---------------------------------------------------------------------------
# run_benchmark
# ---------------------------------------------------------------------------
class TestRunBenchmark:
    @pytest.fixture
    def two_tasks(self):
        r = Rubric(name="T", criteria=[("c", "d")], pass_threshold=0.5)
        return [
            Task(id="tb1", description="q1", rubric=r, max_iterations=3),
            Task(id="tb2", description="q2", rubric=r, max_iterations=3),
        ]

    def test_all_pass(self, two_tasks):
        def agent(prompt: str) -> str:
            if "ANSWER:" in prompt:
                return "ANSWER: correct"
            if "FEEDBACK" in prompt and "REFLECTION" in prompt:
                return "good"
            return "reflection"

        def eval_llm(prompt: str) -> str:
            return "FINAL SCORE: 0.9\nFEEDBACK: Good.\nREFLECTION: ok"

        result = run_benchmark(two_tasks, agent, eval_llm, k_values=[1])
        assert result.per_task["tb1"]["passed"] is True
        assert result.per_task["tb2"]["passed"] is True
        assert result.pass_k[1] == 1.0

    def test_all_fail(self, two_tasks):
        def agent(prompt: str) -> str:
            if "ANSWER:" in prompt:
                return "ANSWER: wrong"
            if "FEEDBACK" in prompt and "REFLECTION" in prompt:
                return "bad"
            return "reflection"

        def eval_llm(prompt: str) -> str:
            return "FINAL SCORE: 0.1\nFEEDBACK: Bad.\nREFLECTION: ok"

        result = run_benchmark(two_tasks, agent, eval_llm, k_values=[1])
        assert result.per_task["tb1"]["passed"] is False
        assert result.per_task["tb2"]["passed"] is False
        assert result.pass_k[1] == 0.0

    def test_mixed_results(self, two_tasks):
        def agent(prompt: str) -> str:
            if "ANSWER:" in prompt:
                if "q1" in prompt:
                    return "ANSWER: correct"
                return "ANSWER: wrong"
            if "FEEDBACK" in prompt and "REFLECTION" in prompt:
                return "reflection"
            return "reflection"

        def eval_llm(prompt: str) -> str:
            if "correct" in prompt:
                return "FINAL SCORE: 0.9\nFEEDBACK: Good.\nREFLECTION: ok"
            return "FINAL SCORE: 0.1\nFEEDBACK: Bad.\nREFLECTION: ok"

        result = run_benchmark(two_tasks, agent, eval_llm, k_values=[1])
        assert result.per_task["tb1"]["passed"] is True
        assert result.per_task["tb2"]["passed"] is False
        assert result.pass_k[1] == 0.5

    def test_max_iterations_override(self, two_tasks):
        def agent(prompt: str) -> str:
            if "ANSWER:" in prompt:
                return "ANSWER: wrong"
            if "FEEDBACK" in prompt and "REFLECTION" in prompt:
                return "reflection"
            return "reflection"

        def eval_llm(prompt: str) -> str:
            return "FINAL SCORE: 0.1\nFEEDBACK: Bad.\nREFLECTION: ok"

        result = run_benchmark(two_tasks, agent, eval_llm, k_values=[1], max_iterations=1)
        assert result.per_task["tb1"]["iterations"] == 1
        assert result.per_task["tb2"]["iterations"] == 1

    def test_result_serializable(self, two_tasks):
        def agent(prompt: str) -> str:
            if "ANSWER:" in prompt:
                return "ANSWER: correct"
            if "FEEDBACK" in prompt and "REFLECTION" in prompt:
                return "reflection"
            return "reflection"

        def eval_llm(prompt: str) -> str:
            return "FINAL SCORE: 0.9\nFEEDBACK: Good.\nREFLECTION: ok"

        result = run_benchmark(two_tasks, agent, eval_llm, k_values=[1, 3])
        d = result.to_dict()
        # should be JSON-serializable
        json.dumps(d)
        assert "pass_at_k" in d
        assert "per_task" in d

    def test_pass_k_computed_for_multiple_ks(self, two_tasks):
        def agent(prompt: str) -> str:
            if "ANSWER:" in prompt:
                return "ANSWER: correct"
            if "FEEDBACK" in prompt and "REFLECTION" in prompt:
                return "reflection"
            return "reflection"

        def eval_llm(prompt: str) -> str:
            return "FINAL SCORE: 0.9\nFEEDBACK: Good.\nREFLECTION: ok"

        result = run_benchmark(two_tasks, agent, eval_llm, k_values=[1, 3])
        assert 1 in result.pass_k
        assert 3 in result.pass_k

    def test_empty_task_list(self):
        result = run_benchmark([], lambda p: "x", lambda p: "x", k_values=[1])
        assert len(result.task_ids) == 0
        assert result.pass_k[1] == 0.0

    def test_result_has_task_ids(self, two_tasks):
        def agent(prompt: str) -> str:
            if "ANSWER:" in prompt:
                return "ANSWER: correct"
            if "FEEDBACK" in prompt and "REFLECTION" in prompt:
                return "reflection"
            return "reflection"

        def eval_llm(prompt: str) -> str:
            return "FINAL SCORE: 0.9\nFEEDBACK: Good.\nREFLECTION: ok"

        result = run_benchmark(two_tasks, agent, eval_llm, k_values=[1])
        assert result.task_ids == ["tb1", "tb2"]
