"""Integration hooks for dbt."""
from __future__ import annotations

from typing import Any

from qualitywatch.engine import run_rule
from qualitywatch.scoring import compute_score
from qualitywatch.models import Rule


def dbt_test(
    dbt_model: Any,
    rules: list[Rule],
    threshold: float = 80.0,
) -> dict[str, Any]:
    """Run quality checks as dbt tests.

    Usage::

        from qualitywatch.integrations.dbt import dbt_test
        from qualitywatch.models import Rule

        rules = [Rule(name="unique_id", rule_type="uniqueness", column="id", params={"threshold": 1.0})]
        result = dbt_test(model, rules, threshold=95.0)
        if result["breached"]:
            raise Exception("dbt test failed: quality threshold breached")
    """
    df = dbt_model.df if hasattr(dbt_model, "df") else None
    if df is None:
        raise ValueError("dbt model must have a 'df' attribute")

    results = []
    for rule in rules:
        if not rule.enabled:
            continue
        result = run_rule(df, rule)
        results.append(result)

    score_info = compute_score(results)
    breached = score_info["score"] < threshold

    return {
        "score": score_info["score"],
        "results": [r.__dict__ for r in results],
        "breached": breached,
        "threshold": threshold,
    }