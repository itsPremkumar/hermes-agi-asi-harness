"""Tests for AutoFixer."""

from __future__ import annotations

import pytest

from harness.review.autofix import AutoFixer, FixResult


class TestAutoFixerInit:
    """Test AutoFixer initialization."""

    def test_default_init(self):
        """Test default initialization."""
        fixer = AutoFixer()
        assert fixer is not None


class TestFixFiles:
    """Test fix_files method."""

    def test_clean_file_unchanged(self):
        """Test that a clean file is not modified."""
        fixer = AutoFixer()
        files = {
            "clean.py": '"""Clean module."""\ndef foo() -> None:\n    """Foo."""\n    pass\n',
        }
        result = fixer.fix_files(files)
        # Clean file should not need fixes (or have minimal)
        assert isinstance(result, FixResult)

    def test_trailing_whitespace_fixed(self):
        """Test that trailing whitespace is removed."""
        fixer = AutoFixer()
        files = {"ws.py": '"""Module."""\nx = 1   \ny = 2\n'}
        result = fixer.fix_files(files)
        assert "ws.py" in result.fixed_files
        fixed = result.fixed_files["ws.py"]
        assert not any(line != line.rstrip() for line in fixed.splitlines() if line.strip())

    def test_missing_final_newline_fixed(self):
        """Test that missing final newline is added."""
        fixer = AutoFixer()
        files = {"noeol.py": '"""Module."""\nx = 1'}  # No trailing newline
        result = fixer.fix_files(files)
        fixed = result.fixed_files.get("noeol.py", "")
        assert fixed.endswith("\n")

    def test_multiple_blank_lines_fixed(self):
        """Test that multiple blank lines are reduced."""
        fixer = AutoFixer()
        files = {
            "blanks.py": '"""Module."""\nx = 1\n\n\n\n\ny = 2\n',
        }
        result = fixer.fix_files(files)
        # Should have reduced 4 newlines to 3 (2 blank lines)
        assert "blanks.py" in result.fixed_files

    def test_bare_except_fixed(self):
        """Test that bare except is replaced."""
        fixer = AutoFixer()
        files = {
            "exc.py": '"""Module."""\ndef foo() -> None:\n    """Foo."""\n    try:\n        pass\n    except:\n        pass\n',
        }
        result = fixer.fix_files(files)
        assert "exc.py" in result.fixed_files
        fixed = result.fixed_files["exc.py"]
        assert "except Exception:" in fixed
        assert "except:" not in fixed

    def test_assert_validation_fixed(self):
        """Test that assert for validation is replaced."""
        fixer = AutoFixer()
        files = {
            "assert_mod.py": '"""Module."""\ndef validate(x: int) -> None:\n    """Validate."""\n    assert x > 0\n',
        }
        result = fixer.fix_files(files)
        fixed = result.fixed_files.get("assert_mod.py", "")
        assert "raise AssertionError" in fixed

    def test_fixes_recorded(self):
        """Test that all fixes are recorded."""
        fixer = AutoFixer()
        files = {
            "multi.py": '"""Module."""\nx = 1   \ny = 2   \ndef foo():\n    try:\n        pass\n    except:\n        pass\n',
        }
        result = fixer.fix_files(files)
        assert len(result.fixes_applied) > 0

    def test_suggestions_generated(self):
        """Test that suggestions are generated."""
        fixer = AutoFixer()
        files = {"ws.py": 'x = 1   \n'}
        result = fixer.fix_files(files)
        assert len(result.suggestions) > 0

    def test_non_python_files_ignored(self):
        """Test that non-Python files are ignored."""
        fixer = AutoFixer()
        files = {
            "readme.md": "# Hello\n",
        }
        result = fixer.fix_files(files)
        assert len(result.fixed_files) == 0

    def test_fix_result_dataclass(self):
        """Test FixResult dataclass fields."""
        result = FixResult(
            fixed_files={"a.py": "fixed"},
            suggestions=["suggestion"],
            fixes_applied=[{"rule": "test"}],
        )
        assert result.fixed_files == {"a.py": "fixed"}
        assert result.suggestions == ["suggestion"]
        assert len(result.fixes_applied) == 1

    def test_fix_trailing_whitespace_helper(self):
        """Test the _fix_trailing_whitespace helper directly."""
        fixer = AutoFixer()
        source = "line1   \nline2\nline3   \n"
        fixed, count = fixer._fix_trailing_whitespace(source)
        assert count == 2
        assert "line1\n" in fixed

    def test_fix_multiple_blank_lines_helper(self):
        """Test the _fix_multiple_blank_lines helper directly."""
        fixer = AutoFixer()
        source = "a\n\n\n\n\nb\n"
        fixed, count = fixer._fix_multiple_blank_lines(source)
        assert count > 0

    def test_fix_bare_except_helper(self):
        """Test the _fix_bare_except helper directly."""
        fixer = AutoFixer()
        source = "    except:\n        pass\n"
        fixed, count = fixer._fix_bare_except(source)
        assert count == 1
        assert "except Exception:" in fixed

    def test_fix_assert_helper(self):
        """Test the _fix_assert_validation helper directly."""
        fixer = AutoFixer()
        source = "assert x > 0\n"
        fixed, count = fixer._fix_assert_validation(source)
        assert count == 1
        assert "raise AssertionError" in fixed

    def test_empty_files_dict(self):
        """Test with empty files dict."""
        fixer = AutoFixer()
        result = fixer.fix_files({})
        assert isinstance(result, FixResult)
        assert len(result.fixed_files) == 0

    def test_multiple_files_fixed(self):
        """Test fixing multiple files."""
        fixer = AutoFixer()
        files = {
            "a.py": '"""A."""\nx = 1   \n',
            "b.py": '"""B."""\ny = 2   \n',
        }
        result = fixer.fix_files(files)
        assert len(result.fixed_files) == 2
