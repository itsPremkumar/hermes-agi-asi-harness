"""Tests for CLI commands."""
import json
from pathlib import Path
from click.testing import CliRunner

from testpilot.cli import main


def test_cli_version() -> None:
    """CLI should display version."""
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "1.0.0" in result.output


def test_cli_help() -> None:
    """CLI should display help."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "TestPilot" in result.output


def test_analyze_command() -> None:
    """Analyze command should work on a directory."""
    runner = CliRunner()
    result = runner.invoke(main, ["analyze", "testpilot"])
    # Should not crash even if no gaps found
    assert result.exit_code == 0


def test_generate_command(tmp_path: Path) -> None:
    """Generate command should create a test file."""
    runner = CliRunner()
    result = runner.invoke(main, [
        "generate",
        "--requirement", "User can login",
        "--output-dir", str(tmp_path),
    ])
    assert result.exit_code == 0


def test_data_command(tmp_path: Path) -> None:
    """Data command should generate synthetic data."""
    runner = CliRunner()
    result = runner.invoke(main, [
        "data", "--type", "users", "--count", "5",
        "--output", str(tmp_path / "users.json"),
    ])
    assert result.exit_code == 0
    assert (tmp_path / "users.json").exists()


def test_init_command(tmp_path: Path, monkeypatch) -> None:
    """Init command should create a config file."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--output-dir", "."])
    assert result.exit_code == 0
    assert (tmp_path / "testpilot.yaml").exists()


def test_perf_command_locust(tmp_path: Path) -> None:
    """Perf command with locust should fail gracefully if not installed."""
    runner = CliRunner()
    result = runner.invoke(main, [
        "perf", "--tool", "locust", "--host", "http://localhost",
        "--users", "1", "--duration", "1s",
    ])
    # Command should not crash; may fail if locust not installed
    assert result.exit_code in (0, 1, 2)


def test_gate_command_no_tests(tmp_path: Path, monkeypatch) -> None:
    """Gate command should run even without tests."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["gate", "--output", "."])
    # Should not crash
    assert result.exit_code in (0, 1)
