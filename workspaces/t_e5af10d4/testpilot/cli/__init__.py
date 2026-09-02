"""TestPilot CLI — command-line interface."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click
import structlog

from testpilot import __version__
from testpilot.ai_test_gen import AITestGenerator
from testpilot.contract_testing import ContractVerifier, load_pact_file
from testpilot.flaky_detect import FlakyDetector, parse_pytest_results
from testpilot.models import TestPilotConfig, TestType
from testpilot.perf_integration import PerfIntegration, PerfThreshold
from testpilot.quality_gates import QualityGateRunner
from testpilot.static_analysis import analyze_directory
from testpilot.test_data import SyntheticDataGenerator, SyntheticDataConfig
from testpilot.visual_regression import VisualRegressionRunner

logger = structlog.get_logger()


@click.group()
@click.version_option(version=__version__)
@click.option("--config", "-c", type=click.Path(exists=True), help="Path to config file")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def main(ctx: click.Context, config: str | None, verbose: bool) -> None:
    """TestPilot — AI-Powered Test Generation Platform."""
    ctx.ensure_object(dict)
    if config:
        import yaml
        cfg_data = yaml.safe_load(Path(config).read_text(encoding="utf-8"))
        ctx.obj["config"] = TestPilotConfig(**cfg_data)
    else:
        ctx.obj["config"] = TestPilotConfig()


@main.command()
@click.argument("path", default=".")
@click.option("--exclude", multiple=True, help="Patterns to exclude")
@click.option("--min-severity", default="low", help="Minimum severity to report")
@click.option("--output", "-o", type=click.Path(), help="Output JSON file")
@click.pass_context
def analyze(ctx: click.Context, path: str, exclude: tuple[str, ...], min_severity: str, output: str | None) -> None:
    """Run static analysis to detect test gaps."""
    config: TestPilotConfig = ctx.obj["config"]
    exclude_list = list(exclude) if exclude else config.exclude_patterns

    click.echo(f"Analyzing {path} for test gaps...")
    gaps = analyze_directory(path, exclude_list)

    if min_severity:
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        min_level = severity_order.get(min_severity, 0)
        gaps = [g for g in gaps if severity_order.get(g.severity.value, 0) >= min_level]

    click.echo(f"\nFound {len(gaps)} test gap(s):\n")
    for gap in gaps:
        click.echo(f"  [{gap.severity.value.upper()}] {gap.file_path}:{gap.line_start}")
        click.echo(f"    Function: {gap.function_name}")
        click.echo(f"    Reason: {gap.reason}")
        click.echo(f"    Suggested test: {gap.suggested_test_name}")
        click.echo()

    if output:
        output_data = {
            "total_gaps": len(gaps),
            "gaps": [g.model_dump() for g in gaps],
        }
        Path(output).write_text(json.dumps(output_data, indent=2), encoding="utf-8")
        click.echo(f"Report saved to {output}")


@main.command()
@click.option("--requirement", "-r", required=True, help="Natural language requirement")
@click.option("--type", "test_type", default="unit", type=click.Choice(["unit", "integration", "e2e", "visual", "contract", "performance"]))
@click.option("--output-dir", "-o", default="./tests", help="Output directory")
@click.option("--context", help="Additional context for generation")
def generate(
    requirement: str,
    test_type: str,
    output_dir: str,
    context: str | None,
) -> None:
    """Generate AI test cases from requirements."""
    click.echo(f"Generating {test_type} test for: {requirement}")

    generator = AITestGenerator()
    spec = generator.generate(
        requirement,
        test_type=TestType(test_type),
        context=context,
    )

    click.echo(f"\nTest: {spec.name}")
    click.echo(f"Description: {spec.description}")
    click.echo(f"Type: {spec.test_type.value}")
    click.echo(f"\nSetup steps:")
    for step in spec.setup_steps:
        click.echo(f"  - {step}")
    click.echo(f"\nAssertions:")
    for assertion in spec.assertions:
        click.echo(f"  - {assertion}")

    file_path = generator.generate_to_file(requirement, output_dir, TestType(test_type))
    click.echo(f"\nTest file written to: {file_path}")


@main.command()
@click.option("--browser", default="chromium", help="Browser to use")
@click.option("--headed", is_flag=True, help="Run in headed mode")
@click.option("--base-url", default="http://localhost:3000", help="Base URL")
@click.option("--test-file", type=click.Path(exists=True), help="YAML test definition file")
@click.option("--output-dir", default="./testpilot-output/e2e", help="Output directory")
def e2e(
    browser: str,
    headed: bool,
    base_url: str,
    test_file: str | None,
    output_dir: str,
) -> None:
    """Run Playwright-based E2E tests."""
    from testpilot.e2e_runner import E2ERunner, create_test_from_yaml

    runner = E2ERunner(
        browser=browser,
        headless=not headed,
        base_url=base_url,
        output_dir=output_dir,
    )

    if test_file:
        test = create_test_from_yaml(test_file)
        with runner:
            result = runner.run_test(test)
        click.echo(f"Test '{result.name}': {'PASS' if result.passed else 'FAIL'}")
        if result.error_message:
            click.echo(f"Error: {result.error_message}")
    else:
        click.echo("No test file specified. Use --test-file to provide a YAML test definition.")


@main.command()
@click.option("--baseline", required=True, help="Baseline screenshots directory")
@click.option("--current", required=True, help="Current screenshots directory")
@click.option("--threshold", default=0.1, help="Pixel diff threshold percentage")
@click.option("--output-dir", default="./testpilot-output/visual", help="Output directory")
def visual(
    baseline: str,
    current: str,
    threshold: float,
    output_dir: str,
) -> None:
    """Run visual regression tests."""
    runner = VisualRegressionRunner(
        baseline_dir=baseline,
        current_dir=current,
        output_dir=output_dir,
        threshold=threshold,
    )

    results = runner.run_all()
    report_path = runner.save_report(results)

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    click.echo(f"Visual regression: {passed} passed, {failed} failed")
    for r in results:
        if not r.passed:
            if r.diff_result:
                click.echo(f"  FAIL: {r.name} ({r.diff_result.diff_percentage:.2f}% diff)")
            else:
                click.echo(f"  FAIL: {r.name} - {r.error_message}")

    click.echo(f"Report saved to: {report_path}")


@main.command()
@click.option("--pact-file", type=click.Path(exists=True), help="Pact JSON file")
@click.option("--pact-dir", help="Directory of pact files")
@click.option("--provider-url", required=True, help="Provider base URL")
def contract(
    pact_file: str | None,
    pact_dir: str | None,
    provider_url: str,
) -> None:
    """Run API contract tests."""
    verifier = ContractVerifier(provider_url)

    if pact_file:
        result = verifier.verify_from_file(pact_file)
        results = [result]
    elif pact_dir:
        results = verifier.verify_from_directory(pact_dir)
    else:
        click.echo("Specify --pact-file or --pact-dir")
        return

    for result in results:
        status = "PASS" if result.passed else "FAIL"
        click.echo(f"[{status}] {result.consumer} -> {result.provider}")
        for interaction in result.interactions:
            icon = "PASS" if interaction.passed else "FAIL"
            click.echo(f"  [{icon}] {interaction.description}")
            if not interaction.passed:
                click.echo(f"       Error: {interaction.error_message}")


@main.command()
@click.option("--tool", type=click.Choice(["locust", "k6"]), default="locust")
@click.option("--host", default="http://localhost:8080", help="Target host")
@click.option("--users", default=50, help="Number of concurrent users")
@click.option("--duration", default="30s", help="Test duration")
@click.option("--script", help="Path to test script")
@click.option("--max-p95", default=500.0, help="Max p95 latency (ms)")
@click.option("--max-failure-rate", default=0.01, help="Max failure rate")
def perf(
    tool: str,
    host: str,
    users: int,
    duration: str,
    script: str | None,
    max_p95: float,
    max_failure_rate: float,
) -> None:
    """Run performance tests."""
    integration = PerfIntegration(tool=tool, host=host, script_path=script)

    click.echo(f"Running {tool} performance test: {users} users for {duration}...")
    result = integration.run(users=users, duration=duration)

    click.echo(f"\nResults:")
    click.echo(f"  Total requests: {result.total_requests}")
    click.echo(f"  Failed requests: {result.failed_requests}")
    click.echo(f"  Avg response time: {result.avg_response_time_ms:.1f}ms")
    click.echo(f"  p95 latency: {result.p95_ms:.1f}ms")
    click.echo(f"  RPS: {result.requests_per_second:.1f}")

    thresholds = PerfThreshold(
        max_p95_ms=max_p95,
        max_failure_rate=max_failure_rate,
    )
    gate = integration.check_thresholds(result, thresholds)
    click.echo(f"\nQuality gate: {gate.status.value.upper()}")
    if gate.status.value == "fail":
        click.echo(f"  Reason: {gate.message}")


@main.command()
@click.option("--count", "-n", default=10, help="Number of records to generate")
@click.option("--type", "data_type", type=click.Choice(["users", "products", "orders", "custom"]), default="users")
@click.option("--schema", type=click.Path(exists=True), help="Custom schema file (YAML/JSON)")
@click.option("--output", "-o", help="Output file path")
@click.option("--format", "output_format", type=click.Choice(["json", "csv"]), default="json")
@click.option("--locale", default="en_US", help="Faker locale")
@click.option("--seed", type=int, help="Random seed for reproducibility")
def data(
    count: int,
    data_type: str,
    schema: str | None,
    output: str | None,
    output_format: str,
    locale: str,
    seed: int | None,
) -> None:
    """Generate synthetic test data."""
    config = SyntheticDataConfig(locale=locale, seed=seed, count=count)
    generator = SyntheticDataGenerator(config)

    if data_type == "users":
        data_records = generator.generate_users(count)
    elif data_type == "products":
        data_records = generator.generate_products(count)
    elif data_type == "orders":
        data_records = generator.generate_orders(count)
    elif data_type == "schema":
        if not schema:
            click.echo("--schema required for custom type")
            return
        import yaml
        schema_data = yaml.safe_load(Path(schema).read_text(encoding="utf-8"))
        data_records = generator.generate_from_schema(schema_data, count)
    else:
        click.echo(f"Unknown data type: {data_type}")
        return

    if output:
        if output_format == "csv":
            generator.to_csv(data_records, output)
        else:
            generator.to_json(data_records, output)
        click.echo(f"Generated {len(data_records)} records -> {output}")
    else:
        click.echo(json.dumps(data_records[:3], indent=2, default=str))
        if len(data_records) > 3:
            click.echo(f"... and {len(data_records) - 3} more")


@main.command()
@click.argument("test_paths", nargs=-1, required=True)
@click.option("--reruns", default=3, help="Number of reruns for flaky detection")
@click.option("--max-flaky-rate", default=0.05, help="Maximum acceptable flaky rate")
@click.option("--quarantine-threshold", default=0.15, help="Auto-quarantine threshold")
@click.option("--output-dir", default="./testpilot-output/flaky", help="Output directory")
def flaky(
    test_paths: tuple[str, ...],
    reruns: int,
    max_flaky_rate: float,
    quarantine_threshold: float,
    output_dir: str,
) -> None:
    """Detect and quarantine flaky tests."""
    from testpilot.flaky_detect import run_pytest_and_detect

    click.echo(f"Running tests with {reruns} reruns for flaky detection...")
    results_dir = Path(output_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    # Run pytest with reruns
    import subprocess
    results_file = results_dir / "pytest-results.json"
    cmd = [
        "pytest", *test_paths,
        "--json-report", f"--json-report-file={results_file}",
        f"--reruns={reruns}", "--reruns-delay=1",
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        click.echo("pytest not found or timed out")
        return

    if results_file.exists():
        records = parse_pytest_results(results_file)
        detector = FlakyDetector(
            max_failure_rate=max_flaky_rate,
            quarantine_threshold=quarantine_threshold,
        )
        detector.add_results(records)
        reports = detector.detect()

        if reports:
            click.echo(f"\nFound {len(reports)} potentially flaky test(s):\n")
            for report in reports:
                click.echo(f"  {report.test_name}")
                click.echo(f"    Failure rate: {report.failure_rate:.1%} ({report.failures}/{report.total_runs})")
                if report.last_failure_message:
                    click.echo(f"    Last error: {report.last_failure_message[:100]}")
        else:
            click.echo("\nNo flaky tests detected.")
    else:
        click.echo("No test results found.")


@main.command()
@click.option("--config", "-c", type=click.Path(exists=True), help="Quality gate config file")
@click.option("--min-coverage", default=80.0, help="Minimum coverage percentage")
@click.option("--max-flaky-rate", default=0.05, help="Maximum flaky test rate")
@click.option("--max-p95", default=500.0, help="Maximum p95 latency (ms)")
@click.option("--output", "-o", help="Output report file")
@click.pass_context
def gate(
    ctx: click.Context,
    config: str | None,
    min_coverage: float,
    max_flaky_rate: float,
    max_p95: float,
    output: str | None,
) -> None:
    """Run the full quality gate suite."""
    runner = QualityGateRunner()

    # Coverage gate
    runner.run_coverage_gate(min_percent=min_coverage)

    # Test gap gate
    gaps = analyze_directory(".")
    runner.run_test_gap_gate(gaps)

    # Print and save report
    report = runner.generate_report()
    click.echo(runner.print_summary())

    output_path = output or "./testpilot-output/quality-gate-report.json"
    runner.save_report(output_path)
    click.echo(f"\nReport saved to: {output_path}")

    # Exit with appropriate code
    if runner.overall_status().value == "fail":
        sys.exit(1)


@main.command()
@click.option("--output-dir", default="./testpilot-output", help="Output directory")
def init(output_dir: str) -> None:
    """Initialize a TestPilot project with sample config."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    config_content = """# TestPilot Configuration
project_name: my-project
root_dir: .
output_dir: ./testpilot-output

# Quality gate thresholds
min_coverage_percent: 80.0
max_flaky_rate: 0.05
max_p95_latency_ms: 500.0
max_failure_rate: 0.01

# Analysis settings
analyze_paths:
  - ./src
exclude_patterns:
  - "*/tests/*"
  - "*/test/*"
  - "*/__pycache__/*"

# E2E settings
browser: chromium
headless: true
base_url: http://localhost:3000

# Visual regression
visual_threshold: 0.1

# Performance
perf_tool: locust
perf_users: 50
perf_duration: 30s

# Contract testing
pact_dir: ./pacts
provider_base_url: http://localhost:8080
"""

    config_path = output_path / "testpilot.yaml"
    config_path.write_text(config_content, encoding="utf-8")
    click.echo(f"Initialized TestPilot config: {config_path}")


if __name__ == "__main__":
    main()
