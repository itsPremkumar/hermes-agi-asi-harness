"""Tests for AI test case generation."""
import pytest

from testpilot.ai_test_gen import AITestGenerator
from testpilot.models import TestType


def test_generator_rule_based_login() -> None:
    """Rule-based generator should produce login test spec."""
    gen = AITestGenerator()
    spec = gen.generate("User can login with email and password", TestType.UNIT)

    assert spec.name.startswith("test_")
    assert "login" in spec.name
    assert spec.test_type == TestType.UNIT
    assert len(spec.assertions) >= 2
    assert len(spec.setup_steps) >= 1


def test_generator_rule_based_create() -> None:
    """Rule-based generator should handle create operations."""
    gen = AITestGenerator()
    spec = gen.generate("Admin can create new user account", TestType.INTEGRATION)

    assert "create" in spec.name
    assert any("201" in a or "create" in a.lower() for a in spec.assertions)


def test_generator_produces_valid_test_code() -> None:
    """Generated test code should be valid Python."""
    gen = AITestGenerator()
    spec = gen.generate("User can search products")
    code = gen.generate_test_code(spec)

    assert "def test_" in code
    assert "import pytest" in code
    # Should be parseable
    compile(code, "<test>", "exec")


def test_generator_custom_requirement() -> None:
    """Generator should handle arbitrary requirements gracefully."""
    gen = AITestGenerator()
    spec = gen.generate("The system shall validate input data")

    assert spec.name.startswith("test_")
    assert len(spec.assertions) >= 1


def test_generate_to_file_creates_file(tmp_path) -> None:
    """generate_to_file should create a Python test file."""
    gen = AITestGenerator()
    output_dir = tmp_path / "generated_tests"

    file_path = gen.generate_to_file("User can logout", str(output_dir))

    assert file_path.exists()
    assert file_path.suffix == ".py"
    content = file_path.read_text(encoding="utf-8")
    assert "def test_" in content
