"""Configuration management for MCPTest."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field


class ServerTarget(BaseModel):
    """Target MCP server configuration."""

    name: str
    command: str = ""
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    url: str = ""
    transport: str = "stdio"


class ThresholdConfig(BaseModel):
    """Pass/fail thresholds."""

    min_requests_per_second: float = 10.0
    max_avg_latency_ms: float = 500.0
    max_p99_latency_ms: float = 2000.0
    max_memory_mb: float = 512.0
    max_critical_findings: int = 0
    max_high_findings: int = 2
    min_conformance_pass_rate: float = 0.95


class Config(BaseModel):
    """Top-level MCPTest configuration."""

    target: ServerTarget
    thresholds: ThresholdConfig = Field(default_factory=ThresholdConfig)
    output_dir: str = "mcptest-report"
    report_formats: list[str] = Field(default_factory=lambda: ["html", "json"])
    fuzzing_iterations: int = 1000
    benchmark_duration_seconds: int = 30
    benchmark_concurrency: int = 10
    security_scan_enabled: bool = True
    compliance_badge_enabled: bool = True
    registry_enabled: bool = False
    registry_url: str = "https://mcphub.dev/api/v1"
    verbose: bool = False


def load_config(path: str | Path) -> Config:
    """Load configuration from a YAML file.

    Falls back to defaults if the file does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}

    return Config(**data)


def load_config_from_env() -> Config:
    """Load configuration from environment variables."""
    target = ServerTarget(
        name=os.environ.get("MCPTEST_TARGET_NAME", "default"),
        command=os.environ.get("MCPTEST_TARGET_COMMAND", ""),
        args=os.environ.get("MCPTEST_TARGET_ARGS", "").split(),
        url=os.environ.get("MCPTEST_TARGET_URL", ""),
        transport=os.environ.get("MCPTEST_TARGET_TRANSPORT", "stdio"),
    )

    return Config(
        target=target,
        output_dir=os.environ.get("MCPTEST_OUTPUT_DIR", "mcptest-report"),
        verbose=os.environ.get("MCPTEST_VERBOSE", "").lower() in ("1", "true", "yes"),
    )


DEFAULT_CONFIG = Config(
    target=ServerTarget(name="default"),
)
