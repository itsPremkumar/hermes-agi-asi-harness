"""Tests for the multi-benchmark harness.

Covers SWE-bench, GAIA, Terminal-Bench, GPQA, HumanEval, MBPP adapters.
"""
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.benchmarks import (
    BenchmarkType, BenchmarkTask, TaskResult, BenchmarkResult,
    SWEBenchAdapter, GAIAAdapter, TerminalBenchAdapter,
    GPQAAdapter, HumanEvalAdapter, MBPPAdapter,
    MultiBenchmarkEngine, create_default_engine,
)


@pytest.fixture
def temp_data_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def write_task(data_dir: Path, benchmark: str, tasks: list):
    """Helper to write task JSON files."""
    bdir = data_dir / benchmark
    bdir.mkdir(parents=True, exist_ok=True)
    for i, task in enumerate(tasks):
        task_file = bdir / f"task_{i}.json"
        import json
        task_file.write_text(json.dumps(task))


# ---------------------------------------------------------------------------
# SWE-bench
# ---------------------------------------------------------------------------

class TestSWEBenchAdapter:
    def test_load_tasks(self, temp_data_dir):
        write_task(temp_data_dir, "swebench_verified", [
            {"instance_id": "test-1", "repo": "test/repo", "problem_statement": "fix bug", "patch": "diff --git a.py b.py"}
        ])
        adapter = SWEBenchAdapter("verified", temp_data_dir)
        tasks = adapter.load_tasks()
        assert len(tasks) == 1
        assert tasks[0].task_id == "test-1"
        assert tasks[0].benchmark == BenchmarkType.SWE_BENCH_VERIFIED

    def test_load_no_tasks(self, temp_data_dir):
        adapter = SWEBenchAdapter("verified", temp_data_dir)
        tasks = adapter.load_tasks()
        assert len(tasks) == 0

    def test_evaluate_valid_patch(self, temp_data_dir):
        adapter = SWEBenchAdapter("verified", temp_data_dir)
        task = BenchmarkTask(task_id="t1", benchmark=BenchmarkType.SWE_BENCH_VERIFIED, prompt="p", ground_truth="diff --git a.py b.py")
        score = adapter.evaluate(task, "diff --git a.py b.py\n--- a.py\n+++ b.py")
        assert score == 0.5

    def test_evaluate_empty(self, temp_data_dir):
        adapter = SWEBenchAdapter("verified", temp_data_dir)
        task = BenchmarkTask(task_id="t1", benchmark=BenchmarkType.SWE_BENCH_VERIFIED, prompt="p")
        assert adapter.evaluate(task, "") == 0.0

    def test_tools(self, temp_data_dir):
        adapter = SWEBenchAdapter("verified", temp_data_dir)
        tools = adapter.get_tools()
        assert len(tools) > 0
        names = [t["name"] for t in tools]
        assert "explore_repo" in names
        assert "run_tests" in names


# ---------------------------------------------------------------------------
# GAIA
# ---------------------------------------------------------------------------

class TestGAIAAdapter:
    def test_load_tasks(self, temp_data_dir):
        write_task(temp_data_dir, "gaia", [
            {"task_id": "g1", "Question": "What is 2+2?", "Final answer": "4", "Level": 1}
        ])
        adapter = GAIAAdapter(temp_data_dir)
        tasks = adapter.load_tasks()
        assert len(tasks) == 1
        assert tasks[0].task_id == "g1"
        assert tasks[0].benchmark == BenchmarkType.GAIA

    def test_evaluate_correct(self, temp_data_dir):
        adapter = GAIAAdapter(temp_data_dir)
        task = BenchmarkTask(task_id="g1", benchmark=BenchmarkType.GAIA, prompt="p", ground_truth="4")
        assert adapter.evaluate(task, "4") == 1.0

    def test_evaluate_incorrect(self, temp_data_dir):
        adapter = GAIAAdapter(temp_data_dir)
        task = BenchmarkTask(task_id="g1", benchmark=BenchmarkType.GAIA, prompt="p", ground_truth="4")
        assert adapter.evaluate(task, "5") == 0.0

    def test_evaluate_case_insensitive(self, temp_data_dir):
        adapter = GAIAAdapter(temp_data_dir)
        task = BenchmarkTask(task_id="g1", benchmark=BenchmarkType.GAIA, prompt="p", ground_truth="Paris")
        assert adapter.evaluate(task, "paris") == 1.0

    def test_tools(self, temp_data_dir):
        adapter = GAIAAdapter(temp_data_dir)
        tools = adapter.get_tools()
        names = [t["name"] for t in tools]
        assert "web_search" in names
        assert "calculator" in names


# ---------------------------------------------------------------------------
# Terminal-Bench
# ---------------------------------------------------------------------------

class TestTerminalBenchAdapter:
    def test_load_tasks(self, temp_data_dir):
        write_task(temp_data_dir, "terminal_bench", [
            {"task_id": "tb1", "instruction": "compile code", "expected_output": "success"}
        ])
        adapter = TerminalBenchAdapter(temp_data_dir)
        tasks = adapter.load_tasks()
        assert len(tasks) == 1
        assert tasks[0].benchmark == BenchmarkType.TERMINAL_BENCH

    def test_evaluate(self, temp_data_dir):
        adapter = TerminalBenchAdapter(temp_data_dir)
        task = BenchmarkTask(task_id="tb1", benchmark=BenchmarkType.TERMINAL_BENCH, prompt="p", ground_truth="success")
        assert adapter.evaluate(task, "success") == 1.0
        assert adapter.evaluate(task, "failure") == 0.0


# ---------------------------------------------------------------------------
# GPQA
# ---------------------------------------------------------------------------

class TestGPQAAdapter:
    def test_load_tasks(self, temp_data_dir):
        write_task(temp_data_dir, "gpqa", [
            {"task_id": "gp1", "question": "What is E=mc^2?", "correct_answer": "A", "choices": ["A", "B", "C", "D"]}
        ])
        adapter = GPQAAdapter(temp_data_dir)
        tasks = adapter.load_tasks()
        assert len(tasks) == 1
        assert tasks[0].benchmark == BenchmarkType.GPQA

    def test_evaluate(self, temp_data_dir):
        adapter = GPQAAdapter(temp_data_dir)
        task = BenchmarkTask(task_id="gp1", benchmark=BenchmarkType.GPQA, prompt="p", ground_truth="A")
        assert adapter.evaluate(task, "A") == 1.0
        assert adapter.evaluate(task, "B") == 0.0

    def test_evaluate_lowercase(self, temp_data_dir):
        adapter = GPQAAdapter(temp_data_dir)
        task = BenchmarkTask(task_id="gp1", benchmark=BenchmarkType.GPQA, prompt="p", ground_truth="A")
        assert adapter.evaluate(task, "a") == 1.0


# ---------------------------------------------------------------------------
# HumanEval
# ---------------------------------------------------------------------------

class TestHumanEvalAdapter:
    def test_load_tasks(self, temp_data_dir):
        write_task(temp_data_dir, "human_eval", [
            {"task_id": "he1", "prompt": "def add(a,b): ...", "canonical_solution": "def add(a,b): return a+b", "entry_point": "add"}
        ])
        adapter = HumanEvalAdapter(temp_data_dir)
        tasks = adapter.load_tasks()
        assert len(tasks) == 1
        assert tasks[0].benchmark == BenchmarkType.HUMAN_EVAL

    def test_evaluate(self, temp_data_dir):
        adapter = HumanEvalAdapter(temp_data_dir)
        task = BenchmarkTask(task_id="he1", benchmark=BenchmarkType.HUMAN_EVAL, prompt="p", ground_truth="def add(a,b): return a+b", metadata={"entry_point": "add"})
        assert adapter.evaluate(task, "def add(a,b): return a+b") == 0.5
        assert adapter.evaluate(task, "no function here") == 0.0


# ---------------------------------------------------------------------------
# MBPP
# ---------------------------------------------------------------------------

class TestMBPPAdapter:
    def test_load_tasks(self, temp_data_dir):
        write_task(temp_data_dir, "mbpp", [
            {"task_id": "mb1", "text": "Write a function that adds two numbers", "code": "def add(a,b): return a+b", "test_list": ["assert add(1,2)==3"]}
        ])
        adapter = MBPPAdapter(temp_data_dir)
        tasks = adapter.load_tasks()
        assert len(tasks) == 1
        assert tasks[0].benchmark == BenchmarkType.MBPP

    def test_evaluate(self, temp_data_dir):
        adapter = MBPPAdapter(temp_data_dir)
        task = BenchmarkTask(task_id="mb1", benchmark=BenchmarkType.MBPP, prompt="p", ground_truth="def add(a,b): return a+b")
        assert adapter.evaluate(task, "def add(a,b): return a+b") == 0.5
        assert adapter.evaluate(task, "no function") == 0.0


# ---------------------------------------------------------------------------
# MultiBenchmarkEngine
# ---------------------------------------------------------------------------

class TestMultiBenchmarkEngine:
    def test_create_engine(self):
        engine = MultiBenchmarkEngine(verbose=False)
        assert len(engine._adapters) == 0

    def test_register_adapter(self, temp_data_dir):
        engine = MultiBenchmarkEngine()
        adapter = SWEBenchAdapter("verified", temp_data_dir)
        engine.register_adapter(adapter)
        assert BenchmarkType.SWE_BENCH_VERIFIED in engine._adapters

    def test_run_benchmark_no_adapter(self):
        engine = MultiBenchmarkEngine()
        with pytest.raises(ValueError):
            engine.run_benchmark(BenchmarkType.SWE_BENCH)

    def test_run_benchmark_with_tasks(self, temp_data_dir):
        write_task(temp_data_dir, "swebench_verified", [
            {"instance_id": "test-1", "repo": "test/repo", "problem_statement": "fix bug", "patch": "diff --git a.py b.py"}
        ])
        engine = MultiBenchmarkEngine(verbose=False)
        engine.register_adapter(SWEBenchAdapter("verified", temp_data_dir))
        result = engine.run_benchmark(BenchmarkType.SWE_BENCH_VERIFIED)
        assert isinstance(result, BenchmarkResult)
        assert result.total_tasks == 1
        assert result.benchmark == BenchmarkType.SWE_BENCH_VERIFIED

    def test_run_all_benchmarks(self, temp_data_dir):
        write_task(temp_data_dir, "gaia", [
            {"task_id": "g1", "Question": "What is 2+2?", "Final answer": "4", "Level": 1}
        ])
        engine = MultiBenchmarkEngine(verbose=False)
        engine.register_adapter(GAIAAdapter(temp_data_dir))
        results = engine.run_all_benchmarks()
        assert BenchmarkType.GAIA in results

    def test_create_default_engine(self, temp_data_dir):
        engine = create_default_engine(temp_data_dir)
        assert len(engine._adapters) == 7  # all standard benchmarks


# ---------------------------------------------------------------------------
# BenchmarkResult
# ---------------------------------------------------------------------------

class TestBenchmarkResult:
    def test_compute_score(self):
        result = BenchmarkResult(
            benchmark=BenchmarkType.GAIA,
            total_tasks=4,
            completed_tasks=2,
            task_results=[
                TaskResult(task_id="g1", benchmark=BenchmarkType.GAIA, completed=True, score=1.0),
                TaskResult(task_id="g2", benchmark=BenchmarkType.GAIA, completed=True, score=1.0),
                TaskResult(task_id="g3", benchmark=BenchmarkType.GAIA, completed=False, score=0.0),
                TaskResult(task_id="g4", benchmark=BenchmarkType.GAIA, completed=False, score=0.0),
            ],
        )
        score = result.compute_score()
        assert score == pytest.approx(0.5)
        assert result.avg_score == pytest.approx(0.5)

    def test_compute_score_empty(self):
        result = BenchmarkResult(benchmark=BenchmarkType.GAIA, total_tasks=0, completed_tasks=0)
        assert result.compute_score() == 0.0

    def test_compute_score_all_pass(self):
        result = BenchmarkResult(
            benchmark=BenchmarkType.GAIA,
            total_tasks=3,
            completed_tasks=3,
            task_results=[
                TaskResult(task_id=f"g{i}", benchmark=BenchmarkType.GAIA, completed=True, score=1.0)
                for i in range(3)
            ],
        )
        assert result.compute_score() == pytest.approx(1.0)
