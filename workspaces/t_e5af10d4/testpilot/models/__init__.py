"""Shared data models for TestPilot."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class TestType(str, Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    VISUAL = "visual"
    CONTRACT = "contract"
    PERFORMANCE = "performance"


class GapSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GateStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


class TestGap(BaseModel):
    """Represents a detected test gap in source code."""
    file_path: str
    function_name: str
    line_start: int
    line_end: int
    severity: GapSeverity = GapSeverity.MEDIUM
    reason: str = ""
    suggested_test_name: str = ""


class TestCaseSpec(BaseModel):
    """Specification for an AI-generated test case."""
    name: str
    description: str
    test_type: TestType = TestType.UNIT
    requirements: list[str] = Field(default_factory=list)
    setup_steps: list[str] = Field(default_factory=list)
    assertions: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ContractDefinition(BaseModel):
    """Pact-compatible contract definition."""
    consumer: str
    provider: str
    interactions: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PerformanceResult(BaseModel):
    """Result from a performance test run."""
    tool: str  # locust or k6
    total_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    requests_per_second: float = 0.0
    duration_seconds: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class FlakyTestReport(BaseModel):
    """Report for a detected flaky test."""
    test_id: str
    file_path: str
    test_name: str
    total_runs: int = 0
    failures: int = 0
    failure_rate: float = 0.0
    is_quarantined: bool = False
    last_failure_message: str = ""


class QualityGateResult(BaseModel):
    """Overall quality gate result."""
    name: str
    status: GateStatus = GateStatus.SKIP
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    sub_results: list[QualityGateResult] = Field(default_factory=list)


class TestPilotConfig(BaseModel):
    """Top-level configuration for TestPilot."""
    project_name: str = "testpilot"
    root_dir: str = "."
    output_dir: str = "./testpilot-output"
    
    # Quality gate thresholds
    min_coverage_percent: float = 80.0
    max_flaky_rate: float = 0.05
    max_p95_latency_ms: float = 500.0
    max_failure_rate: float = 0.01
    
    # Analysis settings
    analyze_paths: list[str] = Field(default_factory=lambda: ["./src"])
    exclude_patterns: list[str] = Field(
        default_factory=lambda: ["*/tests/*", "*/test/*", "*/__pycache__/*"]
    )
    
    # E2E settings
    browser: str = "chromium"
    headless: bool = True
    base_url: str = "http://localhost:3000"
    
    # Visual regression
    visual_threshold: float = 0.1  # pixel diff threshold
    
    # Performance
    perf_tool: str = "locust"
    perf_users: int = 50
    perf_duration: str = "30s"
    
    # AI settings
    ai_provider: str = "openai"
    ai_model: str = "gpt-4"
    
    # Contract testing
    pact_dir: str = "./pacts"
    provider_base_url: str = "http://localhost:8080"


class SyntheticDataConfig(BaseModel):
    """Configuration for synthetic data generation."""
    locale: str = "en_US"
    seed: int | None = None
    count: int = 10
    schema_file: str | None = None


class PixelDiffResult(BaseModel):
    """Result of a pixel-level image comparison."""
    baseline_path: str = ""
    current_path: str = ""
    diff_path: str = ""
    total_pixels: int = 0
    diff_pixels: int = 0
    diff_percentage: float = 0.0
    is_match: bool = False
    threshold: float = 0.1


class VisualTestResult(BaseModel):
    """Result of a visual regression test."""
    name: str = ""
    passed: bool = False
    diff_result: PixelDiffResult | None = None
    error_message: str = ""
