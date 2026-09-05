"""Tests for the benchmark evaluator — real code execution."""
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks.core_suites.evaluator import (
    CodeExecutor, HumanEvalEvaluator, MBPPEvaluator,
    SWEBenchEvaluator, TerminalBenchEvaluator, BenchmarkEvaluator,
    EvaluationResult,
)


# ---------------------------------------------------------------------------
# CodeExecutor tests
# ---------------------------------------------------------------------------

class TestCodeExecutor:
    def test_execute_simple_function(self):
        executor = CodeExecutor()
        code = """
def add(a, b):
    return a + b
"""
        result = executor.execute(code, "add", (2, 3))
        assert result.success
        assert result.return_value == 5

    def test_execute_syntax_error(self):
        executor = CodeExecutor()
        code = "def add(a, b) return a + b"  # missing colon
        result = executor.execute(code, "add")
        assert not result.success
        assert "SyntaxError" in result.error

    def test_execute_runtime_error(self):
        executor = CodeExecutor()
        code = """
def divide(a, b):
    return a / b
"""
        result = executor.execute(code, "divide", (1, 0))
        assert not result.success

    def test_execute_with_tests(self):
        executor = CodeExecutor()
        code = """
def multiply(a, b):
    return a * b
"""
        test_cases = [
            ((2, 3), 6),
            ((0, 5), 0),
            ((-1, 5), -5),
        ]
        result = executor.execute_with_tests(code, test_cases, "multiply")
        assert result.score == 1.0
        assert result.passed == 3
        assert result.failed == 0

    def test_execute_with_tests_partial(self):
        executor = CodeExecutor()
        code = """
def add(a, b):
    return a + b + 1  # wrong
"""
        test_cases = [
            ((1, 2), 3),
            ((2, 3), 5),
        ]
        result = executor.execute_with_tests(code, test_cases, "add")
        assert result.score == 0.0
        assert result.failed == 2

    def test_execute_timeout(self):
        executor = CodeExecutor(timeout=1.0)
        code = """
def infinite():
    while True:
        pass
"""
        result = executor.execute(code, "infinite")
        assert result.timed_out

    def test_execute_no_function(self):
        executor = CodeExecutor()
        code = "x = 42\nprint(x)"
        result = executor.execute(code)
        assert result.success


# ---------------------------------------------------------------------------
# HumanEvalEvaluator tests
# ---------------------------------------------------------------------------

class TestHumanEvalEvaluator:
    def test_evaluate_correct_solution(self):
        evaluator = HumanEvalEvaluator()
        code = """
def add(a, b):
    return a + b
"""
        test_code = """
def check():
    assert add(1, 2) == 3
    assert add(0, 0) == 0
    assert add(-1, 1) == 0
    print("PASS")
"""
        result = evaluator.evaluate(code, test_code, "add")
        assert result.score == 1.0
        assert result.passed == 1

    def test_evaluate_wrong_solution(self):
        evaluator = HumanEvalEvaluator()
        code = """
def add(a, b):
    return a + b + 1
"""
        test_code = """
def check():
    assert add(1, 2) == 3
    print("PASS")
"""
        result = evaluator.evaluate(code, test_code, "add")
        assert result.score == 0.0

    def test_evaluate_syntax_error(self):
        evaluator = HumanEvalEvaluator()
        code = "def add(a, b) return a + b"
        test_code = "def check(): pass"
        result = evaluator.evaluate(code, test_code, "add")
        assert result.score == 0.0
        assert "Syntax" in result.compilation_error or "expected" in result.compilation_error


# ---------------------------------------------------------------------------
# MBPPEvaluator tests
# ---------------------------------------------------------------------------

class TestMBPPEvaluator:
    def test_evaluate_correct(self):
        evaluator = MBPPEvaluator()
        code = """
def add(a, b):
    return a + b
"""
        test_list = [
            "assert add(1, 2) == 3",
            "assert add(0, 0) == 0",
            "assert add(-1, 1) == 0",
        ]
        result = evaluator.evaluate(code, test_list, "add")
        assert result.score == 1.0
        assert result.passed == 3

    def test_evaluate_partial(self):
        evaluator = MBPPEvaluator()
        code = """
def add(a, b):
    return a + b
"""
        test_list = [
            "assert add(1, 2) == 3",
            "assert add(2, 3) == 6",  # wrong
        ]
        result = evaluator.evaluate(code, test_list, "add")
        assert result.score == 0.5
        assert result.passed == 1
        assert result.failed == 1

    def test_evaluate_empty_tests(self):
        evaluator = MBPPEvaluator()
        code = "def add(a, b): return a + b"
        result = evaluator.evaluate(code, [], "add")
        assert result.score == 0.0
        assert result.total == 0


# ---------------------------------------------------------------------------
# SWEBenchEvaluator tests
# ---------------------------------------------------------------------------

class TestSWEBenchEvaluator:
    def test_validate_valid_patch(self):
        evaluator = SWEBenchEvaluator()
        patch = """diff --git a/test.py b/test.py
@@ -1,3 +1,3 @@
 def add(a, b):
-    return a + b
+    return a + b + 1
"""
        valid, msg = evaluator.validate_patch(patch)
        assert valid

    def test_validate_invalid_patch(self):
        evaluator = SWEBenchEvaluator()
        patch = "not a valid patch"
        valid, msg = evaluator.validate_patch(patch)
        assert not valid

    def test_validate_empty_patch(self):
        evaluator = SWEBenchEvaluator()
        valid, msg = evaluator.validate_patch("")
        assert not valid

    def test_evaluate_no_repo(self):
        evaluator = SWEBenchEvaluator()
        patch = """diff --git a/test.py b/test.py
@@ -1,3 +1,3 @@
 def add(a, b):
-    return a + b
+    return a + b + 1
"""
        result = evaluator.evaluate(patch)
        assert result.score == 0.5  # format valid, tests unknown


# ---------------------------------------------------------------------------
# TerminalBenchEvaluator tests
# ---------------------------------------------------------------------------

class TestTerminalBenchEvaluator:
    def test_evaluate_correct_output(self):
        evaluator = TerminalBenchEvaluator()
        commands = ["echo hello"]
        result = evaluator.evaluate(commands, "hello")
        assert result.score == 1.0

    def test_evaluate_wrong_output(self):
        evaluator = TerminalBenchEvaluator()
        commands = ["echo hello"]
        result = evaluator.evaluate(commands, "world")
        assert result.score == 0.0

    def test_evaluate_multiple_commands(self):
        evaluator = TerminalBenchEvaluator()
        commands = ["echo hello", "echo world"]
        result = evaluator.evaluate(commands, "world")
        assert result.score == 1.0  # "world" is in output


# ---------------------------------------------------------------------------
# BenchmarkEvaluator tests
# ---------------------------------------------------------------------------

class TestBenchmarkEvaluator:
    def test_create_evaluator(self):
        evaluator = BenchmarkEvaluator()
        assert evaluator._human_eval is not None
        assert evaluator._mbpp is not None
        assert evaluator._swe_bench is not None
        assert evaluator._terminal is not None

    def test_evaluate_human_eval(self):
        evaluator = BenchmarkEvaluator()
        code = "def add(a, b): return a + b"
        test_code = "def check():\n    assert add(1,2)==3\n    print('PASS')"
        result = evaluator.evaluate_human_eval(code, test_code, "add")
        assert isinstance(result, EvaluationResult)
        assert result.score == 1.0

    def test_evaluate_mbpp(self):
        evaluator = BenchmarkEvaluator()
        code = "def add(a, b): return a + b"
        test_list = ["assert add(1,2)==3"]
        result = evaluator.evaluate_mbpp(code, test_list, "add")
        assert isinstance(result, EvaluationResult)
        assert result.score == 1.0

    def test_evaluate_swe_bench(self):
        evaluator = BenchmarkEvaluator()
        patch = "diff --git a.py b.py\n@@ -1,2 +1,2 @@\n-def f(): pass\n+def f(): return 1\n"
        result = evaluator.evaluate_swe_bench(patch)
        assert isinstance(result, EvaluationResult)

    def test_evaluate_terminal_bench(self):
        evaluator = BenchmarkEvaluator()
        result = evaluator.evaluate_terminal_bench(["echo test"], "test")
        assert isinstance(result, EvaluationResult)
        assert result.score == 1.0
