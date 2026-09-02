"""Tests for self_eval.py."""

from __future__ import annotations

import json
import math
import os
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from learning.self_eval import ConfidenceTracker, Review, SelfEvaluator


# ---------- Review ----------


class TestReview:
    def test_create_review(self):
        r = Review(goal="sort", prediction="sorted", outcome="sorted", success=True, confidence=0.9)
        assert r.goal == "sort"
        assert r.success is True
        assert r.confidence == 0.9

    def test_review_default_values(self):
        r = Review(goal="g", prediction="p", outcome="o", success=False, confidence=0.1)
        assert r.error == ""
        assert r.correction == ""
        assert r.capability == "general"
        assert isinstance(r.timestamp, float)
        assert r.metadata == {}

    def test_review_to_dict(self):
        r = Review(goal="g", prediction="p", outcome="o", success=True, confidence=0.8, capability="sort")
        d = r.to_dict()
        assert d["goal"] == "g"
        assert d["success"] is True
        assert d["capability"] == "sort"

    def test_review_from_dict(self):
        d = {"goal": "g", "prediction": "p", "outcome": "o", "success": True, "confidence": 0.7}
        r = Review.from_dict(d)
        assert r.goal == "g"
        assert r.success is True

    def test_review_frozen(self):
        r = Review(goal="g", prediction="p", outcome="o", success=True, confidence=0.5)
        with pytest.raises(AttributeError):
            r.goal = "changed"


# ---------- ConfidenceTracker ----------


class TestConfidenceTracker:
    def test_default_confidence(self):
        ct = ConfidenceTracker()
        assert ct.get("sorting") == 0.5

    def test_update_increases_on_success(self):
        ct = ConfidenceTracker(alpha=0.5)
        new = ct.update("cap", True)
        assert new > 0.5

    def test_update_decreases_on_failure(self):
        ct = ConfidenceTracker(alpha=0.5)
        new = ct.update("cap", False)
        assert new < 0.5

    def test_update_clamps_to_range(self):
        ct = ConfidenceTracker(alpha=1.0)
        ct.update("cap", True)
        assert ct.get("cap") == 1.0
        ct.update("cap", False)
        assert ct.get("cap") == 0.0

    def test_history_tracks_values(self):
        ct = ConfidenceTracker(alpha=0.3)
        ct.update("x", True)
        ct.update("x", False)
        ct.update("x", True)
        assert len(ct.history("x")) == 3

    def test_reset(self):
        ct = ConfidenceTracker()
        ct.update("x", True)
        ct.reset("x")
        assert ct.get("x") == 0.5
        assert ct.history("x") == []

    def test_all_returns_dict(self):
        ct = ConfidenceTracker()
        ct.update("a", True)
        ct.update("b", False)
        result = ct.all()
        assert "a" in result
        assert "b" in result


# ---------- SelfEvaluator ----------


class TestSelfEvaluator:
    def test_empty_evaluator(self):
        ev = SelfEvaluator()
        assert len(ev) == 0
        report = ev.analyse()
        assert report["count"] == 0

    def test_review_adds_to_list(self):
        ev = SelfEvaluator()
        ev.review(goal="g", prediction="p", outcome="o", success=True, capability="x")
        assert len(ev) == 1

    def test_review_returns_review(self):
        ev = SelfEvaluator()
        r = ev.review(goal="g", prediction="p", outcome="o", success=True, capability="x")
        assert isinstance(r, Review)

    def test_analyse_count(self):
        ev = SelfEvaluator()
        for _ in range(5):
            ev.review(goal="g", prediction="p", outcome="o", success=True, capability="x")
        report = ev.analyse("x")
        assert report["count"] == 5

    def test_analyse_accuracy(self):
        ev = SelfEvaluator()
        for _ in range(3):
            ev.review(goal="g", prediction="p", outcome="o", success=True, capability="x")
        for _ in range(1):
            ev.review(goal="g", prediction="p", outcome="o", success=False, capability="x")
        report = ev.analyse("x")
        assert report["accuracy"] == 0.75

    def test_analyse_confidence(self):
        ev = SelfEvaluator()
        ev.review(goal="g", prediction="p", outcome="o", success=True, capability="x")
        report = ev.analyse("x")
        assert "confidence" in report

    def test_weak_points(self):
        ev = SelfEvaluator()
        for _ in range(10):
            ev.review(goal="g", prediction="p", outcome="o", success=True, capability="good")
        for _ in range(10):
            ev.review(goal="g", prediction="p", outcome="o", success=False, capability="bad")
        weak = ev.weak_points(top_k=1)
        assert len(weak) == 1
        assert weak[0][0] == "bad"

    def test_forget_removes_old(self):
        ev = SelfEvaluator()
        ev.review(goal="g", prediction="p", outcome="o", success=True, capability="x")
        ev.reviews[0] = Review(
            goal="g", prediction="p", outcome="o", success=True, confidence=0.5, timestamp=1000.0
        )
        removed = ev.forget(before=2000.0)
        assert removed == 1
        assert len(ev) == 0

    def test_save_and_load(self):
        ev = SelfEvaluator()
        ev.review(goal="g", prediction="p", outcome="o", success=True, capability="x")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            ev.save(path)
            ev2 = SelfEvaluator.load(path)
            assert len(ev2) == 1
            assert ev2.reviews[0].goal == "g"
        finally:
            os.unlink(path)

    def test_prediction_error_calibration(self):
        ev = SelfEvaluator()
        ev.review(goal="g", prediction="p", outcome="o", success=True, confidence=0.9)
        ev.review(goal="g", prediction="p", outcome="o", success=False, confidence=0.1)
        cal = ev.prediction_error_calibration()
        assert "mae" in cal
        assert cal["bin_count"] == 2

    def test_improvement_trajectory(self):
        ev = SelfEvaluator()
        for _ in range(5):
            ev.review(goal="g", prediction="p", outcome="o", success=True, capability="x")
        traj = ev.improvement_trajectory("x")
        assert len(traj) == 5
        assert traj[-1] >= traj[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
