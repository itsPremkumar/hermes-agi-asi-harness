"""Tests for experience_replay.py."""

from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from learning.experience_replay import (
    ExperienceBuffer,
    Mission,
    Replayer,
    Step,
    generate_synthetic_missions,
    make_mission_id,
)


# ---------- Step ----------


class TestStep:
    def test_create(self):
        s = Step(observation="see obj", action="move left", reward=0.5)
        assert s.observation == "see obj"
        assert s.action == "move left"
        assert s.reward == 0.5

    def test_to_dict(self):
        s = Step(observation="o", action="a", reward=1.0)
        d = s.to_dict()
        assert d["observation"] == "o"
        assert d["reward"] == 1.0

    def test_from_dict(self):
        d = {"observation": "o", "action": "a", "reward": -0.5}
        s = Step.from_dict(d)
        assert s.reward == -0.5


# ---------- Mission ----------


class TestMission:
    def test_add_step(self):
        m = Mission(id="m1", goal="solve x")
        m.add_step("obs1", "act1", 0.5)
        assert m.length == 1
        assert m.steps[0].action == "act1"

    def test_total_reward(self):
        m = Mission(id="m1", goal="g")
        m.add_step("o1", "a1", 1.0)
        m.add_step("o2", "a2", 0.5)
        m.final_reward = 2.0
        assert m.total_reward == 3.5

    def test_average_reward(self):
        m = Mission(id="m1", goal="g")
        m.add_step("o1", "a1", 1.0)
        m.add_step("o2", "a2", 0.5)
        m.final_reward = 0.5
        assert m.average_reward == pytest.approx(2.0 / 3)

    def test_average_reward_empty(self):
        m = Mission(id="m1", goal="g")
        assert m.average_reward == 0.0

    def test_to_dict(self):
        m = Mission(id="m1", goal="g", capability="sort")
        m.add_step("o", "a", 0.5)
        d = m.to_dict()
        assert d["id"] == "m1"
        assert d["capability"] == "sort"
        assert len(d["steps"]) == 1

    def test_from_dict(self):
        d = {"id": "m2", "goal": "g", "success": True, "final_reward": 3.0}
        m = Mission.from_dict(d)
        assert m.id == "m2"
        assert m.success is True


# ---------- ExperienceBuffer ----------


class TestExperienceBuffer:
    def test_store_and_len(self):
        buf = ExperienceBuffer()
        buf.store(Mission(id="m1", goal="g"))
        assert len(buf) == 1

    def test_extend(self):
        buf = ExperienceBuffer()
        buf.extend([Mission(id="m1", goal="g"), Mission(id="m2", goal="g")])
        assert len(buf) == 2

    def test_capacity_evicts(self):
        buf = ExperienceBuffer(capacity=2)
        for i in range(5):
            buf.store(Mission(id=f"m{i}", goal="g"))
        assert len(buf) == 2

    def test_sample(self):
        buf = ExperienceBuffer()
        for i in range(10):
            buf.store(Mission(id=f"m{i}", goal="g"))
        batch = buf.sample(3)
        assert len(batch) == 3

    def test_sample_empty(self):
        buf = ExperienceBuffer()
        assert buf.sample(5) == []

    def test_sample_steps(self):
        buf = ExperienceBuffer()
        m = Mission(id="m1", goal="g")
        for i in range(5):
            m.add_step(f"o{i}", f"a{i}")
        buf.store(m)
        steps = buf.sample_steps(3)
        assert len(steps) == 3

    def test_filter_by_capability(self):
        buf = ExperienceBuffer()
        buf.store(Mission(id="m1", goal="g", capability="sort"))
        buf.store(Mission(id="m2", goal="g", capability="search"))
        buf.store(Mission(id="m3", goal="g", capability="sort"))
        result = buf.filter_by(capability="sort")
        assert len(result) == 2

    def test_filter_by_success(self):
        buf = ExperienceBuffer()
        buf.store(Mission(id="m1", goal="g", success=True))
        buf.store(Mission(id="m2", goal="g", success=False))
        result = buf.filter_by(success=True)
        assert len(result) == 1

    def test_get(self):
        buf = ExperienceBuffer()
        buf.store(Mission(id="m1", goal="g"))
        m = buf.get("m1")
        assert m is not None
        assert m.goal == "g"

    def test_stats(self):
        buf = ExperienceBuffer()
        m = Mission(id="m1", goal="g", capability="sort", success=True)
        m.add_step("o", "a", 1.0)
        m.final_reward = 2.0
        buf.store(m)
        stats = buf.stats()
        assert stats["count"] == 1
        assert stats["success_rate"] == 1.0
        assert "sort" in stats["by_capability"]

    def test_reward_distribution(self):
        buf = ExperienceBuffer()
        for i in range(10):
            m = Mission(id=f"m{i}", goal="g", final_reward=float(i))
            buf.store(m)
        dist = buf.reward_distribution(bins=5)
        assert sum(dist) == 10

    def test_prune_oldest(self):
        buf = ExperienceBuffer()
        for i in range(10):
            buf.store(Mission(id=f"m{i}", goal="g"))
        removed = buf.prune(oldest=3)
        assert removed == 7
        assert len(buf) == 3

    def test_prune_min_reward(self):
        buf = ExperienceBuffer()
        for i in range(5):
            m = Mission(id=f"m{i}", goal="g", final_reward=float(i))
            buf.store(m)
        removed = buf.prune(min_reward=3.0)
        assert removed == 3

    def test_clear(self):
        buf = ExperienceBuffer()
        buf.store(Mission(id="m1", goal="g"))
        buf.clear()
        assert len(buf) == 0

    def test_save_and_load(self):
        buf = ExperienceBuffer()
        buf.store(Mission(id="m1", goal="g", capability="sort"))
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            buf.save(path)
            buf2 = ExperienceBuffer.load(path)
            assert len(buf2) == 1
            assert buf2.get("m1").goal == "g"
        finally:
            os.unlink(path)

    def test_contains(self):
        buf = ExperienceBuffer()
        buf.store(Mission(id="m1", goal="g"))
        assert "m1" in buf
        assert "m2" not in buf


# ---------- Replayer ----------


class TestReplayer:
    def test_replay_mission(self):
        buf = ExperienceBuffer()
        m = Mission(id="m1", goal="g")
        m.add_step("obs1", "act1")
        m.add_step("obs2", "act2")
        buf.store(m)
        r = Replayer(buf)
        report = r.replay("m1", runner=lambda obs, act: act)
        assert report["total_steps"] == 2
        assert report["accuracy"] == 1.0

    def test_replay_mission_not_found(self):
        buf = ExperienceBuffer()
        r = Replayer(buf)
        report = r.replay("missing", runner=lambda o, a: a)
        assert "error" in report

    def test_replay_all(self):
        buf = ExperienceBuffer()
        for i in range(3):
            m = Mission(id=f"m{i}", goal="g")
            m.add_step("o", "a")
            buf.store(m)
        r = Replayer(buf)
        report = r.replay_all(runner=lambda obs, act: act)
        assert report["missions_replayed"] == 3
        assert report["avg_accuracy"] == 1.0

    def test_replay_all_by_capability(self):
        buf = ExperienceBuffer()
        buf.store(Mission(id="m1", goal="g", capability="sort"))
        buf.store(Mission(id="m2", goal="g", capability="search"))
        r = Replayer(buf)
        report = r.replay_all(runner=lambda o, a: a, capability="sort")
        assert report["missions_replayed"] == 1

    def test_compare_runners(self):
        buf = ExperienceBuffer()
        m = Mission(id="m1", goal="g")
        m.add_step("obs", "act")
        buf.store(m)
        r = Replayer(buf)
        result = r.compare_runners(
            "m1",
            runners={
                "perfect": lambda o, a: a,
                "wrong": lambda o, a: "different",
            },
        )
        assert result["runner_count"] == 2
        assert result["results"]["perfect"]["accuracy"] == 1.0
        assert result["results"]["wrong"]["accuracy"] == 0.0

    def test_fuzzy_match(self):
        assert Replayer._fuzzy_match("move left", "move left") is True
        assert Replayer._fuzzy_match("completely different", "nothing alike") is False


# ---------- Helpers ----------


class TestMakeMissionId:
    def test_deterministic_with_ts(self):
        a = make_mission_id("goal", ts=1000.0)
        b = make_mission_id("goal", ts=1000.0)
        assert a == b

    def test_unique_per_goal(self):
        a = make_mission_id("goal_a", ts=1000.0)
        b = make_mission_id("goal_b", ts=1000.0)
        assert a != b


class TestGenerateSyntheticMissions:
    def test_count(self):
        missions = generate_synthetic_missions(5, ["sort", "search"], seed=42)
        assert len(missions) == 5

    def test_capabilities(self):
        missions = generate_synthetic_missions(10, ["sort", "search"], seed=42)
        caps = {m.capability for m in missions}
        assert caps.issubset({"sort", "search"})

    def test_steps_in_range(self):
        missions = generate_synthetic_missions(10, ["a"], steps_range=(2, 5), seed=42)
        for m in missions:
            assert 2 <= m.length <= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
