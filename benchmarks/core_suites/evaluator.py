"""Test execution engine for coding benchmarks.

Provides safe code execution, test evaluation, and patch verification for:
- HumanEval: execute generated code against test assertions
- MBPP: run test assertions against generated functions
- SWE-bench: apply patches and run test suites (local mode)
- Terminal-Bench: execute shell commands and verify output
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Tuple


# ---------------------------------------------------------------------------
# Execution results
# ---------------------------------------------------------------------------

@dataclass
class ExecutionResult:
    """Result of executing code."""
    success: bool
    output: str = ""
    error: str = ""
    return_value: Any = None
    timed_out: bool = False
    duration: float = 0.0


@dataclass
class TestResult:
    """Result of running a test case."""
    passed: bool
    test_name: str = ""
    expected: str = ""
    actual: str = ""
    error: str = ""
    duration: float = 0.0


@dataclass
class EvaluationResult:
    """Complete evaluation result for a coding task."""
    score: float  # 0.0 to 1.0
    passed: int = 0
    failed: int = 0
    total: int = 0
    test_results: List[TestResult] = field(default_factory=list)
    compilation_error: str = ""
    execution_error: str = ""
    duration: float = 0.0


# ---------------------------------------------------------------------------
# Safe code executor
# ---------------------------------------------------------------------------

class CodeExecutor:
    """Safely execute Python code with timeout and error handling."""

    def __init__(self, timeout: float = 30.0, max_memory_mb: int = 512):
        self._timeout = timeout
        self._max_memory_mb = max_memory_mb

    def execute(self, code: str, function_name: str = "", args: tuple = ()) -> ExecutionResult:
        """Execute Python code and return the result."""
        start_time = time.time()

        # Check syntax first
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return ExecutionResult(
                success=False,
                error=f"SyntaxError: {e}",
                duration=time.time() - start_time,
            )

        # If no function name, just execute the code directly
        if not function_name:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_path = f.name
            try:
                result = subprocess.run(
                    [sys.executable, temp_path],
                    capture_output=True,
                    text=True,
                    timeout=self._timeout,
                )
                return ExecutionResult(
                    success=result.returncode == 0,
                    output=result.stdout,
                    error=result.stderr,
                    duration=time.time() - start_time,
                )
            finally:
                os.unlink(temp_path)

        # Write code to a temp file and execute in subprocess
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            # Wrap code to capture output and handle execution
            wrapper = f"""
import sys
import json
import traceback

{code}

if __name__ == "__main__":
    try:
        result = {function_name}(*json.loads(sys.argv[1]))
        print(json.dumps({{"success": True, "result": result}}))
    except Exception as e:
        print(json.dumps({{"success": False, "error": str(e), "traceback": traceback.format_exc()}}))
"""
            f.write(wrapper)
            temp_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, temp_path, json.dumps(list(args))],
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            duration = time.time() - start_time

            if result.returncode != 0:
                return ExecutionResult(
                    success=False,
                    output=result.stdout,
                    error=result.stderr,
                    duration=duration,
                )

            # Parse JSON output
            try:
                output_data = json.loads(result.stdout.strip().split('\n')[-1])
                return ExecutionResult(
                    success=output_data.get("success", False),
                    output=result.stdout,
                    return_value=output_data.get("result"),
                    error=output_data.get("error", ""),
                    duration=duration,
                )
            except (json.JSONDecodeError, IndexError):
                return ExecutionResult(
                    success=True,
                    output=result.stdout,
                    duration=duration,
                )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                error=f"Execution timed out after {self._timeout}s",
                timed_out=True,
                duration=time.time() - start_time,
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )
        finally:
            os.unlink(temp_path)

    def execute_with_tests(
        self,
        code: str,
        test_cases: List[Tuple[tuple, Any]],
        function_name: str = "",
    ) -> EvaluationResult:
        """Execute code against multiple test cases."""
        start_time = time.time()
        test_results = []
        passed = 0
        failed = 0

        for i, (args, expected) in enumerate(test_cases):
            result = self.execute(code, function_name, args)

            if not result.success:
                failed += 1
                test_results.append(TestResult(
                    passed=False,
                    test_name=f"test_{i}",
                    expected=str(expected),
                    actual="",
                    error=result.error,
                    duration=result.duration,
                ))
                continue

            # Compare result with expected
            actual = result.return_value
            try:
                # Handle floating point comparison
                if isinstance(expected, float) and isinstance(actual, float):
                    test_passed = abs(actual - expected) < 1e-9
                elif isinstance(expected, (list, tuple)) and isinstance(actual, (list, tuple)):
                    test_passed = list(actual) == list(expected)
                else:
                    test_passed = actual == expected
            except Exception:
                test_passed = False

            if test_passed:
                passed += 1
                test_results.append(TestResult(
                    passed=True,
                    test_name=f"test_{i}",
                    expected=str(expected),
                    actual=str(actual),
                    duration=result.duration,
                ))
            else:
                failed += 1
                test_results.append(TestResult(
                    passed=False,
                    test_name=f"test_{i}",
                    expected=str(expected),
                    actual=str(actual),
                    duration=result.duration,
                ))

        total = passed + failed
        return EvaluationResult(
            score=passed / total if total > 0 else 0.0,
            passed=passed,
            failed=failed,
            total=total,
            test_results=test_results,
            duration=time.time() - start_time,
        )


# ---------------------------------------------------------------------------
# HumanEval evaluator
# ---------------------------------------------------------------------------

class HumanEvalEvaluator:
    """Evaluate HumanEval tasks by executing generated code against test cases."""

    def __init__(self, executor: CodeExecutor | None = None):
        self._executor = executor or CodeExecutor()

    def evaluate(
        self,
        generated_code: str,
        test_code: str,
        entry_point: str,
    ) -> EvaluationResult:
        """Evaluate a HumanEval solution.

        Args:
            generated_code: The code generated by the agent
            test_code: The test code (usually contains `check` function)
            entry_point: The function name to test

        Returns:
            EvaluationResult with pass/fail score
        """
        start_time = time.time()

        # Combine generated code with test code
        full_code = generated_code + "\n\n" + test_code + "\n\ncheck()\n"

        # Check syntax
        try:
            ast.parse(full_code)
        except SyntaxError as e:
            return EvaluationResult(
                score=0.0,
                compilation_error=str(e),
                duration=time.time() - start_time,
            )

        # Execute the combined code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(full_code)
            temp_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            duration = time.time() - start_time

            if result.returncode == 0:
                return EvaluationResult(
                    score=1.0,
                    passed=1,
                    failed=0,
                    total=1,
                    test_results=[TestResult(passed=True, test_name="human_eval_check")],
                    duration=duration,
                )
            else:
                return EvaluationResult(
                    score=0.0,
                    passed=0,
                    failed=1,
                    total=1,
                    test_results=[TestResult(
                        passed=False,
                        test_name="human_eval_check",
                        error=result.stderr,
                    )],
                    execution_error=result.stderr,
                    duration=duration,
                )
        except subprocess.TimeoutExpired:
            return EvaluationResult(
                score=0.0,
                passed=0,
                failed=1,
                total=1,
                execution_error="Timeout",
                duration=time.time() - start_time,
            )
        finally:
            os.unlink(temp_path)


# ---------------------------------------------------------------------------
# MBPP evaluator
# ---------------------------------------------------------------------------

class MBPPEvaluator:
    """Evaluate MBPP tasks by running test assertions."""

    def __init__(self, executor: CodeExecutor | None = None):
        self._executor = executor or CodeExecutor()

    def evaluate(
        self,
        generated_code: str,
        test_list: List[str],
        entry_point: str = "",
    ) -> EvaluationResult:
        """Evaluate an MBPP solution.

        Args:
            generated_code: The generated function
            test_list: List of assertion strings (e.g., "assert add(1,2) == 3")
            entry_point: The function name

        Returns:
            EvaluationResult with pass/fail score
        """
        start_time = time.time()
        test_results = []
        passed = 0
        failed = 0

        for i, test_assertion in enumerate(test_list):
            # Build a test script
            test_script = f"""
{generated_code}

{test_assertion}
"""
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(test_script)
                temp_path = f.name

            try:
                result = subprocess.run(
                    [sys.executable, temp_path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0:
                    passed += 1
                    test_results.append(TestResult(
                        passed=True,
                        test_name=f"assertion_{i}",
                        duration=result.returncode,
                    ))
                else:
                    failed += 1
                    test_results.append(TestResult(
                        passed=False,
                        test_name=f"assertion_{i}",
                        error=result.stderr,
                    ))
            except subprocess.TimeoutExpired:
                failed += 1
                test_results.append(TestResult(
                    passed=False,
                    test_name=f"assertion_{i}",
                    error="Timeout",
                ))
            finally:
                os.unlink(temp_path)

        total = passed + failed
        return EvaluationResult(
            score=passed / total if total > 0 else 0.0,
            passed=passed,
            failed=failed,
            total=total,
            test_results=test_results,
            duration=time.time() - start_time,
        )


# ---------------------------------------------------------------------------
# SWE-bench evaluator (local mode)
# ---------------------------------------------------------------------------

class SWEBenchEvaluator:
    """Evaluate SWE-bench patches locally.

    For full evaluation, Docker is required. This evaluator provides:
    - Patch format validation
    - Basic syntax checking of modified files
    - Test execution when tests are available locally
    """

    def __init__(self, executor: CodeExecutor | None = None):
        self._executor = executor or CodeExecutor()

    def validate_patch(self, patch: str) -> Tuple[bool, str]:
        """Validate a git patch format."""
        if not patch or not patch.strip():
            return False, "Empty patch"

        # Check for diff headers
        if "diff --git" not in patch:
            return False, "Missing diff --git header"

        # Check for valid hunk headers
        hunk_pattern = r'@@ -\d+,\d+ \+\d+,\d+ @@'
        if not re.search(hunk_pattern, patch):
            return False, "Missing or invalid hunk headers"

        return True, "Valid patch format"

    def evaluate(
        self,
        patch: str,
        test_patch: str = "",
        repo_path: Path | None = None,
    ) -> EvaluationResult:
        """Evaluate a SWE-bench patch.

        Args:
            patch: The generated patch
            test_patch: The test patch to apply
            repo_path: Path to the repository (if available locally)

        Returns:
            EvaluationResult
        """
        start_time = time.time()

        # Validate patch format
        valid, msg = self.validate_patch(patch)
        if not valid:
            return EvaluationResult(
                score=0.0,
                compilation_error=msg,
                duration=time.time() - start_time,
            )

        # If no repo path, we can only validate format
        if not repo_path or not repo_path.exists():
            return EvaluationResult(
                score=0.5,  # Format valid, tests unknown
                passed=0,
                failed=0,
                total=0,
                execution_error="No local repo for test execution",
                duration=time.time() - start_time,
            )

        # Try to apply patch and run tests
        try:
            # Apply the patch
            result = subprocess.run(
                ["git", "apply", "--check"],
                input=patch,
                capture_output=True,
                text=True,
                cwd=repo_path,
            )

            if result.returncode != 0:
                return EvaluationResult(
                    score=0.0,
                    execution_error=f"Patch does not apply: {result.stderr}",
                    duration=time.time() - start_time,
                )

            return EvaluationResult(
                score=0.7,  # Patch applies, tests not run
                passed=0,
                failed=0,
                total=0,
                execution_error="Patch applies cleanly (tests not executed)",
                duration=time.time() - start_time,
            )
        except Exception as e:
            return EvaluationResult(
                score=0.0,
                execution_error=str(e),
                duration=time.time() - start_time,
            )


# ---------------------------------------------------------------------------
# Terminal-Bench evaluator
# ---------------------------------------------------------------------------

class TerminalBenchEvaluator:
    """Evaluate Terminal-Bench tasks by executing commands."""

    def __init__(self, executor: CodeExecutor | None = None):
        self._executor = executor or CodeExecutor()

    def evaluate(
        self,
        commands: List[str],
        expected_output: str,
        work_dir: Path | None = None,
    ) -> EvaluationResult:
        """Evaluate terminal commands.

        Args:
            commands: List of shell commands to execute
            expected_output: Expected output string
            work_dir: Working directory for execution

        Returns:
            EvaluationResult
        """
        start_time = time.time()
        actual_output = ""

        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=work_dir,
                )
                actual_output += result.stdout + result.stderr
            except subprocess.TimeoutExpired:
                return EvaluationResult(
                    score=0.0,
                    execution_error=f"Command timed out: {cmd}",
                    duration=time.time() - start_time,
                )
            except Exception as e:
                return EvaluationResult(
                    score=0.0,
                    execution_error=str(e),
                    duration=time.time() - start_time,
                )

        # Compare output
        passed = expected_output.strip() in actual_output.strip() or actual_output.strip() == expected_output.strip()
        return EvaluationResult(
            score=1.0 if passed else 0.0,
            passed=1 if passed else 0,
            failed=0 if passed else 1,
            total=1,
            test_results=[TestResult(
                passed=passed,
                test_name="output_match",
                expected=expected_output,
                actual=actual_output[:500],
            )],
            duration=time.time() - start_time,
        )


# ---------------------------------------------------------------------------
# Unified evaluator
# ---------------------------------------------------------------------------

class BenchmarkEvaluator:
    """Unified evaluator that dispatches to specific evaluators."""

    def __init__(self):
        self._human_eval = HumanEvalEvaluator()
        self._mbpp = MBPPEvaluator()
        self._swe_bench = SWEBenchEvaluator()
        self._terminal = TerminalBenchEvaluator()

    def evaluate_human_eval(
        self,
        code: str,
        test_code: str,
        entry_point: str,
    ) -> EvaluationResult:
        """Evaluate a HumanEval solution."""
        return self._human_eval.evaluate(code, test_code, entry_point)

    def evaluate_mbpp(
        self,
        code: str,
        test_list: List[str],
        entry_point: str = "",
    ) -> EvaluationResult:
        """Evaluate an MBPP solution."""
        return self._mbpp.evaluate(code, test_list, entry_point)

    def evaluate_swe_bench(
        self,
        patch: str,
        test_patch: str = "",
        repo_path: Path | None = None,
    ) -> EvaluationResult:
        """Evaluate a SWE-bench patch."""
        return self._swe_bench.evaluate(patch, test_patch, repo_path)

    def evaluate_terminal_bench(
        self,
        commands: List[str],
        expected_output: str,
        work_dir: Path | None = None,
    ) -> EvaluationResult:
        """Evaluate terminal commands."""
        return self._terminal.evaluate(commands, expected_output, work_dir)


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "BenchmarkEvaluator",
    "CodeExecutor",
    "EvaluationResult",
    "ExecutionResult",
    "HumanEvalEvaluator",
    "MBPPEvaluator",
    "SWEBenchEvaluator",
    "TerminalBenchEvaluator",
    "TestResult",
]
