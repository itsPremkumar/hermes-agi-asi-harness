"""Data models for MCPTest."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Finding severity levels."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TestStatus(str, Enum):
    """Test execution status."""

    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


class TestResult(BaseModel):
    """Single test result."""

    name: str
    status: TestStatus
    duration_ms: float = 0.0
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TestSuite(BaseModel):
    """A suite of test results."""

    name: str
    results: list[TestResult] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.PASS)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.FAIL)

    @property
    def errors(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.ERROR)

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.SKIP)

    @property
    def total(self) -> int:
        return len(self.results)


class ConformanceResult(BaseModel):
    """MCP protocol conformance test result."""

    suite: TestSuite
    mcp_version: str = "2024-11-05"
    server_name: str = ""
    server_version: str = ""
    transport: str = "stdio"


class FuzzResult(BaseModel):
    """Fuzzing engine result."""

    suite: TestSuite
    iterations: int = 0
    crashes: int = 0
    unique_paths: int = 0
    coverage_pct: float = 0.0


class BenchmarkResult(BaseModel):
    """Performance benchmark result."""

    suite: TestSuite
    requests_per_second: float = 0.0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    peak_memory_mb: float = 0.0
    total_requests: int = 0
    failed_requests: int = 0


class SecurityFinding(BaseModel):
    """A single security finding."""

    id: str
    title: str
    severity: Severity
    category: str
    description: str
    remediation: str = ""
    evidence: str = ""
    owasp_category: str = ""


class SecurityScanResult(BaseModel):
    """Security scan result."""

    suite: TestSuite
    findings: list[SecurityFinding] = Field(default_factory=list)
    target_url: str = ""
    scan_duration_ms: float = 0.0

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.HIGH)

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.MEDIUM)

    @property
    def low_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.LOW)


class ComplianceReport(BaseModel):
    """Full compliance report combining all test types."""

    server_name: str
    server_version: str
    mcp_version: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    conformance: Optional[ConformanceResult] = None
    fuzzing: Optional[FuzzResult] = None
    benchmark: Optional[BenchmarkResult] = None
    security: Optional[SecurityScanResult] = None
    overall_score: float = 0.0
    badge_eligible: bool = False
