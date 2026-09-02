"""Tests for CodeReview Bot."""

from __future__ import annotations

import pytest

from codereview_bot.config import Config
from codereview_bot.models import Issue, PullRequest, ReviewResult, Severity
from codereview_bot.security import SecurityScanner
from codereview_bot.performance import PerformanceAnalyzer
from codereview_bot.coverage import CoverageAnalyzer
from codereview_bot.assignment import ReviewAssigner
from codereview_bot.rules import RuleEngine


class TestConfig:
    def test_default_config(self):
        config = Config()
        assert config.port == 8000
        assert config.host == "0.0.0.0"
        assert config.enable_security_scan is True

    def test_config_from_env(self, monkeypatch):
        monkeypatch.setenv("GITHUB_APP_ID", "12345")
        monkeypatch.setenv("PORT", "9000")
        config = Config.from_env()
        assert config.github_app_id == 12345
        assert config.port == 9000

    def test_validate_missing_app_id(self):
        config = Config()
        errors = config.validate()
        assert any("GITHUB_APP_ID" in e for e in errors)


class TestModels:
    def test_issue_creation(self):
        issue = Issue(
            file="test.py",
            line=10,
            severity=Severity.ERROR,
            message="Test issue",
            rule_id="TEST001",
            source="test",
        )
        assert issue.file == "test.py"
        assert issue.line == 10

    def test_pull_request_from_webhook(self):
        payload = {
            "pull_request": {
                "number": 42,
                "title": "Test PR",
                "body": "Description",
                "head": {"sha": "abc123", "ref": "feature"},
                "base": {"sha": "def456", "ref": "main"},
                "user": {"login": "testuser"},
                "diff_url": "https://example.com/diff",
                "changed_files": 3,
                "additions": 50,
                "deletions": 10,
            },
            "repository": {"full_name": "owner/repo"},
        }
        pr = PullRequest.from_webhook(payload)
        assert pr.number == 42
        assert pr.title == "Test PR"
        assert pr.user == "testuser"

    def test_review_result_add_issue(self):
        result = ReviewResult(pr_number=1, repo="owner/repo")
        result.add_issue(Issue(file="a.py", line=1, message="test"))
        assert len(result.issues) == 1


class TestSecurityScanner:
    def test_detects_hardcoded_password(self):
        scanner = SecurityScanner()
        diff = (
            "+++ b/config.py\n"
            "+# config\n"
            "+password = 'supersecret123'\n"
        )
        issues = scanner.scan_diff(diff)
        assert len(issues) >= 1
        assert any(i.rule_id == "SEC008" for i in issues)

    def test_detects_eval(self):
        scanner = SecurityScanner()
        diff = (
            "+++ b/main.py\n"
            "+result = eval(user_input)\n"
        )
        issues = scanner.scan_diff(diff)
        assert any(i.rule_id == "SEC001" for i in issues)

    def test_detects_sql_injection(self):
        scanner = SecurityScanner()
        diff = (
            "+++ b/db.py\n"
            "+query = f'SELECT * FROM users WHERE id = {user_id}'\n"
        )
        issues = scanner.scan_diff(diff)
        assert any("SQL" in i.message for i in issues)

    def test_no_issues_in_safe_code(self):
        scanner = SecurityScanner()
        diff = (
            "+++ b/utils.py\n"
            "+def add(a, b):\n"
            "+    return a + b\n"
        )
        issues = scanner.scan_diff(diff)
        assert len(issues) == 0


class TestPerformanceAnalyzer:
    def test_detects_range_len(self):
        analyzer = PerformanceAnalyzer()
        diff = (
            "+++ b/main.py\n"
            "+for i in range(len(items)):\n"
            "+    print(items[i])\n"
        )
        issues = analyzer.analyze_diff(diff)
        assert any(i.rule_id == "PERF001" for i in issues)

    def test_detects_select_star(self):
        analyzer = PerformanceAnalyzer()
        diff = (
            "+++ b/db.py\n"
            "+query = 'SELECT * FROM users'\n"
        )
        issues = analyzer.analyze_diff(diff)
        assert any(i.rule_id == "PERF005" for i in issues)


class TestCoverageAnalyzer:
    def test_detects_source_without_tests(self):
        analyzer = CoverageAnalyzer()
        diff = (
            "+++ b/src/main.py\n"
            "+def new_feature():\n"
            "+    pass\n"
        )
        result = analyzer.analyze_diff(diff)
        assert len(result["source_files"]) == 1
        assert len(result["test_files"]) == 0
        assert any("without" in n.lower() for n in result["notes"])

    def test_detects_test_file(self):
        analyzer = CoverageAnalyzer()
        diff = (
            "+++ b/tests/test_main.py\n"
            "+def test_feature():\n"
            "+    pass\n"
        )
        result = analyzer.analyze_diff(diff)
        assert len(result["test_files"]) == 1


class TestReviewAssigner:
    def test_assigns_based_on_pattern(self):
        assigner = ReviewAssigner()
        assigner.load_codeowners(
            "# Default\n"
            "* @default-reviewer\n"
            "\n"
            "# Python files\n"
            "*.py @python-reviewer\n"
            "\n"
            "# Frontend\n"
            "src/frontend/* @frontend-reviewer\n"
        )
        reviewers = assigner.get_reviewers_for_pr(["src/main.py"])
        assert "python-reviewer" in reviewers

    def test_default_reviewer(self):
        assigner = ReviewAssigner()
        assigner.load_codeowners("* @default-reviewer\n")
        reviewers = assigner.get_reviewers_for_pr(["README.md"])
        assert "default-reviewer" in reviewers

    def test_frontend_pattern(self):
        assigner = ReviewAssigner()
        assigner.load_codeowners("src/frontend/* @frontend-reviewer\n")
        reviewers = assigner.get_reviewers_for_pr(["src/frontend/App.tsx"])
        assert "frontend-reviewer" in reviewers


class TestRuleEngine:
    def test_evaluates_custom_rule(self):
        engine = RuleEngine()
        engine.load_rules(
            "rules:\n"
            "  - id: CUSTOM001\n"
            "    pattern: 'TODO|FIXME'\n"
            "    message: 'Found TODO/FIXME comment'\n"
            "    severity: info\n"
            "    enabled: true\n"
        )
        diff = (
            "+++ b/main.py\n"
            "+# TODO: fix this later\n"
            "+pass\n"
        )
        issues = engine.evaluate_diff(diff)
        assert len(issues) >= 1
        assert any(i.rule_id == "CUSTOM001" for i in issues)

    def test_disabled_rule_skipped(self):
        engine = RuleEngine()
        engine.load_rules(
            "rules:\n"
            "  - id: CUSTOM001\n"
            "    pattern: 'TODO'\n"
            "    message: 'Found TODO'\n"
            "    severity: info\n"
            "    enabled: false\n"
        )
        diff = "+++ b/main.py\n+# TODO: fix\n"
        issues = engine.evaluate_diff(diff)
        assert len(issues) == 0

    def test_file_pattern_filter(self):
        engine = RuleEngine()
        engine.load_rules(
            "rules:\n"
            "  - id: PY001\n"
            "    pattern: 'import pdb'\n"
            "    message: 'Debugger import found'\n"
            "    severity: warning\n"
            "    files: '.*\\.py$'\n"
            "    enabled: true\n"
        )
        diff = "+++ b/main.py\n+import pdb\n"
        issues = engine.evaluate_diff(diff)
        assert len(issues) == 1
