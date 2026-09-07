"""Tests for QualityChecker."""

from __future__ import annotations

import pytest

from harness.review.quality import QualityChecker, QualityIssue, QualityReport


class TestQualityCheckerInit:
    """Test QualityChecker initialization."""

    def test_default_init(self):
        """Test default initialization."""
        checker = QualityChecker()
        assert checker.MAX_LINE_LENGTH == 120
        assert checker.MAX_FUNCTION_LENGTH == 50
        assert checker.MAX_CYCLOMATIC_COMPLEXITY == 10


class TestCheckFiles:
    """Test check_files method."""

    def test_clean_file_has_no_critical_issues(self):
        """Test that a clean file has no critical issues."""
        checker = QualityChecker()
        files = {
            "good.py": '"""Good module."""\ndef add(a: int, b: int) -> int:\n    """Add two numbers."""\n    return a + b\n',
        }
        report = checker.check_files(files)
        critical = [i for i in report.issues if i.severity == "critical"]
        assert len(critical) == 0

    def test_long_line_detected(self):
        """Test detection of overly long lines."""
        checker = QualityChecker()
        long_line = "x = " + "a" * 200
        files = {"long.py": f'"""Module."""\n{long_line}\n'}
        report = checker.check_files(files)
        assert any(i.rule == "line-too-long" for i in report.issues)

    def test_trailing_whitespace_detected(self):
        """Test detection of trailing whitespace."""
        checker = QualityChecker()
        files = {"ws.py": '"""Module."""\nx = 1   \n'}
        report = checker.check_files(files)
        assert any(i.rule == "trailing-whitespace" for i in report.issues)

    def test_todo_comment_detected(self):
        """Test detection of TODO comments."""
        checker = QualityChecker()
        files = {"todo.py": '"""Module."""\n# TODO: fix this later\n'}
        report = checker.check_files(files)
        assert any(i.rule == "todo-comment" for i in report.issues)

    def test_bare_except_detected(self):
        """Test detection of bare except clauses."""
        checker = QualityChecker()
        files = {
            "exc.py": '"""Module."""\ndef foo() -> None:\n    """Do."""\n    try:\n        pass\n    except:\n        pass\n',
        }
        report = checker.check_files(files)
        assert any(i.rule == "bare-except" for i in report.issues)

    def test_eval_detected(self):
        """Test detection of eval usage."""
        checker = QualityChecker()
        files = {
            "eval_mod.py": '"""Module."""\ndef run(code: str) -> None:\n    """Run."""\n    eval(code)\n',
        }
        report = checker.check_files(files)
        assert any(i.rule == "dangerous-eval" for i in report.issues)

    def test_exec_detected(self):
        """Test detection of exec usage."""
        checker = QualityChecker()
        files = {
            "exec_mod.py": '"""Module."""\ndef run(code: str) -> None:\n    """Run."""\n    exec(code)\n',
        }
        report = checker.check_files(files)
        assert any(i.rule == "dangerous-exec" for i in report.issues)

    def test_syntax_error_detected(self):
        """Test detection of syntax errors."""
        checker = QualityChecker()
        files = {"broken.py": "def foo(\n  invalid\n"}
        report = checker.check_files(files)
        assert any(i.rule == "syntax-error" for i in report.issues)
        assert any(i.severity == "critical" for i in report.issues)

    def test_long_function_detected(self):
        """Test detection of overly long functions."""
        checker = QualityChecker()
        body = "\n".join([f"    x{i} = {i}" for i in range(60)])
        files = {
            "long_func.py": f'"""Module."""\ndef very_long() -> None:\n    """Long function."""\n{body}\n',
        }
        report = checker.check_files(files)
        assert any(i.rule == "function-too-long" for i in report.issues)

    def test_too_many_parameters_detected(self):
        """Test detection of too many parameters."""
        checker = QualityChecker()
        params = ", ".join([f"a{i}: int" for i in range(10)])
        files = {
            "params.py": f'"""Module."""\ndef many_params({params}) -> None:\n    """Many."""\n    pass\n',
        }
        report = checker.check_files(files)
        assert any(i.rule == "too-many-parameters" for i in report.issues)

    def test_missing_docstring_detected(self):
        """Test detection of missing docstrings."""
        checker = QualityChecker()
        files = {"nodoc.py": "def no_doc():\n    pass\n"}
        report = checker.check_files(files)
        assert any(i.rule == "missing-docstring" for i in report.issues)

    def test_high_complexity_detected(self):
        """Test detection of high cyclomatic complexity."""
        checker = QualityChecker()
        # Create a function with many branches
        body = "\n".join([f"    if x == {i}:\n        pass" for i in range(15)])
        files = {
            "complex.py": f'"""Module."""\ndef complex_func(x: int) -> None:\n    """Complex."""\n{body}\n',
        }
        report = checker.check_files(files)
        assert any(i.rule == "high-complexity" for i in report.issues)

    def test_duplicate_code_across_files(self):
        """Test detection of duplicate code across files."""
        checker = QualityChecker()
        duplicate_block = "    x = 1\n    y = 2\n    z = 3\n    w = 4"
        files = {
            "a.py": f'"""Module A."""\ndef func_a() -> None:\n    """A."""\n{duplicate_block}\n',
            "b.py": f'"""Module B."""\ndef func_b() -> None:\n    """B."""\n{duplicate_block}\n',
        }
        report = checker.check_files(files)
        assert any(i.rule == "duplicate-code" for i in report.issues)

    def test_overall_score_computed(self):
        """Test that overall score is computed."""
        checker = QualityChecker()
        files = {"simple.py": '"""Simple."""\ndef foo() -> None:\n    """Foo."""\n    pass\n'}
        report = checker.check_files(files)
        assert report.overall_score is not None
        assert 0 <= report.overall_score <= 100

    def test_metrics_computed(self):
        """Test that metrics are computed."""
        checker = QualityChecker()
        files = {"test.py": '"""Test."""\ndef foo() -> None:\n    """Foo."""\n    pass\n'}
        report = checker.check_files(files)
        assert "files_checked" in report.metrics
        assert report.metrics["files_checked"] == 1
