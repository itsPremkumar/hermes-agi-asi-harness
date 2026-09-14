"""Integration hooks for Apache Airflow."""
from __future__ import annotations

from typing import Any

from qualitywatch.engine import run_rule
from qualitywatch.scoring import compute_score
from qualitywatch.models import Rule


def airflow_check(
    task: Any,
    df: Any,
    rules: list[Rule],
    threshold: float = 80.0,
) -> dict[str, Any]:
    """Run quality checks inside an Airflow task.

    Usage::

        from qualitywatch.integrations.airflow import airflow_check
        from qualitywatch.models import Rule

        rules = [Rule(name="no_nulls", rule_type="null_check", column="id")]
        result = airflow_check(task, df, rules, threshold=90.0)
        if result["breached"]:
            task.fail("Quality threshold breached")
    """
    results = []
    for rule in rules:
        if not rule.enabled:
            continue
        result = run_rule(df, rule)
        results.append(result)
        if result.status.value == "fail":
            task.log.warning(f"FAIL {result.rule_name}: {result.message}")
        else:
            task.log.info(f"PASS {result.rule_name}: {result.message}")

    score_info = compute_score(results)
    breached = score_info["score"] < threshold

    return {
        "score": score_info["score"],
        "results": [r.__dict__ for r in results],
        "breached": breached,
        "threshold": threshold,
    }