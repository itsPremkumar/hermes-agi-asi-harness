# QualityWatch — Data Quality Monitoring & Validation System

A comprehensive data quality monitoring system for data pipelines, featuring rule-based validation, automated profiling, quality scoring, trend analysis, and alerting with Airflow and dbt integrations.

## Features

- **Rule Engine** — null checks, uniqueness validation, range checks, referential integrity
- **Data Profiling** — automated statistics per column (null rates, uniqueness, distribution)
- **Quality Scoring** — weighted score (0-100) with severity-aware penalties
- **Trend Analysis** — track quality over time, detect improving/declining/stable
- **Alerting** — threshold-based alerts with callback hooks
- **Dashboard** — Rich terminal UI with tables and score bars
- **Integrations** — Apache Airflow and dbt hooks for pipeline-embedded checks

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Run checks on a CSV with rules file
qualitywatch check -f sample_data.csv -r rules.yaml

# Validate rules file
qualitywatch validate -r rules.yaml

# Version
qualitywatch version
```

## Rule Configuration

Rules are defined in YAML:

```yaml
rules:
  - name: "id_not_null"
    rule_type: null_check
    column: id
    severity: error

  - name: "email_unique"
    rule_type: uniqueness
    column: email
    params:
      threshold: 1.0
    severity: error

  - name: "age_range"
    rule_type: range
    column: age
    params:
      min: 0
      max: 120
    severity: warning

  - name: "order_customer_ref"
    rule_type: referential
    column: customer_id
    params:
      reference_df: customers
      reference_column: id
    severity: error
```

### Rule Types

| Type | Description | Key Params |
|------|-------------|------------|
| `null_check` | Detect nulls in a column | `column` |
| `uniqueness` | Check uniqueness ratio | `column`, `threshold` |
| `range` | Value bounds check | `column`, `min`, `max` |
| `referential` | FK integrity check | `column`, `reference_df`, `reference_column` |
| `custom` | Placeholder for user-defined | — |

## Integration with Airflow

```python
from qualitywatch.integrations.airflow import airflow_check
from qualitywatch.models import Rule

rules = [
    Rule(name="no_nulls", rule_type="null_check", column="id"),
]
result = airflow_check(task, df, rules, threshold=90.0)
if result["breached"]:
    task.fail("Quality threshold breached")
```

## Integration with dbt

```python
from qualitywatch.integrations.dbt import dbt_test
from qualitywatch.models import Rule

rules = [
    Rule(name="unique_id", rule_type="uniqueness", column="id", params={"threshold": 1.0}),
]
result = dbt_test(model, rules, threshold=95.0)
if result["breached"]:
    raise Exception("dbt test failed")
```

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Architecture

```
qualitywatch/
├── models.py        # Domain model (Rule, CheckResult, QualityProfile)
├── engine.py        # Rule execution engines
├── profiler.py      # Automated data profiling
├── scoring.py       # Quality score + trend tracker
├── alerter.py       # Threshold-based alerting
├── dashboard.py     # Rich terminal dashboard
├── cli.py           # Click CLI entry point
├── integrations/
│   ├── airflow.py   # Airflow task hook
│   └── dbt.py       # dbt model hook
└── __init__.py
```