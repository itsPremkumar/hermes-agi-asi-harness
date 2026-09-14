"""QualityWatch test suite."""
import pandas as pd
import pytest

from qualitywatch.models import Rule, Severity, Status, QualityProfile
from qualitywatch.engine import run_rule
from qualitywatch.profiler import profile
from qualitywatch.scoring import compute_score, TrendTracker
from qualitywatch.alerter import AlertManager


SAMPLE_DF = pd.DataFrame({
    "id": [1, 2, 3, 4, 5],
    "name": ["Alice", "Bob", None, "Diana", "Eve"],
    "age": [25, 30, 35, 40, 45],
    "email": ["a@b.com", "c@d.com", "e@f.com", "g@h.com", "i@j.com"],
})


def test_null_check_pass():
    rule = Rule(name="id_not_null", rule_type="null_check", column="id")
    result = run_rule(SAMPLE_DF, rule)
    assert result.status == Status.PASS
    assert result.rows_affected == 0


def test_null_check_fail():
    rule = Rule(name="name_not_null", rule_type="null_check", column="name")
    result = run_rule(SAMPLE_DF, rule)
    assert result.status == Status.FAIL
    assert result.rows_affected == 1
    assert "null" in result.message.lower()


def test_uniqueness_pass():
    rule = Rule(name="email_unique", rule_type="uniqueness", column="email", params={"threshold": 1.0})
    result = run_rule(SAMPLE_DF, rule)
    assert result.status == Status.PASS


def test_uniqueness_fail():
    df = pd.DataFrame({"id": [1, 1, 2]})
    rule = Rule(name="id_unique", rule_type="uniqueness", column="id", params={"threshold": 1.0})
    result = run_rule(df, rule)
    assert result.status == Status.FAIL


def test_range_pass():
    rule = Rule(name="age_range", rule_type="range", column="age", params={"min": 0, "max": 100})
    result = run_rule(SAMPLE_DF, rule)
    assert result.status == Status.PASS


def test_range_fail():
    rule = Rule(name="age_range", rule_type="range", column="age", params={"min": 30, "max": 40})
    result = run_rule(SAMPLE_DF, rule)
    assert result.status == Status.FAIL
    assert result.rows_affected == 2  # 25 and 45


def test_referential_check_pass():
    ref_df = pd.DataFrame({"id": [1, 2, 3, 4, 5]})
    rule = Rule(name="id_ref", rule_type="referential", column="id", params={"reference_df": ref_df, "reference_column": "id"})
    result = run_rule(SAMPLE_DF, rule)
    assert result.status == Status.PASS


def test_referential_check_fail():
    ref_df = pd.DataFrame({"id": [1, 2, 3]})
    rule = Rule(name="id_ref", rule_type="referential", column="id", params={"reference_df": ref_df})
    result = run_rule(SAMPLE_DF, rule)
    assert result.status == Status.FAIL
    assert result.rows_affected == 2  # ids 4, 5 not in ref


def test_compute_score():
    results = [
        run_rule(SAMPLE_DF, Rule(name="r1", rule_type="null_check", column="id")),
        run_rule(SAMPLE_DF, Rule(name="r2", rule_type="null_check", column="name")),
    ]
    score_info = compute_score(results)
    assert score_info["score"] < 100.0  # one failure
    assert score_info["passed"] == 1
    assert score_info["failed"] == 1


def test_trend_tracker():
    tracker = TrendTracker()
    tracker.add(95.0)
    tracker.add(92.0)
    tracker.add(90.0)
    tracker.add(88.0)
    tracker.add(85.0)
    tracker.add(80.0)
    assert tracker.trend == "declining"
    assert tracker.current == 80.0


def test_alert_manager():
    fired = []
    def callback(rule, alert):
        fired.append(alert)

    mgr = AlertManager(threshold=80.0, on_alert=callback)
    results = [
        run_rule(SAMPLE_DF, Rule(name="r1", rule_type="null_check", column="name")),
    ]
    score_info = compute_score(results)
    mgr.evaluate(score_info["score"], results)
    assert mgr.breached is True
    assert len(fired) == 1


def test_profile():
    prof = profile(SAMPLE_DF, name="test")
    assert prof.row_count == 5
    assert prof.column_count == 4
    assert prof.null_counts["name"] == 1
    assert prof.uniqueness["id"] == 1.0