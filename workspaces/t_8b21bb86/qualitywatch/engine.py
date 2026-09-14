"""Rule engine — executes rules against pandas DataFrames."""
from __future__ import annotations

import math
from typing import Any

import pandas as pd

from qualitywatch.models import CheckResult, Rule, Status


def _null_check(df: pd.DataFrame, rule: Rule) -> CheckResult:
    col = rule.column
    if col is None or col not in df.columns:
        return CheckResult(
            rule_name=rule.name, rule_type=rule.rule_type,
            status=Status.SKIP, severity=rule.severity,
            message=f"Column '{col}' not found — skipping",
        )
    nulls = df[col].isna().sum()
    if nulls > 0:
        return CheckResult(
            rule_name=rule.name, rule_type=rule.rule_type,
            status=Status.FAIL, severity=rule.severity,
            message=f"Column '{col}' has {nulls} null values",
            rows_affected=int(nulls),
            details={"null_count": nulls, "null_rate": nulls / len(df)},
        )
    return CheckResult(
        rule_name=rule.name, rule_type=rule.rule_type,
        status=Status.PASS, severity=rule.severity,
        message=f"Column '{col}' has no nulls",
        details={"null_count": 0},
    )


def _uniqueness(df: pd.DataFrame, rule: Rule) -> CheckResult:
    col = rule.column
    threshold = rule.params.get("threshold", 1.0)
    if col is None or col not in df.columns:
        return CheckResult(
            rule_name=rule.name, rule_type=rule.rule_type,
            status=Status.SKIP, severity=rule.severity,
            message=f"Column '{col}' not found — skipping",
        )
    n = len(df)
    n_unique = df[col].nunique()
    ratio = n_unique / n if n else 0.0
    if ratio < threshold:
        return CheckResult(
            rule_name=rule.name, rule_type=rule.rule_type,
            status=Status.FAIL, severity=rule.severity,
            message=f"Uniqueness {ratio:.2%} below threshold {threshold:.0%}",
            rows_affected=n - n_unique,
            details={"unique_count": n_unique, "uniqueness_ratio": round(ratio, 4), "threshold": threshold},
        )
    return CheckResult(
        rule_name=rule.name, rule_type=rule.rule_type,
        status=Status.PASS, severity=rule.severity,
        message=f"Uniqueness {ratio:.2%} meets threshold {threshold:.0%}",
        details={"unique_count": n_unique, "uniqueness_ratio": round(ratio, 4)},
    )


def _range_check(df: pd.DataFrame, rule: Rule) -> CheckResult:
    col = rule.column
    min_val = rule.params.get("min")
    max_val = rule.params.get("max")
    if col is None or col not in df.columns:
        return CheckResult(
            rule_name=rule.name, rule_type=rule.rule_type,
            status=Status.SKIP, severity=rule.severity,
            message=f"Column '{col}' not found — skipping",
        )
    series = pd.to_numeric(df[col], errors="coerce")
    total = series.count()
    oob = series[(series < min_val) | (series > max_val)].count() if min_val is not None or max_val is not None else 0
    if oob > 0:
        return CheckResult(
            rule_name=rule.name, rule_type=rule.rule_type,
            status=Status.FAIL, severity=rule.severity,
            message=f"{oob} values outside range [{min_val}, {max_val}]",
            rows_affected=int(oob),
            details={"out_of_range": int(oob), "total": int(total), "min": min_val, "max": max_val},
        )
    return CheckResult(
        rule_name=rule.name, rule_type=rule.rule_type,
        status=Status.PASS, severity=rule.severity,
        message=f"All {total} values in range [{min_val}, {max_val}]",
        details={"out_of_range": 0, "total": int(total)},
    )


def _referential_check(df: pd.DataFrame, rule: Rule) -> CheckResult:
    col = rule.column
    ref_df = rule.params.get("reference_df")
    ref_col = rule.params.get("reference_column", col)
    if col is None or ref_df is None or ref_col not in ref_df.columns:
        return CheckResult(
            rule_name=rule.name, rule_type=rule.rule_type,
            status=Status.SKIP, severity=rule.severity,
            message="Missing reference data — skipping",
        )
    if col not in df.columns:
        return CheckResult(
            rule_name=rule.name, rule_type=rule.rule_type,
            status=Status.SKIP, severity=rule.severity,
            message=f"Column '{col}' not found — skipping",
        )
    orphan = df[~df[col].isin(ref_df[ref_col])]
    if len(orphan) > 0:
        return CheckResult(
            rule_name=rule.name, rule_type=rule.rule_type,
            status=Status.FAIL, severity=rule.severity,
            message=f"{len(orphan)} rows violate referential integrity",
            rows_affected=len(orphan),
            details={"orphan_count": len(orphan), "total": len(df)},
        )
    return CheckResult(
        rule_name=rule.name, rule_type=rule.rule_type,
        status=Status.PASS, severity=rule.severity,
        message="All rows pass referential integrity",
        details={"orphan_count": 0, "total": len(df)},
    )


_ENGINES: dict[str, Any] = {
    "null_check": _null_check,
    "uniqueness": _uniqueness,
    "range": _range_check,
    "referential": _referential_check,
}


def run_rule(df: pd.DataFrame, rule: Rule) -> CheckResult:
    """Execute a single rule against a DataFrame."""
    rule.validate()
    engine = _ENGINES.get(rule.rule_type)
    if engine is None:
        return CheckResult(
            rule_name=rule.name, rule_type=rule.rule_type,
            status=Status.SKIP, severity=rule.severity,
            message=f"No engine for rule type '{rule.rule_type}'",
        )
    return engine(df, rule)