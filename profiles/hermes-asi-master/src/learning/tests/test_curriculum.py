"""Tests for curriculum.py."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from learning.curriculum import (
    CapabilityGap,
    Curriculum,
    CurriculumBuilder,
    PracticeResult,
    PracticeTask,
    make_task_id,
    simple_task_pool,
)


# ---------- CapabilityGap ----------


class TestCapabilityGap:
    def test_gap_size(self):
        g = CapabilityGap(capability="x", current_score=0.3, target_score=0.8)
        assert g.gap_size == 0.5

    def test_gap_size_already_above_target(self):
        g = CapabilityGap(capability="x", current_score=0.9, target_score=0.8)
        assert g.gap_size == 0.0

    def test_priority_higher_for_larger_gap(self):
        big = CapabilityGap(capability="big", current_score=0.1, target_score=0.9, difficulty=0.5)
        small = CapabilityGap(capability="small", current_score=0.7, target_score=0.9, difficulty=0.5)
        assert big.priority > small.priority

    def test_to_dict(self):
        g = CapabilityGap(capability="c", current_score=0.5, target_score=0.8, difficulty=0.3)
        d = g.to_dict()
        assert d["capability"] == "c"

    def test_from_dict(self):
        d = {"capability": "z", "current_score": 0.2, "target_score": 0.9, "difficulty": 0.7}
        g = CapabilityGap.from_dict(d)
        assert g.capability == "z"


# ---------- PracticeTask ----------


class TestPracticeTask:
    def test_create(self):
        t = PracticeTask(
            id="t1",
            capability="sort",
            description="sort a list",
            difficulty=0.3,
            expected_outcome="sorted",
        )
        assert t.id == "t1"
        assert t.max_attempts == 3

    def test_to_dict(self):
        t = PracticeTask(id="t1", capability="c", description="d", difficulty=0.5)
        d = t.to_dict()
        assert d["id"] == "t1"

    def test_from_dict(self):
        d = {"id": "t2", "capability": "c", "description": "d", "difficulty": 0.8}
        t = PracticeTask.from_dict(d)
        assert t.id == "t2"


# ---------- Curriculum ----------


class TestCurriculum:
    def test_add_task(self):
        c = Curriculum(id="c1")
        t = PracticeTask(id="t1", capability="c", description="d", difficulty=0.3)
        c.add_task(t)
        assert len(c.tasks) == 1

    def test_remaining(self):
        c = Curriculum(id="c1")
        c.add_task(PracticeTask(id="t1", capability="c", description="d", difficulty=0.3))
        c.add_task(PracticeTask(id="t2", capability="c", description="d", difficulty=0.5))
        remaining = c.remaining({"t1"})
        assert len(remaining) == 1
        assert remaining[0].id == "t2"

    def test_completion_rate(self):
        c = Curriculum(id="c1")
        c.add_task(PracticeTask(id="t1", capability="c", description="d", difficulty=0.3))
        c.add_task(PracticeTask(id="t2", capability="c", description="d", difficulty=0.5))
        c.add_task(PracticeTask(id="t3", capability="c", description="d", difficulty=0.7))
        assert c.completion_rate({"t1", "t3"}) == 2 / 3

    def test_completion_rate_empty(self):
        c = Curriculum(id="c1")
        assert c.completion_rate(set()) == 1.0

    def test_to_dict(self):
        c = Curriculum(id="c1")
        c.add_task(PracticeTask(id="t1", capability="c", description="d", difficulty=0.3))
        d = c.to_dict()
        assert d["id"] == "c1"
        assert len(d["tasks"]) == 1


# ---------- CurriculumBuilder ----------


class TestCurriculumBuilder:
    def test_discover_gaps(self):
        b = CurriculumBuilder(target_score=0.8, gap_threshold=0.1)
        scores = {"good": 0.9, "bad": 0.3, "medium": 0.65}
        gaps = b.discover_gaps(scores)
        caps = [g.capability for g in gaps]
        assert "bad" in caps
        assert "medium" in caps
        assert "good" not in caps

    def test_discover_gaps_sorted_by_priority(self):
        b = CurriculumBuilder(target_score=0.8, gap_threshold=0.1)
        scores = {"low": 0.1, "mid": 0.5}
        gaps = b.discover_gaps(scores)
        assert gaps[0].priority >= gaps[-1].priority

    def test_estimate_difficulty_inverse_score(self):
        b = CurriculumBuilder(difficulty_model="inverse_score")
        diff = b._estimate_difficulty("x", 0.2)
        assert diff > 0.7  # low score -> high difficulty

    def test_estimate_difficulty_linear(self):
        b = CurriculumBuilder(difficulty_model="linear", target_score=0.8)
        diff = b._estimate_difficulty("x", 0.3)
        assert diff == pytest.approx(0.5)

    def test_build_curriculum(self):
        b = CurriculumBuilder(target_score=0.8, gap_threshold=0.1)
        gaps = [
            CapabilityGap(capability="sort", current_score=0.3, target_score=0.8, difficulty=0.5),
        ]
        pool = simple_task_pool(["sort", "search"])
        curr = b.build(gaps, pool, max_tasks=3)
        assert len(curr.tasks) > 0
        assert all(t.capability == "sort" for t in curr.tasks)

    def test_build_sparse(self):
        b = CurriculumBuilder(seed=42)
        gaps = [
            CapabilityGap(capability="a", current_score=0.2, target_score=0.8, difficulty=0.5),
            CapabilityGap(capability="b", current_score=0.3, target_score=0.8, difficulty=0.5),
        ]
        pool = simple_task_pool(["a", "b"])
        curr = b.build_sparse(gaps, pool, max_tasks=4)
        assert len(curr.tasks) > 0

    def test_evaluate(self):
        b = CurriculumBuilder()
        curr = Curriculum(id="c1")
        curr.add_task(PracticeTask(id="t1", capability="x", description="d", difficulty=0.3))
        curr.add_task(PracticeTask(id="t2", capability="y", description="d", difficulty=0.5))
        results = [
            PracticeResult(task_id="t1", success=True, score=0.9),
            PracticeResult(task_id="t2", success=False, score=0.3),
        ]
        report = b.evaluate(curr, results)
        assert report["completed"] == 2
        assert report["pass_rate"] == 0.5
        assert "x" in report["per_capability"]


# ---------- Helpers ----------


class TestMakeTaskId:
    def test_deterministic(self):
        a = make_task_id("same description")
        b = make_task_id("same description")
        assert a == b

    def test_unique(self):
        a = make_task_id("first")
        b = make_task_id("second")
        assert a != b


class TestSimpleTaskPool:
    def test_creates_tasks(self):
        pool = simple_task_pool(["sort", "search"])
        caps = {t.capability for t in pool}
        assert "sort" in caps
        assert "search" in caps
        assert len(pool) >= 8  # 4 levels * 2 capabilities


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
