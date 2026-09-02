"""Tests for AgentOS CLI."""

from __future__ import annotations

from click.testing import CliRunner

from agentos.cli import main


class TestCLI:
    def test_version(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "1.0.0" in result.output

    def test_status(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "running" in result.output

    def test_self_test(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["self-test"])
        assert result.exit_code == 0
        assert "PASS" in result.output

    def test_submit(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["submit", "test-agent", "--priority", "high"])
        assert result.exit_code == 0
        assert "submitted" in result.output

    def test_metrics(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["metrics"])
        assert result.exit_code == 0
