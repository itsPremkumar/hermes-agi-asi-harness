"""CLI entry point."""
from __future__ import annotations

import click
import yaml

from qualitywatch.engine import run_rule
from qualitywatch.profiler import profile
from qualitywatch.scoring import TrendTracker, compute_score
from qualitywatch.alerter import AlertManager
from qualitywatch.dashboard import Dashboard
from qualitywatch.models import Rule, Status


@click.group()
def main() -> None:
    """QualityWatch — Data Quality Monitoring & Validation System."""


@main.command()
@click.option("--file", "-f", required=True, type=click.Path(exists=True), help="CSV file to validate")
@click.option("--rules", "-r", required=True, type=click.Path(exists=True), help="YAML rules file")
@click.option("--threshold", "-t", default=80.0, show_default=True, help="Quality score threshold")
def check(file: str, rules: str, threshold: float) -> None:
    """Run quality checks on a CSV file."""
    import pandas as pd
    from rich.console import Console

    console = Console()
    console.print(f"[bold]Loading data:[/bold] {file}")
    df = pd.read_csv(file)

    with open(rules) as f:
        rule_configs = yaml.safe_load(f)

    rules_list = [Rule(**rc) for rc in rule_configs.get("rules", [])]
    results = []

    for rule in rules_list:
        if not rule.enabled:
            continue
        result = run_rule(df, rule)
        results.append(result)
        status_color = "green" if result.status == Status.PASS else "red" if result.status == Status.FAIL else "yellow"
        console.print(f"  [{status_color}]{result.status.value}[/{status_color}] {result.rule_name}: {result.message}")

    score_info = compute_score(results)
    console.print()
    dashboard = Dashboard()
    dashboard.render_score(score_info)

    alert_mgr = AlertManager(threshold=threshold)
    alert_mgr.evaluate(score_info["score"], results)
    if alert_mgr.breached:
        console.print(f"\n[bold red]ALERT: Quality score {score_info['score']} below threshold {threshold}[/bold red]")

    # Profile
    console.print("\n[bold]Data Profile:[/bold]")
    prof = profile(df)
    dashboard.render_profile(prof)


@main.command()
@click.option("--rules", "-r", required=True, type=click.Path(exists=True), help="YAML rules file")
def validate(rules: str) -> None:
    """Validate a rules YAML file."""
    from qualitywatch.models import Rule

    with open(rules) as f:
        config = yaml.safe_load(f)

    for rc in config.get("rules", []):
        try:
            rule = Rule(**rc)
            rule.validate()
            click.echo(f"  OK: {rule.name} ({rule.rule_type})")
        except Exception as e:
            click.echo(f"  FAIL: {rc.get('name', '?')} — {e}", err=True)


@main.command()
def version() -> None:
    """Print version."""
    from importlib.metadata import version, PackageNotFoundError
    try:
        click.echo(f"QualityWatch {version('qualitywatch')}")
    except PackageNotFoundError:
        click.echo("QualityWatch (dev)")


if __name__ == "__main__":
    main()