"""
Tests for SelfHealer module.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.harness.improvement.healer import (
    DetectedIssue,
    HealResult,
    IssueCategory,
    SelfHealer,
)


@pytest.fixture
def healer(tmp_path: Path) -> SelfHealer:
    return SelfHealer(project_root=tmp_path, dry_run=True)


@pytest.fixture
def healer_live(tmp_path: Path) -> SelfHealer:
    return SelfHealer(project_root=tmp_path, dry_run=False)


@pytest.fixture
def file_with_bare_except(tmp_path: Path) -> Path:
    f = tmp_path / "bare_except.py"
    f.write_text("def risky():\n    try:\n        pass\n    except:\n        pass\n")
    return f


@pytest.fixture
def file_with_has_key(tmp_path: Path) -> Path:
    f = tmp_path / "haskey.py"
    f.write_text("def check(d):\n    if d.has_key('foo'):\n        return True\n    return False\n")
    return f


@pytest.fixture
def file_with_comparisons(tmp_path: Path) -> Path:
    f = tmp_path / "comparisons.py"
    f.write_text("def compare(x):\n    if x == None:\n        return True\n    return False\n")
    return f


@pytest.fixture
def file_with_syntax_error(tmp_path: Path) -> Path:
    f = tmp_path / "broken.py"
    f.write_text("def broken(\n  pass\n")
    return f


@pytest.fixture
def file_with_mutable_default(tmp_path: Path) -> Path:
    f = tmp_path / "mutable.py"
    f.write_text("def bad(items=[]):\n    items.append(1)\n    return items\n")
    return f


class TestDetectedIssue:
    def test_issue_creation(self) -> None:
        issue = DetectedIssue(
            file_path="test.py",
            line=10,
            category=IssueCategory.STYLE,
            severity="medium",
            message="Test issue",
        )
        assert issue.file_path == "test.py"
        assert issue.line == 10
        assert issue.fixable is True

    def test_issue_not_fixable(self) -> None:
        issue = DetectedIssue(
            file_path="test.py",
            line=1,
            category=IssueCategory.LOGIC,
            severity="high",
            message="Complex issue",
            fixable=False,
        )
        assert issue.fixable is False


class TestHealResult:
    def test_heal_result_defaults(self) -> None:
        r = HealResult(file_path="test.py")
        assert r.issues_detected == 0
        assert r.issues_fixed == 0
        assert r.success is True

    def test_heal_result_with_fixes(self) -> None:
        r = HealResult(
            file_path="test.py",
            issues_detected=5,
            issues_fixed=3,
            issues_skipped=2,
        )
        assert r.issues_fixed == 3
        assert r.issues_skipped == 2


class TestSelfHealer:
    def test_scan_nonexistent_file(self, healer: SelfHealer) -> None:
        issues = healer.scan_file("/nonexistent/file.py")
        assert issues == []

    def test_scan_non_python_file(self, healer: SelfHealer, tmp_path: Path) -> None:
        f = tmp_path / "readme.txt"
        f.write_text("Hello world")
        issues = healer.scan_file(f)
        assert issues == []

    def test_scan_bare_except(self, healer: SelfHealer, file_with_bare_except: Path) -> None:
        issues = healer.scan_file(file_with_bare_except)
        assert any("Bare except" in i.message for i in issues)

    def test_scan_has_key(self, healer: SelfHealer, file_with_has_key: Path) -> None:
        issues = healer.scan_file(file_with_has_key)
        assert any(".has_key(" in i.message for i in issues)

    def test_scan_comparisons(self, healer: SelfHealer, file_with_comparisons: Path) -> None:
        issues = healer.scan_file(file_with_comparisons)
        assert any("Comparison to True/False/None" in i.message for i in issues)

    def test_scan_syntax_error(self, healer: SelfHealer, file_with_syntax_error: Path) -> None:
        issues = healer.scan_file(file_with_syntax_error)
        assert any("Syntax error" in i.message for i in issues)

    def test_scan_mutable_default(self, healer: SelfHealer, file_with_mutable_default: Path) -> None:
        issues = healer.scan_file(file_with_mutable_default)
        assert any("Mutable default" in i.message for i in issues)

    def test_heal_bare_except(self, healer_live: SelfHealer, file_with_bare_except: Path) -> None:
        result = healer_live.heal_file(file_with_bare_except)
        assert result.issues_fixed >= 1
        content = file_with_bare_except.read_text()
        assert "except Exception:" in content

    def test_heal_has_key(self, healer_live: SelfHealer, file_with_has_key: Path) -> None:
        result = healer_live.heal_file(file_with_has_key)
        assert result.issues_fixed >= 1
        content = file_with_has_key.read_text()
        assert "in " in content
        assert ".has_key(" not in content

    def test_heal_comparisons(self, healer_live: SelfHealer, file_with_comparisons: Path) -> None:
        result = healer_live.heal_file(file_with_comparisons)
        assert result.issues_fixed >= 1
        content = file_with_comparisons.read_text()
        assert "is None" in content

    def test_heal_file_not_found(self, healer: SelfHealer) -> None:
        result = healer.heal_file("/nonexistent/file.py")
        assert result.success is False

    def test_heal_file_no_issues(self, healer: SelfHealer, tmp_path: Path) -> None:
        f = tmp_path / "clean.py"
        f.write_text("x = 1\n")
        result = healer.heal_file(f)
        assert result.issues_detected == 0
        assert result.issues_fixed == 0

    def test_heal_file_with_provided_issues(self, healer_live: SelfHealer, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("try:\n    pass\nexcept:\n    pass\n")
        issues = [
            DetectedIssue(
                file_path=str(f),
                line=3,
                category=IssueCategory.LOGIC,
                severity="high",
                message="Bare except clause",
                fixable=True,
                fix_description="Replace with except Exception:",
            )
        ]
        result = healer_live.heal_file(f, issues)
        assert result.issues_fixed == 1

    def test_scan_project(self, healer: SelfHealer, file_with_bare_except: Path, file_with_has_key: Path) -> None:
        issues = healer.scan_project([str(file_with_bare_except), str(file_with_has_key)])
        assert len(issues) >= 2

    def test_heal_project(self, healer_live: SelfHealer, file_with_bare_except: Path, file_with_has_key: Path) -> None:
        results = healer_live.heal_project([str(file_with_bare_except), str(file_with_has_key)])
        assert len(results) >= 1
        total_fixed = sum(r.issues_fixed for r in results)
        assert total_fixed >= 1

    def test_get_healing_summary(self, healer_live: SelfHealer, file_with_bare_except: Path) -> None:
        healer_live.heal_file(file_with_bare_except)
        summary = healer_live.get_healing_summary()
        assert summary["files_scanned"] >= 1
        assert summary["issues_fixed"] >= 1

    def test_heal_history(self, healer_live: SelfHealer, file_with_bare_except: Path) -> None:
        healer_live.heal_file(file_with_bare_except)
        assert len(healer_live.heal_history) == 1

    def test_dry_run_no_changes(self, healer: SelfHealer, file_with_bare_except: Path) -> None:
        original = file_with_bare_except.read_text()
        healer.heal_file(file_with_bare_except)
        assert file_with_bare_except.read_text() == original
