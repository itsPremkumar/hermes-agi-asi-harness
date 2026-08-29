"""Integration tests for MCPTest."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from mcptest.config import Config, ServerTarget, load_config
from mcptest.reports import ReportGenerator
from mcptest.badge import BadgeGenerator
from mcptest.models import (
    ComplianceReport,
    ConformanceResult,
    TestSuite,
    TestResult,
    TestStatus,
    BenchmarkResult,
    FuzzResult,
    SecurityScanResult,
)


@pytest.fixture
def config(tmp_path):
    return Config(
        target=ServerTarget(name="test-server", transport="stdio"),
        output_dir=str(tmp_path / "report"),
    )


@pytest.fixture
def sample_report():
    suite = TestSuite(name="Test Suite")
    suite.results = [
        TestResult(name="test1", status=TestStatus.PASS, duration_ms=10.0),
        TestResult(name="test2", status=TestStatus.PASS, duration_ms=20.0),
        TestResult(name="test3", status=TestStatus.FAIL, duration_ms=5.0),
    ]

    return ComplianceReport(
        server_name="test-server",
        server_version="1.0.0",
        mcp_version="2024-11-05",
        conformance=ConformanceResult(
            suite=suite,
            server_name="test-server",
        ),
        overall_score=85.0,
        badge_eligible=True,
    )


class TestConfig:
    """Tests for configuration management."""

    def test_load_config_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nonexistent.yaml")

    def test_load_config_valid(self, tmp_path):
        import yaml
        cfg_data = {
            "target": {"name": "my-server", "transport": "http", "url": "http://localhost:8000"},
            "output_dir": "custom-report",
        }
        cfg_path = tmp_path / "mcptest.yaml"
        cfg_path.write_text(yaml.dump(cfg_data))

        cfg = load_config(cfg_path)
        assert cfg.target.name == "my-server"
        assert cfg.target.url == "http://localhost:8000"


class TestReports:
    """Tests for report generation."""

    def test_generate_html(self, config, sample_report):
        config.report_formats = ["html"]
        gen = ReportGenerator(config)
        gen.generate(sample_report)

        html_path = Path(config.output_dir) / "report.html"
        assert html_path.exists()
        content = html_path.read_text()
        assert "test-server" in content

    def test_generate_json(self, config, sample_report):
        config.report_formats = ["json"]
        gen = ReportGenerator(config)
        gen.generate(sample_report)

        json_path = Path(config.output_dir) / "report.json"
        assert json_path.exists()
        import json
        data = json.loads(json_path.read_text())
        assert data["server_name"] == "test-server"

    def test_generate_markdown(self, config, sample_report):
        config.report_formats = ["markdown"]
        gen = ReportGenerator(config)
        gen.generate(sample_report)

        md_path = Path(config.output_dir) / "report.md"
        assert md_path.exists()
        content = md_path.read_text()
        assert "test-server" in content

    def test_generate_all_formats(self, config, sample_report):
        config.report_formats = ["html", "json", "markdown"]
        gen = ReportGenerator(config)
        gen.generate(sample_report)

        output = Path(config.output_dir)
        assert (output / "report.html").exists()
        assert (output / "report.json").exists()
        assert (output / "report.md").exists()


class TestBadge:
    """Tests for badge generation."""

    def test_generate_badge(self, config, sample_report):
        gen = BadgeGenerator(config)
        gen.generate(sample_report)

        svg_path = Path(config.output_dir) / "badge.svg"
        assert svg_path.exists()
        content = svg_path.read_text()
        assert "mcptest" in content

    def test_badge_json(self, config, sample_report):
        gen = BadgeGenerator(config)
        gen.generate(sample_report)

        json_path = Path(config.output_dir) / "badge.json"
        assert json_path.exists()
        import json
        data = json.loads(json_path.read_text())
        assert data["label"] == "mcptest"
        assert "85%" in data["message"]
