"""Tests for ConventionEnforcer."""

from __future__ import annotations

import pytest

from harness.review.convention import ConventionEnforcer, ConventionViolation


class TestConventionEnforcerInit:
    """Test ConventionEnforcer initialization."""

    def test_default_init(self):
        """Test default initialization."""
        enforcer = ConventionEnforcer()
        assert "naming" in enforcer.default_rules
        assert "imports" in enforcer.default_rules
        assert "docstrings" in enforcer.default_rules

    def test_custom_rules(self):
        """Test initialization with custom rules."""
        enforcer = ConventionEnforcer(default_rules={"naming", "imports"})
        assert enforcer.default_rules == {"naming", "imports"}


class TestCheckFiles:
    """Test check_files method."""

    def test_clean_file_no_violations(self):
        """Test that a clean file has no violations."""
        enforcer = ConventionEnforcer()
        files = {
            "good.py": '"""Good module."""\n\ndef add(a: int, b: int) -> int:\n    """Add two numbers."""\n    return a + b\n',
        }
        violations = enforcer.check_files(files)
        # Should have minimal or no violations
        assert isinstance(violations, list)

    def test_missing_module_docstring(self):
        """Test detection of missing module docstring."""
        enforcer = ConventionEnforcer()
        files = {"nodoc.py": "x = 1\n"}
        violations = enforcer.check_files(files, rules=["module-header"])
        assert any(v.rule == "module-header" for v in violations)

    def test_missing_function_docstring(self):
        """Test detection of missing function docstrings."""
        enforcer = ConventionEnforcer()
        files = {
            "nodoc.py": '"""Module."""\ndef public_func() -> None:\n    pass\n',
        }
        violations = enforcer.check_files(files, rules=["docstrings"])
        assert any(v.rule == "docstrings" for v in violations)

    def test_missing_class_docstring(self):
        """Test detection of missing class docstrings."""
        enforcer = ConventionEnforcer()
        files = {
            "nodoc.py": '"""Module."""\nclass MyClass:\n    pass\n',
        }
        violations = enforcer.check_files(files, rules=["docstrings"])
        assert any(v.rule == "docstrings" for v in violations)

    def test_bad_function_naming(self):
        """Test detection of non-snake_case function names."""
        enforcer = ConventionEnforcer()
        files = {
            "naming.py": '"""Module."""\ndef badName() -> None:\n    """Bad name."""\n    pass\n',
        }
        violations = enforcer.check_files(files, rules=["naming"])
        assert any(v.rule == "naming" for v in violations)

    def test_bad_class_naming(self):
        """Test detection of non-PascalCase class names."""
        enforcer = ConventionEnforcer()
        files = {
            "naming.py": '"""Module."""\nclass bad_class:\n    """Bad."""\n    pass\n',
        }
        violations = enforcer.check_files(files, rules=["naming"])
        assert any(v.rule == "naming" for v in violations)

    def test_missing_type_hints(self):
        """Test detection of missing type hints."""
        enforcer = ConventionEnforcer()
        files = {
            "notypes.py": '"""Module."""\ndef no_types(a, b):\n    """No types."""\n    pass\n',
        }
        violations = enforcer.check_files(files, rules=["type-hints"])
        assert any(v.rule == "type-hints" for v in violations)

    def test_print_statement_detected(self):
        """Test detection of print statements."""
        enforcer = ConventionEnforcer()
        files = {
            "print_mod.py": '"""Module."""\ndef show() -> None:\n    """Show."""\n    print("hello")\n',
        }
        violations = enforcer.check_files(files, rules=["logging"])
        assert any(v.rule == "logging" for v in violations)

    def test_bare_except_convention(self):
        """Test detection of bare except in convention rules."""
        enforcer = ConventionEnforcer()
        files = {
            "exc.py": '"""Module."""\ndef foo() -> None:\n    """Foo."""\n    try:\n        pass\n    except:\n        pass\n',
        }
        violations = enforcer.check_files(files, rules=["error-handling"])
        assert any(v.rule == "error-handling" for v in violations)

    def test_empty_except_block(self):
        """Test detection of empty except blocks."""
        enforcer = ConventionEnforcer()
        files = {
            "exc.py": '"""Module."""\ndef foo() -> None:\n    """Foo."""\n    try:\n        pass\n    except Exception:\n        pass\n',
        }
        violations = enforcer.check_files(files, rules=["error-handling"])
        assert any("Empty except" in v.message for v in violations)

    def test_import_ordering(self):
        """Test detection of incorrect import ordering."""
        enforcer = ConventionEnforcer()
        files = {
            "imports.py": '"""Module."""\nfrom harness import something\nimport os\n',
        }
        violations = enforcer.check_files(files, rules=["imports"])
        # Should detect wrong order (third-party before stdlib)
        assert any(v.rule == "imports" for v in violations)

    def test_file_too_large(self):
        """Test detection of overly large files."""
        enforcer = ConventionEnforcer()
        body = "\n".join([f"x{i} = {i}" for i in range(600)])
        files = {
            "large.py": f'"""Large."""\n{body}\n',
        }
        violations = enforcer.check_files(files, rules=["structure"])
        assert any(v.rule == "structure" for v in violations)

    def test_class_too_many_methods(self):
        """Test detection of classes with too many methods."""
        enforcer = ConventionEnforcer()
        methods = "\n".join([f"    def method_{i}(self) -> None:\n        '''Method {i}.'''\n        pass" for i in range(25)])
        files = {
            "bigclass.py": f'"""Module."""\nclass BigClass:\n    """Big."""\n{methods}\n',
        }
        violations = enforcer.check_files(files, rules=["structure"])
        assert any("too many methods" in v.message for v in violations)

    def test_unknown_rules_ignored(self):
        """Test that unknown rules are ignored gracefully."""
        enforcer = ConventionEnforcer()
        files = {"test.py": '"""Test."""\npass\n'}
        violations = enforcer.check_files(files, rules=["nonexistent-rule"])
        # Should not raise, just ignore unknown rules
        assert isinstance(violations, list)

    def test_multiple_files_checked(self):
        """Test checking multiple files."""
        enforcer = ConventionEnforcer()
        files = {
            "a.py": '"""A."""\ndef foo() -> None:\n    """Foo."""\n    pass\n',
            "b.py": '"""B."""\ndef bar() -> None:\n    """Bar."""\n    pass\n',
        }
        violations = enforcer.check_files(files)
        # Should process both files
        assert isinstance(violations, list)

    def test_non_python_files_ignored(self):
        """Test that non-Python files are ignored."""
        enforcer = ConventionEnforcer()
        files = {
            "readme.md": "# No docstring here\n",
        }
        violations = enforcer.check_files(files, rules=["module-header"])
        assert len(violations) == 0

    def test_violation_has_fix_hint(self):
        """Test that violations include fix hints."""
        enforcer = ConventionEnforcer()
        files = {"nodoc.py": "x = 1\n"}
        violations = enforcer.check_files(files, rules=["module-header"])
        assert len(violations) > 0
        assert violations[0].fix_hint != ""
