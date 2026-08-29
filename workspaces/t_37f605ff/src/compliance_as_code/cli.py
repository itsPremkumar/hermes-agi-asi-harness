"""Command-line interface for Compliance-as-Code."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from compliance_as_code.engine import (
    ComplianceEngine,
    ComplianceFramework,
)
from compliance_as_code.policies import get_all_controls
from compliance_as_code.drift import DriftDetector
from compliance_as_code.risk import RiskScoringEngine
from compliance_as_code.remediation import generate_remediation_plan
from compliance_as_code.reports import ReportGenerator
from compliance_as_code.cloud import CloudProvider, get_cloud_integration

console = Console()
logger = logging.getLogger(__name__)


def _build_engine() -> ComplianceEngine:
    """Build a compliance engine with all controls registered."""
    engine = ComplianceEngine()
    for control in get_all_controls():
        engine.register_control(control)
    return engine


def _display_report(report: Any, title: str) -> None:
    """Display a compliance report using rich."""
    console.print(Panel(f"[bold]{title}[/bold]"))
    console.print(f"Report ID: {report.report_id}")
    console.print(f"Compliance Score: [bold]{report.compliance_score}%[/bold]")
    console.print(f"Passed: [green]{report.passed}[/green] | Failed: [red]{report.failed}[/red] | Warnings: [yellow]{report.warnings}[/yellow]")
    console.print("")

    table = Table(title="Control Results")
    table.add_column("Control", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Severity")
    table.add_column("Description")

    for result in report.results:
        status_style = {
            "PASS": "green",
            "FAIL": "red",
            "WARNING": "yellow",
            "ERROR": "red",
            "NOT_APPLICABLE": "dim",
        }.get(result.status.value, "white")

        table.add_row(
            result.control_id,
            f"[{status_style}]{result.status.value}[/{status_style}]",
            result.severity.value,
            result.description[:80],
        )

    console.print(table)


@click.group()
@click.version_option(version="1.0.0")
def main() -> None:
    """Compliance-as-Code: Automated Regulatory Testing Platform."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


@main.command()
@click.option(
    "--framework",
    type=click.Choice(["SOC2", "HIPAA", "GDPR", "PCI-DSS", "all"]),
    default="all",
    help="Compliance framework to evaluate",
)
@click.option(
    "--context",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to context JSON file",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False),
    help="Output file path for JSON report",
)
def evaluate(framework: str, context: str | None, output: str | None) -> None:
    """Run compliance evaluation."""
    engine = _build_engine()

    ctx: dict[str, Any] = {}
    if context:
        ctx = json.loads(Path(context).read_text(encoding="utf-8"))

    if framework == "all":
        reports = engine.evaluate_all(ctx)
        for fw, report in reports.items():
            _display_report(report, f"{fw.value} Compliance Report")
    else:
        fw = ComplianceFramework(framework)
        report = engine.evaluate(fw, ctx)
        _display_report(report, f"{framework} Compliance Report")

    if output:
        # Save last report to file
        report_data = report.to_dict() if hasattr(report, "to_dict") else {
            fw.value: r.to_dict() for fw, r in reports.items()
        }
        Path(output).write_text(json.dumps(report_data, indent=2, default=str), encoding="utf-8")
        console.print(f"\n[green]Report saved to {output}[/green]")


@main.command()
@click.option(
    "--baseline",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to baseline JSON file",
)
@click.option(
    "--current",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to current state JSON file",
)
@click.option(
    "--framework",
    type=click.Choice(["SOC2", "HIPAA", "GDPR", "PCI-DSS"]),
    default="SOC2",
    help="Framework for control mapping",
)
def detect_drift(baseline: str, current: str, framework: str) -> None:
    """Detect compliance drift between baseline and current state."""
    detector = DriftDetector(baseline)
    current_state = json.loads(Path(current).read_text(encoding="utf-8"))

    report = detector.detect_drift(current_state, framework)

    console.print(Panel("[bold]Drift Detection Report[/bold]"))
    console.print(f"Total Drifts: [bold red]{report.total_drifts}[/bold red]")
    console.print(f"Critical: [red]{report.critical}[/red] | High: [yellow]{report.high}[/yellow]")

    if report.events:
        table = Table(title="Drift Events")
        table.add_column("Type", style="cyan")
        table.add_column("Severity", style="bold")
        table.add_column("Control")
        table.add_column("Description")

        for event in report.events:
            sev_style = {
                "CRITICAL": "red bold",
                "HIGH": "red",
                "MEDIUM": "yellow",
                "LOW": "green",
            }.get(event.severity.value, "white")

            table.add_row(
                event.drift_type.value,
                f"[{sev_style}]{event.severity.value}[/{sev_style}]",
                event.control_id,
                event.description[:60],
            )

        console.print(table)
    else:
        console.print("[green]No drift detected — system is compliant[/green]")


@main.command()
@click.option(
    "--framework",
    type=click.Choice(["SOC2", "HIPAA", "GDPR", "PCI-DSS"]),
    default="SOC2",
    help="Framework to score",
)
@click.option(
    "--context",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to context JSON file",
)
def risk_score(framework: str, context: str | None) -> None:
    """Calculate risk score for a framework."""
    engine = _build_engine()
    risk_engine = RiskScoringEngine()

    ctx: dict[str, Any] = {}
    if context:
        ctx = json.loads(Path(context).read_text(encoding="utf-8"))

    fw = ComplianceFramework(framework)
    report = engine.evaluate(fw, ctx)
    risk = risk_engine.calculate_risk(report)

    console.print(Panel(f"[bold]Risk Score: {framework}[/bold]"))
    console.print(f"Overall Score: [bold]{risk.overall_score}/100[/bold]")
    console.print(f"Risk Level: [bold red]{risk.risk_level.value}[/bold red]")

    if risk.recommendations:
        console.print("\n[bold]Recommendations:[/bold]")
        for rec in risk.recommendations:
            console.print(f"  - {rec}")


@main.command()
@click.option(
    "--framework",
    type=click.Choice(["SOC2", "HIPAA", "GDPR", "PCI-DSS"]),
    default="SOC2",
    help="Framework to generate plan for",
)
@click.option(
    "--context",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to context JSON file",
)
def remediate(framework: str, context: str | None) -> None:
    """Generate remediation plan for compliance failures."""
    engine = _build_engine()

    ctx: dict[str, Any] = {}
    if context:
        ctx = json.loads(Path(context).read_text(encoding="utf-8"))

    fw = ComplianceFramework(framework)
    report = engine.evaluate(fw, ctx)
    plan = generate_remediation_plan(report.results)

    console.print(Panel(f"[bold]Remediation Plan: {framework}[/bold]"))
    console.print(f"Plan ID: {plan.plan_id}")
    console.print(f"Total Actions: {plan.total_actions}")
    console.print(f"Automated: {plan.automated_actions}")
    console.print(f"Estimated Effort: {plan.total_effort_hours} hours")

    if plan.actions:
        table = Table(title="Remediation Actions")
        table.add_column("Priority", style="cyan", justify="right")
        table.add_column("Control")
        table.add_column("Title")
        table.add_column("Type")
        table.add_column("Effort (hrs)", justify="right")

        for action in plan.actions:
            table.add_row(
                str(action.priority),
                action.control_id,
                action.title,
                action.remediation_type.value,
                str(action.estimated_effort_hours),
            )

        console.print(table)


@main.command()
@click.option(
    "--provider",
    type=click.Choice(["aws", "azure", "gcp"]),
    required=True,
    help="Cloud provider",
)
@click.option(
    "--region",
    default="us-east-1",
    help="Cloud region (for AWS)",
)
def cloud_compliance(provider: str, region: str) -> None:
    """Check cloud provider compliance."""
    provider_map = {
        "aws": CloudProvider.AWS,
        "azure": CloudProvider.AZURE,
        "gcp": CloudProvider.GCP,
    }

    cloud_provider = provider_map[provider]
    integration = get_cloud_integration(cloud_provider, region=region)
    summary = integration.get_compliance_summary()

    console.print(Panel(f"[bold]Cloud Compliance: {provider.upper()}[/bold]"))
    console.print(f"Provider: {summary['provider']}")
    console.print(f"Total Resources: {summary['total_resources']}")
    console.print(f"Rules Evaluated: {summary['total_rules_evaluated']}")
    console.print(f"Compliant: [green]{summary['compliant']}[/green]")
    console.print(f"Non-Compliant: [red]{summary['non_compliant']}[/red]")
    console.print(f"Compliance: [bold]{summary['compliance_percentage']}%[/bold]")


@main.command()
@click.option(
    "--output",
    type=click.Path(),
    default="audit-report",
    help="Output directory for reports",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "all"]),
    default="all",
    help="Output format",
)
def audit(output: str, fmt: str) -> None:
    """Generate comprehensive audit report."""
    engine = _build_engine()
    report_gen = ReportGenerator()

    # Evaluate all frameworks
    reports = engine.evaluate_all()
    audit_report = report_gen.generate_audit_report(reports)

    formats = ["json", "markdown"] if fmt == "all" else [fmt]
    saved = report_gen.save_report(audit_report, output, formats)

    console.print(Panel("[bold]Audit Report Generated[/bold]"))
    for fmt_name, path in saved.items():
        console.print(f"  {fmt_name}: [cyan]{path}[/cyan]")


if __name__ == "__main__":
    main()
