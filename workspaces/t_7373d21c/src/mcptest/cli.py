"""CLI entry point for MCPTest."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from mcptest import __version__
from mcptest.config import Config, load_config, load_config_from_env
from mcptest.conformance import ConformanceTester
from mcptest.fuzzing import FuzzingEngine
from mcptest.benchmark import BenchmarkRunner
from mcptest.security import SecurityScanner
from mcptest.reports import ReportGenerator
from mcptest.badge import BadgeGenerator
from mcptest.models import ComplianceReport

console = Console()


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """MCPTest — Automated MCP Server Testing Framework."""


@main.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to mcptest.yaml config file.",
)
@click.option("--target", "-t", help="Target MCP server URL or command.")
@click.option("--transport", type=click.Choice(["stdio", "http", "sse"]), default="stdio")
@click.option("--output", "-o", default="mcptest-report", help="Output directory.")
@click.option("--format", "fmt", multiple=True, type=click.Choice(["html", "json", "markdown"]), default=["html", "json"])
@click.option("--skip-fuzzing", is_flag=True, help="Skip fuzzing tests.")
@click.option("--skip-benchmark", is_flag=True, help="Skip benchmark tests.")
@click.option("--skip-security", is_flag=True, help="Skip security scan.")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output.")
def run(
    config: Optional[str],
    target: Optional[str],
    transport: str,
    output: str,
    fmt: tuple[str, ...],
    skip_fuzzing: bool,
    skip_benchmark: bool,
    skip_security: bool,
    verbose: bool,
) -> None:
    """Run full MCPTest suite against a target server."""
    cfg = _resolve_config(config, target, transport, output, fmt, verbose)

    console.print(f"[bold blue]MCPTest v{__version__}[/bold blue]")
    console.print(f"Target: [cyan]{cfg.target.name}[/cyan] ({cfg.target.transport})")

    report = ComplianceReport(
        server_name=cfg.target.name,
        server_version="",
        mcp_version="2024-11-05",
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Conformance
        task = progress.add_task("Running conformance tests...", total=None)
        conformance = ConformanceTester(cfg)
        report.conformance = asyncio.run(conformance.run())
        progress.update(task, description="Conformance tests complete")

        # Fuzzing
        if not skip_fuzzing:
            task = progress.add_task("Running fuzzing engine...", total=None)
            fuzzing = FuzzingEngine(cfg)
            report.fuzzing = asyncio.run(fuzzing.run())
            progress.update(task, description="Fuzzing complete")

        # Benchmark
        if not skip_benchmark:
            task = progress.add_task("Running benchmarks...", total=None)
            benchmark = BenchmarkRunner(cfg)
            report.benchmark = asyncio.run(benchmark.run())
            progress.update(task, description="Benchmark complete")

        # Security
        if not skip_security:
            task = progress.add_task("Running security scan...", total=None)
            security = SecurityScanner(cfg)
            report.security = asyncio.run(security.run())
            progress.update(task, description="Security scan complete")

    # Calculate overall score
    report.overall_score = _calculate_score(report)
    report.badge_eligible = report.overall_score >= 80.0

    # Generate reports
    reporter = ReportGenerator(cfg)
    reporter.generate(report)

    # Generate badge
    if cfg.compliance_badge_enabled:
        badge = BadgeGenerator(cfg)
        badge.generate(report)

    # Print summary
    _print_summary(report)

    if report.overall_score < cfg.thresholds.min_conformance_pass_rate * 100:
        console.print("[bold red]FAILED: Overall score below threshold[/bold red]")
        sys.exit(1)


@main.command()
@click.option("--config", "-c", type=click.Path(exists=True))
@click.option("--target", "-t")
@click.option("--transport", type=click.Choice(["stdio", "http", "sse"]), default="stdio")
@click.option("--verbose", "-v", is_flag=True)
def conformance(config, target, transport, verbose):
    """Run only conformance tests."""
    cfg = _resolve_config(config, target, transport, "mcptest-report", ("json",), verbose)
    tester = ConformanceTester(cfg)
    result = asyncio.run(tester.run())
    _print_conformance(result)


@main.command()
@click.option("--config", "-c", type=click.Path(exists=True))
@click.option("--target", "-t")
@click.option("--transport", type=click.Choice(["stdio", "http", "sse"]), default="stdio")
@click.option("--iterations", "-n", default=1000, help="Number of fuzzing iterations.")
@click.option("--verbose", "-v", is_flag=True)
def fuzz(config, target, transport, iterations, verbose):
    """Run only fuzzing tests."""
    cfg = _resolve_config(config, target, transport, "mcptest-report", ("json",), verbose)
    cfg.fuzzing_iterations = iterations
    engine = FuzzingEngine(cfg)
    result = asyncio.run(engine.run())
    _print_fuzzing(result)


@main.command()
@click.option("--config", "-c", type=click.Path(exists=True))
@click.option("--target", "-t")
@click.option("--transport", type=click.Choice(["stdio", "http", "sse"]), default="stdio")
@click.option("--duration", "-d", default=30, help="Benchmark duration in seconds.")
@click.option("--concurrency", default=10, help="Concurrent requests.")
@click.option("--verbose", "-v", is_flag=True)
def benchmark(config, target, transport, duration, concurrency, verbose):
    """Run only benchmark tests."""
    cfg = _resolve_config(config, target, transport, "mcptest-report", ("json",), verbose)
    cfg.benchmark_duration_seconds = duration
    cfg.benchmark_concurrency = concurrency
    runner = BenchmarkRunner(cfg)
    result = asyncio.run(runner.run())
    _print_benchmark(result)


@main.command()
@click.option("--config", "-c", type=click.Path(exists=True))
@click.option("--target", "-t")
@click.option("--transport", type=click.Choice(["stdio", "http", "sse"]), default="stdio")
@click.option("--verbose", "-v", is_flag=True)
def security(config, target, transport, verbose):
    """Run only security scan."""
    cfg = _resolve_config(config, target, transport, "mcptest-report", ("json",), verbose)
    scanner = SecurityScanner(cfg)
    result = asyncio.run(scanner.run())
    _print_security(result)


@main.command()
@click.option("--config", "-c", type=click.Path(exists=True), required=True)
def validate(config):
    """Validate a mcptest.yaml config file."""
    try:
        cfg = load_config(config)
        console.print(f"[green]Config valid:[/green] {cfg.target.name}")
    except Exception as e:
        console.print(f"[red]Config invalid:[/red] {e}")
        sys.exit(1)


@main.command()
def init():
    """Create a sample mcptest.yaml config file."""
    sample = """# MCPTest Configuration
target:
  name: my-mcp-server
  command: python
  args: ["-m", "my_mcp_server"]
  transport: stdio
  # url: http://localhost:8000  # for HTTP/SSE transport

thresholds:
  min_requests_per_second: 10.0
  max_avg_latency_ms: 500.0
  max_p99_latency_ms: 2000.0
  max_memory_mb: 512.0
  max_critical_findings: 0
  max_high_findings: 2
  min_conformance_pass_rate: 0.95

output_dir: mcptest-report
report_formats: [html, json]
fuzzing_iterations: 1000
benchmark_duration_seconds: 30
benchmark_concurrency: 10
security_scan_enabled: true
compliance_badge_enabled: true
verbose: false
"""
    path = Path("mcptest.yaml")
    if path.exists():
        console.print("[yellow]mcptest.yaml already exists[/yellow]")
        sys.exit(1)
    path.write_text(sample, encoding="utf-8")
    console.print(f"[green]Created {path}[/green]")


def _resolve_config(
    config: Optional[str],
    target: Optional[str],
    transport: str,
    output: str,
    fmt: tuple[str, ...],
    verbose: bool,
) -> Config:
    """Resolve config from file, CLI args, or env."""
    if config:
        cfg = load_config(config)
    elif target:
        from mcptest.config import ServerTarget
        cfg = Config(
            target=ServerTarget(name=target, url=target, transport=transport),
        )
    else:
        try:
            cfg = load_config_from_env()
        except Exception:
            console.print("[red]No config file or target specified.[/red]")
            console.print("Run `mcptest init` to create a config file.")
            sys.exit(1)

    cfg.output_dir = output
    cfg.report_formats = list(fmt)
    cfg.verbose = verbose
    return cfg


def _calculate_score(report: ComplianceReport) -> float:
    """Calculate overall compliance score (0-100)."""
    scores: list[float] = []

    if report.conformance:
        total = report.conformance.suite.total
        if total > 0:
            scores.append((report.conformance.suite.passed / total) * 100)

    if report.fuzzing:
        total = report.fuzzing.suite.total
        if total > 0:
            scores.append((report.fuzzing.suite.passed / total) * 100)

    if report.benchmark:
        total = report.benchmark.suite.total
        if total > 0:
            scores.append((report.benchmark.suite.passed / total) * 100)

    if report.security:
        total = report.security.suite.total
        if total > 0:
            scores.append((report.security.suite.passed / total) * 100)

    return sum(scores) / len(scores) if scores else 0.0


def _print_summary(report: ComplianceReport) -> None:
    """Print a summary table of all results."""
    table = Table(title="MCPTest Results Summary")
    table.add_column("Suite", style="cyan")
    table.add_column("Passed", style="green", justify="right")
    table.add_column("Failed", style="red", justify="right")
    table.add_column("Errors", style="yellow", justify="right")
    table.add_column("Score", justify="right")

    if report.conformance:
        s = report.conformance.suite
        table.add_row("Conformance", str(s.passed), str(s.failed), str(s.errors), "")
    if report.fuzzing:
        s = report.fuzzing.suite
        table.add_row("Fuzzing", str(s.passed), str(s.failed), str(s.errors), "")
    if report.benchmark:
        s = report.benchmark.suite
        table.add_row("Benchmark", str(s.passed), str(s.failed), str(s.errors), "")
    if report.security:
        s = report.security.suite
        table.add_row("Security", str(s.passed), str(s.failed), str(s.errors), "")

    table.add_row("", "", "", "", f"[bold]{report.overall_score:.1f}%[/bold]")
    console.print(table)

    if report.badge_eligible:
        console.print("[green]Badge eligible![/green]")
    else:
        console.print("[yellow]Not eligible for compliance badge (score < 80%)[/yellow]")


def _print_conformance(result) -> None:
    """Print conformance results."""
    table = Table(title="Conformance Test Results")
    table.add_column("Test", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Duration (ms)", justify="right")
    table.add_column("Message")
    for r in result.suite.results:
        status_style = "green" if r.status.value == "pass" else "red"
        table.add_row(r.name, f"[{status_style}]{r.status.value}[/{status_style}]", f"{r.duration_ms:.1f}", r.message)
    console.print(table)


def _print_fuzzing(result) -> None:
    """Print fuzzing results."""
    console.print(f"Iterations: {result.iterations}")
    console.print(f"Crashes: {result.crashes}")
    console.print(f"Unique paths: {result.unique_paths}")
    console.print(f"Coverage: {result.coverage_pct:.1f}%")


def _print_benchmark(result) -> None:
    """Print benchmark results."""
    table = Table(title="Benchmark Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    table.add_row("Requests/sec", f"{result.requests_per_second:.1f}")
    table.add_row("Avg latency (ms)", f"{result.avg_latency_ms:.2f}")
    table.add_row("P50 latency (ms)", f"{result.p50_latency_ms:.2f}")
    table.add_row("P95 latency (ms)", f"{result.p95_latency_ms:.2f}")
    table.add_row("P99 latency (ms)", f"{result.p99_latency_ms:.2f}")
    table.add_row("Peak memory (MB)", f"{result.peak_memory_mb:.1f}")
    table.add_row("Total requests", str(result.total_requests))
    table.add_row("Failed requests", str(result.failed_requests))
    console.print(table)


def _print_security(result) -> None:
    """Print security results."""
    table = Table(title="Security Scan Results")
    table.add_column("ID", style="cyan")
    table.add_column("Title")
    table.add_column("Severity", justify="center")
    table.add_column("Category")
    for f in result.findings:
        sev_style = {
            "critical": "bold red",
            "high": "red",
            "medium": "yellow",
            "low": "blue",
            "info": "dim",
        }.get(f.severity.value, "")
        table.add_row(f.id, f.title, f"[{sev_style}]{f.severity.value}[/{sev_style}]", f.category)
    console.print(table)
