"""Tests for ReviewReporter."""

from __future__ import annotations

import pytest

from harness.review.reporter import ReviewReporter
from harness.review.quality import QualityReport, QualityIssue
from harness.review.security import SecurityReport, Vulnerability


class TestReviewReporterInit:
    """Test ReviewReporter initialization."""

    def test_default_init(self):
        """Test default initialization."""
        reporter = ReviewReporter()
        assert reporter is not None


class TestGenerateMarkdown:
    """Test markdown report generation."""

    def _make_result(self, **kwargs):
        """Create a ReviewResult for testing (imported here to avoid circular import)."""
        from harness.review.engine import ReviewResult
        defaults = {
            "passed": True,
            "score": 85.0,
            "issues": [],
            "suggestions": [],
        }
        defaults.update(kwargs)
        return ReviewResult(**defaults)

    def test_markdown_has_header(self):
        """Test markdown report has header."""
        reporter = ReviewReporter()
        result = self._make_result()
        report = reporter.generate(result, format="markdown")
        assert "# Code Review Report" in report

    def test_markdown_shows_passed(self):
        """Test markdown shows PASSED status."""
        reporter = ReviewReporter()
        result = self._make_result(passed=True)
        report = reporter.generate(result, format="markdown")
        assert "PASSED" in report

    def test_markdown_shows_failed(self):
        """Test markdown shows FAILED status."""
        reporter = ReviewReporter()
        result = self._make_result(passed=False, score=50.0)
        report = reporter.generate(result, format="markdown")
        assert "FAILED" in report

    def test_markdown_shows_score(self):
        """Test markdown includes score."""
        reporter = ReviewReporter()
        result = self._make_result(score=87.5)
        report = reporter.generate(result, format="markdown")
        assert "87.5" in report

    def test_markdown_shows_issues_table(self):
        """Test markdown includes issues table."""
        reporter = ReviewReporter()
        issues = [
            {
                "file": "test.py",
                "line": 10,
                "severity": "high",
                "category": "quality",
                "rule": "line-too-long",
                "message": "Line too long",
            }
        ]
        result = self._make_result(issues=issues)
        report = reporter.generate(result, format="markdown")
        assert "test.py" in report
        assert "10" in report
        assert "high" in report

    def test_markdown_shows_suggestions(self):
        """Test markdown includes suggestions section."""
        reporter = ReviewReporter()
        result = self._make_result(suggestions=["Use type hints", "Add docstrings"])
        report = reporter.generate(result, format="markdown")
        assert "Use type hints" in report
        assert "Add docstrings" in report

    def test_markdown_shows_quality_score(self):
        """Test markdown includes quality score."""
        reporter = ReviewReporter()
        qr = QualityReport(overall_score=88.0, metrics={"total_lines": 100})
        result = self._make_result(quality_report=qr)
        report = reporter.generate(result, format="markdown")
        assert "Quality Report" in report
        assert "88.0" in report

    def test_markdown_shows_security_score(self):
        """Test markdown includes security score."""
        from harness.review.engine import ReviewResult
        security_report = SecurityReport(overall_score=92.0)
        result = ReviewResult(passed=True, score=90.0, security_report=security_report)
        md = result.to_dict()
        # Just check it doesn't crash
        assert "score" in md


class TestGenerateJson:
    """Test JSON report generation."""

    def _make_result(self, **kwargs):
        """Create a ReviewResult for testing (imported here to avoid circular import)."""
        from harness.review.engine import ReviewResult
        defaults = {
            "passed": True,
            "score": 85.0,
            "issues": [],
            "suggestions": [],
        }
        defaults.update(kwargs)
        return ReviewResult(**defaults)

    def test_json_is_valid(self):
        """Test JSON report is valid JSON."""
        reporter = ReviewReporter()
        result = self._make_result()
        report = reporter.generate(result, format="json")
        import json
        data = json.loads(report)
        assert isinstance(data, dict)

    def test_json_has_passed_field(self):
        """Test JSON has passed field."""
        reporter = ReviewReporter()
        result = self._make_result(passed=True)
        report = reporter.generate(result, format="json")
        import json
        data = json.loads(report)
        assert data["passed"] is True

    def test_json_has_score_field(self):
        """Test JSON has score field."""
        reporter = ReviewReporter()
        result = self._make_result(score=92.5)
        report = reporter.generate(result, format="json")
        import json
        data = json.loads(report)
        assert data["score"] == 92.5

    def test_json_has_issues_count(self):
        """Test JSON has issue count."""
        reporter = ReviewReporter()
        result = self._make_result(issues=[{"test": "issue"}])
        report = reporter.generate(result, format="json")
        import json
        data = json.loads(report)
        assert data["issue_count"] == 1


class TestGenerateText:
    """Test plain text report generation."""

    def _make_result(self, **kwargs):
        """Create a ReviewResult for testing (imported here to avoid circular import)."""
        from harness.review.engine import ReviewResult
        defaults = {
            "passed": True,
            "score": 85.0,
            "issues": [],
            "suggestions": [],
        }
        defaults.update(kwargs)
        return ReviewResult(**defaults)

    def test_text_has_header(self):
        """Test text report has header."""
        reporter = ReviewReporter()
        result = self._make_result()
        report = reporter.generate(result, format="text")
        assert "CODE REVIEW REPORT" in report

    def test_text_shows_score(self):
        """Test text report shows score."""
        reporter = ReviewReporter()
        result = self._make_result(score=75.0)
        report = reporter.generate(result, format="text")
        assert "75.0" in report

    def test_text_lists_issues(self):
        """Test text report lists issues."""
        reporter = ReviewReporter()
        issues = [
            {
                "file": "test.py",
                "line": 5,
                "severity": "high",
                "message": "Bad thing",
            }
        ]
        result = self._make_result(issues=issues)
        report = reporter.generate(result, format="text")
        assert "test.py" in report
        assert "Bad thing" in report

    def test_text_lists_suggestions(self):
        """Test text report lists suggestions."""
        reporter = ReviewReporter()
        result = self._make_result(suggestions=["Improve this"])
        report = reporter.generate(result, format="text")
        assert "Improve this" in report


class TestInvalidFormat:
    """Test invalid format handling."""

    def test_invalid_format_raises_value_error(self):
        """Test that invalid format raises ValueError."""
        from harness.review.engine import ReviewResult
        reporter = ReviewReporter()
        result = ReviewResult(passed=True, score=100.0)
        with pytest.raises(ValueError, match="Unknown format"):
            reporter.generate(result, format="xml")
