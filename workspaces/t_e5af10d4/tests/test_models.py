"""Tests for models."""
from testpilot.models import (
    ContractDefinition,
    FlakyTestReport,
    GateStatus,
    GapSeverity,
    PerformanceResult,
    QualityGateResult,
    SyntheticDataConfig,
    TestCaseSpec,
    TestGap,
    TestPilotConfig,
    TestType,
    VisualTestResult,
)


def test_test_gap_creation() -> None:
    """TestGap model should serialize correctly."""
    gap = TestGap(
        file_path="src/app.py",
        function_name="process",
        line_start=10,
        line_end=25,
        severity=GapSeverity.HIGH,
        reason="Complex function",
    )
    assert gap.severity == GapSeverity.HIGH
    assert gap.file_path == "src/app.py"


def test_test_case_spec() -> None:
    """TestCaseSpec should have defaults."""
    spec = TestCaseSpec(name="test_example", description="Example test")
    assert spec.test_type == TestType.UNIT
    assert spec.requirements == []
    assert spec.tags == []


def test_performance_result_defaults() -> None:
    """PerformanceResult should have sensible defaults."""
    result = PerformanceResult(tool="locust")
    assert result.total_requests == 0
    assert result.p95_ms == 0.0


def test_contract_definition() -> None:
    """ContractDefinition should require consumer and provider."""
    contract = ContractDefinition(
        consumer="web-app",
        provider="api-service",
        interactions=[
            {
                "description": "get user",
                "request": {"method": "GET", "path": "/users/1"},
                "response": {"status": 200, "body": {"schema": {"type": "object"}}},
            }
        ],
    )
    assert contract.consumer == "web-app"
    assert len(contract.interactions) == 1


def test_quality_gate_result_sub_results() -> None:
    """QualityGateResult supports nested results."""
    parent = QualityGateResult(
        name="parent",
        status=GateStatus.PASS,
        sub_results=[
            QualityGateResult(name="child", status=GateStatus.PASS),
        ],
    )
    assert len(parent.sub_results) == 1


def test_synthetic_data_config_defaults() -> None:
    """SyntheticDataConfig should have defaults."""
    config = SyntheticDataConfig()
    assert config.locale == "en_US"
    assert config.count == 10


def test_test_pilot_config_defaults() -> None:
    """TestPilotConfig should have reasonable defaults."""
    config = TestPilotConfig()
    assert config.min_coverage_percent == 80.0
    assert config.browser == "chromium"
    assert config.headless is True
