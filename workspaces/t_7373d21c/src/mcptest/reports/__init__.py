"""Report generator for MCPTest (HTML, JSON, Markdown)."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from jinja2 import Template

from mcptest.config import Config
from mcptest.models import ComplianceReport

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCPTest Report - {{ report.server_name }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }
        .container { max-width: 900px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }
        .header h1 { font-size: 2em; margin-bottom: 10px; }
        .header .meta { opacity: 0.9; font-size: 0.9em; }
        .score-card { background: white; border-radius: 10px; padding: 25px; text-align: center; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .score-card .score { font-size: 3em; font-weight: bold; }
        .score-card .label { color: #666; font-size: 0.9em; }
        .score-high { color: #22c55e; }
        .score-medium { color: #f59e0b; }
        .score-low { color: #ef4444; }
        .badge { display: inline-block; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 0.85em; }
        .badge-success { background: #dcfce7; color: #166534; }
        .badge-fail { background: #fee2e2; color: #991b1b; }
        .suite { background: white; border-radius: 10px; margin-bottom: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden; }
        .suite-header { background: #f8fafc; padding: 15px 20px; border-bottom: 1px solid #e2e8f0; font-weight: 600; display: flex; justify-content: space-between; align-items: center; }
        .suite-body { padding: 0; }
        .test-result { padding: 12px 20px; border-bottom: 1px solid #f1f5f9; display: flex; justify-content: space-between; align-items: center; }
        .test-result:last-child { border-bottom: none; }
        .test-name { font-weight: 500; }
        .test-status { padding: 3px 10px; border-radius: 12px; font-size: 0.8em; font-weight: 600; }
        .status-pass { background: #dcfce7; color: #166534; }
        .status-fail { background: #fee2e2; color: #991b1b; }
        .status-error { background: #fef3c7; color: #92400e; }
        .status-skip { background: #e0e7ff; color: #3730a3; }
        .findings { background: white; border-radius: 10px; padding: 20px; margin-bottom: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .finding { padding: 12px; border-left: 4px solid; margin-bottom: 10px; background: #f8fafc; border-radius: 4px; }
        .finding.critical { border-color: #991b1b; }
        .finding.high { border-color: #dc2626; }
        .finding.medium { border-color: #f59e0b; }
        .finding.low { border-color: #3b82f6; }
        .finding .title { font-weight: 600; }
        .finding .meta { font-size: 0.85em; color: #666; }
        .footer { text-align: center; padding: 20px; color: #94a3b8; font-size: 0.85em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>&#128269; MCPTest Report</h1>
            <div class="meta">
                Server: {{ report.server_name }} v{{ report.server_version }}<br>
                MCP Version: {{ report.mcp_version }}<br>
                Generated: {{ report.generated_at.strftime('%Y-%m-%d %H:%M UTC') }}
            </div>
        </div>

        <div class="score-card">
            <div class="score {% if report.overall_score >= 80 %}score-high{% elif report.overall_score >= 50 %}score-medium{% else %}score-low{% endif %}">
                {{ "%.1f"|format(report.overall_score) }}%
            </div>
            <div class="label">Overall Compliance Score</div>
            <br>
            {% if report.badge_eligible %}
            <span class="badge badge-success">&#10003; Badge Eligible</span>
            {% else %}
            <span class="badge badge-fail">&#10007; Not Badge Eligible</span>
            {% endif %}
        </div>

        {% if report.conformance %}
        <div class="suite">
            <div class="suite-header">
                <span>&#128269; Conformance Tests</span>
                <span>{{ report.conformance.suite.passed }}/{{ report.conformance.suite.total }} passed</span>
            </div>
            <div class="suite-body">
                {% for r in report.conformance.suite.results %}
                <div class="test-result">
                    <span class="test-name">{{ r.name }}</span>
                    <span class="test-status status-{{ r.status.value }}">{{ r.status.value|upper }}</span>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        {% if report.fuzzing %}
        <div class="suite">
            <div class="suite-header">
                <span>&#128270; Fuzzing Tests</span>
                <span>{{ report.fuzzing.suite.passed }}/{{ report.fuzzing.suite.total }} passed</span>
            </div>
            <div class="suite-body">
                {% for r in report.fuzzing.suite.results %}
                <div class="test-result">
                    <span class="test-name">{{ r.name }}</span>
                    <span class="test-status status-{{ r.status.value }}">{{ r.status.value|upper }}</span>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        {% if report.benchmark %}
        <div class="suite">
            <div class="suite-header">
                <span>&#9200; Benchmark</span>
                <span>{{ report.benchmark.suite.passed }}/{{ report.benchmark.suite.total }} passed</span>
            </div>
            <div class="suite-body">
                {% for r in report.benchmark.suite.results %}
                <div class="test-result">
                    <span class="test-name">{{ r.name }}</span>
                    <span class="test-status status-{{ r.status.value }}">{{ r.status.value|upper }}</span>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        {% if report.security %}
        <div class="suite">
            <div class="suite-header">
                <span>&#128274; Security Scan</span>
                <span>{{ report.security.suite.passed }}/{{ report.security.suite.total }} passed</span>
            </div>
            <div class="suite-body">
                {% for r in report.security.suite.results %}
                <div class="test-result">
                    <span class="test-name">{{ r.name }}</span>
                    <span class="test-status status-{{ r.status.value }}">{{ r.status.value|upper }}</span>
                </div>
                {% endfor %}
            </div>
        </div>

        {% if report.security and report.security.findings %}
        <div class="findings">
            <h3 style="margin-bottom: 15px;">&#9888; Security Findings</h3>
            {% for f in report.security.findings %}
            <div class="finding {{ f.severity.value }}">
                <div class="title">[{{ f.id }}] {{ f.title }} ({{ f.severity.value|upper }})</div>
                <div class="meta">{{ f.description }}</div>
                <div class="meta" style="margin-top: 5px;"><strong>Remediation:</strong> {{ f.remediation }}</div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        {% endif %}

        <div class="footer">
            Generated by MCPTest v1.0.0
        </div>
    </div>
</body>
</html>"""


class ReportGenerator:
    """Generates test reports in HTML, JSON, and Markdown formats."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.output_dir = Path(config.output_dir)

    def generate(self, report: ComplianceReport) -> None:
        """Generate reports in all configured formats."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if "html" in self.config.report_formats:
            self._generate_html(report)

        if "json" in self.config.report_formats:
            self._generate_json(report)

        if "markdown" in self.config.report_formats:
            self._generate_markdown(report)

    def _generate_html(self, report: ComplianceReport) -> None:
        """Generate HTML report."""
        template = Template(HTML_TEMPLATE)
        html = template.render(report=report)

        path = self.output_dir / "report.html"
        path.write_text(html, encoding="utf-8")
        print(f"HTML report: {path}")

    def _generate_json(self, report: ComplianceReport) -> None:
        """Generate JSON report."""
        path = self.output_dir / "report.json"
        data = self._report_to_dict(report)
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        print(f"JSON report: {path}")

    def _generate_markdown(self, report: ComplianceReport) -> None:
        """Generate Markdown report."""
        lines = [
            f"# MCPTest Report: {report.server_name}",
            "",
            f"**Server Version:** {report.server_version}  ",
            f"**MCP Version:** {report.mcp_version}  ",
            f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}  ",
            f"**Overall Score:** {report.overall_score:.1f}%  ",
            f"**Badge Eligible:** {'Yes' if report.badge_eligible else 'No'}",
            "",
            "---",
            "",
        ]

        if report.conformance:
            lines.extend(self._suite_markdown("Conformance", report.conformance.suite))
        if report.fuzzing:
            lines.extend(self._suite_markdown("Fuzzing", report.fuzzing.suite))
        if report.benchmark:
            lines.extend(self._suite_markdown("Benchmark", report.benchmark.suite))
        if report.security:
            lines.extend(self._suite_markdown("Security", report.security.suite))
            if report.security.findings:
                lines.append("")
                lines.append("## Security Findings")
                lines.append("")
                for f in report.security.findings:
                    lines.append(f"- **[{f.id}]** {f.title} ({f.severity.value})")

        path = self.output_dir / "report.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Markdown report: {path}")

    def _suite_markdown(self, title: str, suite) -> list[str]:
        """Generate markdown for a test suite."""
        lines = [
            f"## {title}",
            "",
            f"| Test | Status | Duration | Message |",
            f"|------|--------|----------|---------|",
        ]
        for r in suite.results:
            lines.append(f"| {r.name} | {r.status.value.upper()} | {r.duration_ms:.1f}ms | {r.message} |")
        lines.append("")
        return lines

    def _report_to_dict(self, report: ComplianceReport) -> dict[str, Any]:
        """Convert report to a JSON-serializable dict."""
        return json.loads(report.model_dump_json())
