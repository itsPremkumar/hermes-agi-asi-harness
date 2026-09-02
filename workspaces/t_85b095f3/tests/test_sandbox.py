"""Tests for AgentOS sandbox module."""

from __future__ import annotations

import pytest

from agentos.sandbox import Sandbox, SandboxConfig, SandboxResult


class TestSandboxConfig:
    def test_default_config(self) -> None:
        config = SandboxConfig()
        assert config.max_cpu_time == 30.0
        assert config.max_memory_mb == 512
        assert config.allow_network is False

    def test_custom_config(self) -> None:
        config = SandboxConfig(max_cpu_time=10.0, allow_network=True)
        assert config.max_cpu_time == 10.0
        assert config.allow_network is True


class TestSandboxResult:
    def test_create_result(self) -> None:
        result = SandboxResult(
            returncode=0,
            stdout="output",
            stderr="",
            duration=1.5,
            memory_used_mb=128,
        )
        assert result.returncode == 0
        assert result.timed_out is False


class TestSandbox:
    def test_create_sandbox(self) -> None:
        sandbox = Sandbox()
        assert sandbox.config.max_cpu_time == 30.0

    def test_run_echo(self) -> None:
        sandbox = Sandbox(SandboxConfig(allow_write=True))
        result = sandbox.run(["echo", "hello"])
        assert result.returncode == 0
        assert "hello" in result.stdout

    def test_run_with_timeout(self) -> None:
        sandbox = Sandbox(SandboxConfig(max_cpu_time=1.0))
        # This should complete quickly
        result = sandbox.run(["echo", "fast"])
        assert result.timed_out is False

    def test_create_isolated_dir(self) -> None:
        sandbox = Sandbox()
        path = sandbox.create_isolated_dir()
        assert path.exists()
        assert path.is_dir()
        # Cleanup
        path.rmdir()
