"""MCPTest — Automated MCP Server Testing Framework.

A comprehensive testing toolkit for MCP servers: conformance, fuzzing,
benchmarking, security scanning, and compliance reporting.
"""

__version__ = "1.0.0"
__author__ = "Prem Kumar"
__license__ = "MIT"

from mcptest.config import Config, load_config
from mcptest.models import (
    TestResult,
    TestSuite,
    ConformanceResult,
    FuzzResult,
    BenchmarkResult,
    SecurityFinding,
    ComplianceReport,
)

__all__ = [
    "__version__",
    "Config",
    "load_config",
    "TestResult",
    "TestSuite",
    "ConformanceResult",
    "FuzzResult",
    "BenchmarkResult",
    "SecurityFinding",
    "ComplianceReport",
]
