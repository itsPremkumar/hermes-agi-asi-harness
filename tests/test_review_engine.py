"""Tests for ReviewEngine."""

from __future__ import annotations

import pytest

from harness.review.engine import ReviewEngine, ReviewResult, ReviewSeverity


class TestReviewEngineInit:
    """Test ReviewEngine initialization."""

    def test_default_init(self):
        """Test default initialization."""
        engine = ReviewEngine()
        assert engine.pass_threshold == ReviewEngine.DEFAULT_PASS_THRESHOLD
        assert engine.quality_checker is not None
        assert engine.security_scanner is not None
        assert engine.convention_enforcer is not None
        assert engine.autofixer is not None
        assert engine.reporter is not None

    def test_custom_threshold(self):
        """Test custom pass threshold."""
        engine = ReviewEngine(pass_threshold=80.0)
        assert engine.pass_threshold == 80.0

    def test_zero_threshold(self):
        """Test zero threshold."""
        engine = ReviewEngine(pass_threshold=0.0)
        assert engine.pass_threshold == 0.0

    def test_hundred_threshold(self):
        """Test 100 threshold."""
        engine = ReviewEngine(pass_threshold=100.0)
        assert engine.pass_threshold == 100.0


class TestReviewFiles:
    """Test review_files method."""

    def test_review_clean_file_passes(self):
        """Test that a clean file passes review."""
        engine = ReviewEngine()
        files = {
            "good.py": '"""Good module."""\n\ndef add(a: int, b: int) -> int:\n    """Add two numbers."""\n    return a + b\n',
        }
        result = engine.review_files(files)
        assert isinstance(result, ReviewResult)
        assert result.passed is True
        assert result.score > 70.0
        assert result.metadata["files_reviewed"] == 1

    def test_review_with_syntax_error(self):
        """Test review catches syntax errors."""
        engine = ReviewEngine()
        files = {"broken.py": "def foo(\n  invalid syntax\n"}
        result = engine.review_files(files)
        assert result.passed is False
        assert any("Syntax error" in issue["message"] for issue in result.issues)

    def test_review_multiple_files(self):
        """Test reviewing multiple files."""
        engine = ReviewEngine()
        files = {
            "a.py": '"""Module A."""\ndef foo() -> None:\n    """Do something."""\n    pass\n',
            "b.py": '"""Module B."""\ndef bar() -> None:\n    """Do other."""\n    pass\n',
        }
        result = engine.review_files(files)
        assert result.metadata["files_reviewed"] == 2

    def test_review_ignores_non_python_files(self):
        """Test that non-Python files are ignored."""
        engine = ReviewEngine()
        files = {
            "readme.md": "# Readme\nThis is bad code: eval('dangerous')",
        }
        result = engine.review_files(files)
        # Should not have any security issues from the markdown
        assert not any(issue["category"] == "security" for issue in result.issues)

    def test_review_with_security_issues(self):
        """Test review detects security issues."""
        engine = ReviewEngine()
        files = {
            "bad.py": '"""Bad module."""\nimport pickle\n\ndef load(data: bytes) -> None:\n    """Load data."""\n    pickle.loads(data)\n',
        }
        result = engine.review_files(files)
        assert any(issue["category"] == "security" for issue in result.issues)

    def test_review_with_auto_fix(self):
        """Test review with auto-fix enabled."""
        engine = ReviewEngine()
        files = {
            "fixable.py": '"""Module with trailing whitespace."""\ndef foo() -> None:\n    """Do something."""\n    pass   \n',
        }
        result = engine.review_files(files, auto_fix=True)
        assert len(result.fixed_code) > 0

    def test_review_with_convention_override(self):
        """Test review with custom convention rules."""
        engine = ReviewEngine()
        files = {
            "test.py": '"""Test."""\ndef foo():\n    pass\n',
        }
        result = engine.review_files(files, conventions=["naming"])
        # Should only check naming
        assert result.score > 0

    def test_review_empty_files_dict(self):
        """Test review with empty files."""
        engine = ReviewEngine()
        result = engine.review_files({})
        assert result.passed is True
        assert result.metadata["files_reviewed"] == 0


class TestReviewDiff:
    """Test review_diff method."""

    def test_review_valid_diff(self):
        """Test reviewing a valid diff."""
        engine = ReviewEngine()
        diff = """diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1,3 +1,3 @@
-old line
+new line 1
+new line 2
"""
        result = engine.review_diff(diff)
        assert isinstance(result, ReviewResult)
        assert result.metadata["files_reviewed"] == 1

    def test_review_empty_diff(self):
        """Test reviewing an empty diff."""
        engine = ReviewEngine()
        result = engine.review_diff("")
        assert result.passed is False
        assert result.score == 0.0

    def test_review_diff_with_multiple_files(self):
        """Test reviewing a diff with multiple files."""
        engine = ReviewEngine()
        diff = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,2 +1,2 @@
-old
+new_a
diff --git a/b.py b/b.py
--- a/b.py
+++ b/b.py
@@ -1,2 +1,2 @@
-old
+new_b
"""
        result = engine.review_diff(diff)
        assert result.metadata["files_reviewed"] == 2


class TestGenerateReport:
    """Test generate_report method."""

    def test_generate_markdown_report(self):
        """Test markdown report generation."""
        engine = ReviewEngine()
        files = {
            "test.py": '"""Test."""\ndef foo() -> None:\n    pass\n',
        }
        result = engine.review_files(files)
        report = engine.generate_report(result, format="markdown")
        assert "# Code Review Report" in report
        assert "PASSED" in report or "FAILED" in report

    def test_generate_json_report(self):
        """Test JSON report generation."""
        engine = ReviewEngine()
        files = {
            "test.py": '"""Test."""\ndef foo() -> None:\n    pass\n',
        }
        result = engine.review_files(files)
        report = engine.generate_report(result, format="json")
        import json
        data = json.loads(report)
        assert "passed" in data
        assert "score" in data

    def test_generate_text_report(self):
        """Test text report generation."""
        engine = ReviewEngine()
        files = {
            "test.py": '"""Test."""\ndef foo() -> None:\n    pass\n',
        }
        result = engine.review_files(files)
        report = engine.generate_report(result, format="text")
        assert "CODE REVIEW REPORT" in report

    def test_generate_invalid_format_raises(self):
        """Test that invalid format raises ValueError."""
        engine = ReviewEngine()
        result = ReviewResult(passed=True, score=100.0)
        with pytest.raises(ValueError, match="Unknown format"):
            engine.generate_report(result, format="invalid")


class TestParseDiff:
    """Test _parse_diff static method."""

    def test_parse_simple_diff(self):
        """Test parsing a simple diff."""
        diff = """diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1,3 +1,3 @@
-old content
+new content
"""
        result = ReviewEngine._parse_diff(diff)
        assert "test.py" in result
        assert "new content" in result["test.py"]

    def test_parse_diff_preserves_context(self):
        """Test that context lines are preserved."""
        diff = """diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1,5 +1,5 @@
 context before
-old line
+new line
 context after
"""
        result = ReviewEngine._parse_diff(diff)
        assert "context before" in result["test.py"]
        assert "context after" in result["test.py"]

    def test_parse_empty_diff(self):
        """Test parsing empty diff."""
        result = ReviewEngine._parse_diff("")
        assert result == {}


class TestSeverityWeights:
    """Test severity weight configuration."""

    def test_severity_weights_exist(self):
        """Test that all severity levels have weights."""
        weights = ReviewEngine.SEVERITY_WEIGHTS
        assert ReviewSeverity.INFO in weights
        assert ReviewSeverity.LOW in weights
        assert ReviewSeverity.MEDIUM in weights
        assert ReviewSeverity.HIGH in weights
        assert ReviewSeverity.CRITICAL in weights

    def test_critical_weight_highest(self):
        """Test that critical has the highest weight."""
        weights = ReviewEngine.SEVERITY_WEIGHTS
        assert weights[ReviewSeverity.CRITICAL] > weights[ReviewSeverity.HIGH]
        assert weights[ReviewSeverity.HIGH] > weights[ReviewSeverity.MEDIUM]
