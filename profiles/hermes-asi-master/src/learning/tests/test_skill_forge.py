"""Tests for skill_forge.py."""

from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from learning.skill_forge import (
    ForgeLog,
    Skill,
    SkillForge,
    SkillParameter,
    SkillRegistry,
)


# ---------- SkillParameter ----------


class TestSkillParameter:
    def test_create(self):
        p = SkillParameter(name="path", description="file path", required=True)
        assert p.name == "path"
        assert p.required is True

    def test_to_dict(self):
        p = SkillParameter(name="x", default="val")
        d = p.to_dict()
        assert d["name"] == "x"
        assert d["default"] == "val"

    def test_from_dict(self):
        p = SkillParameter.from_dict({"name": "y", "required": False})
        assert p.name == "y"
        assert p.required is False


# ---------- Skill ----------


class TestSkill:
    def test_instantiate_basic(self):
        s = Skill(
            name="write",
            description="write file",
            template="Write {content} to {path}",
            parameters=[SkillParameter(name="content"), SkillParameter(name="path")],
        )
        result = s.instantiate(content="hello", path="/tmp/a")
        assert result == "Write hello to /tmp/a"

    def test_instantiate_missing_required(self):
        s = Skill(
            name="write",
            description="d",
            template="Write {content} to {path}",
            parameters=[SkillParameter(name="content", required=True), SkillParameter(name="path")],
        )
        with pytest.raises(ValueError):
            s.instantiate(content="hello")

    def test_instantiate_with_default(self):
        s = Skill(
            name="greet",
            description="d",
            template="Hello {name}, welcome to {place}",
            parameters=[
                SkillParameter(name="name", required=True),
                SkillParameter(name="place", default="Earth"),
            ],
        )
        result = s.instantiate(name="Alice")
        assert result == "Hello Alice, welcome to Earth"

    def test_hash_stable(self):
        s1 = Skill(name="a", description="d", template="T {x}")
        s2 = Skill(name="a", description="d", template="T {x}")
        assert s1.hash() == s2.hash()

    def test_hash_differs(self):
        s1 = Skill(name="a", description="d", template="T {x}")
        s2 = Skill(name="b", description="d", template="T {y}")
        assert s1.hash() != s2.hash()

    def test_to_dict_roundtrip(self):
        s = Skill(
            name="test",
            description="desc",
            template="Do {x}",
            parameters=[SkillParameter(name="x")],
            version=3,
            test_pass_rate=0.9,
        )
        d = s.to_dict()
        s2 = Skill.from_dict(d)
        assert s2.name == "test"
        assert s2.version == 3
        assert s2.test_pass_rate == 0.9


# ---------- SkillForge ----------


class TestSkillForge:
    def test_extract_with_template(self):
        f = SkillForge()
        s = f.extract("my_skill", description="d", template="Action {p1}")
        assert s.name == "my_skill"
        assert s.template == "Action {p1}"

    def test_extract_auto_template(self):
        f = SkillForge()
        trace = [{"action": "read", "path": "/tmp/file"}, {"action": "write", "path": "/tmp/out"}]
        s = f.extract("auto", source_trace=trace)
        assert "{action}" in s.template
        assert "{path}" in s.template

    def test_test_all_pass(self):
        f = SkillForge()
        s = Skill(
            name="echo",
            description="d",
            template="echo {msg}",
            parameters=[SkillParameter(name="msg")],
        )
        cases = [
            {"msg": "hello", "expected": "echo hello"},
            {"msg": "world", "expected": "echo world"},
        ]
        logs = f.test(s, cases)
        assert len(logs) == 2
        assert all(l.success for l in logs)
        assert s.test_pass_rate == 1.0

    def test_test_some_fail(self):
        f = SkillForge()
        s = Skill(
            name="echo",
            description="d",
            template="echo {msg}",
            parameters=[SkillParameter(name="msg")],
        )
        cases = [
            {"msg": "hello", "expected": "echo hello"},
            {"msg": "world", "expected": "WRONG"},
        ]
        logs = f.test(s, cases)
        assert sum(1 for l in logs if l.success) == 1
        assert s.test_pass_rate == 0.5

    def test_review_pass(self):
        f = SkillForge()
        s = Skill(name="s", description="d", template="T {x}")
        s.test_pass_rate = 0.9
        s.test_count = 10
        f.logs = [ForgeLog(skill_name="s", inputs={}, output="", success=True) for _ in range(10)]
        verdict = f.review(s, min_pass_rate=0.8)
        assert verdict["pass"] is True

    def test_review_fail(self):
        f = SkillForge()
        s = Skill(name="s", description="d", template="T {x}")
        s.test_pass_rate = 0.3
        s.test_count = 10
        verdict = f.review(s, min_pass_rate=0.8)
        assert verdict["pass"] is False

    def test_register_success(self):
        f = SkillForge()
        s = Skill(name="good", description="d", template="T {x}")
        s.test_pass_rate = 1.0
        s.test_count = 5
        f.logs = [ForgeLog(skill_name="good", inputs={}, output="", success=True) for _ in range(5)]
        assert f.register(s, min_pass_rate=0.8) is True
        assert "good" in f.registry

    def test_register_failure(self):
        f = SkillForge()
        s = Skill(name="bad", description="d", template="T {x}")
        s.test_pass_rate = 0.2
        s.test_count = 5
        assert f.register(s, min_pass_rate=0.8) is False

    def test_forge_pipeline(self):
        f = SkillForge()
        skill, verdict = f.forge_pipeline(
            "full_test",
            description="d",
            template="Run {task}",
            parameters=[SkillParameter(name="task")],
            test_cases=[{"task": "a", "expected": "Run a"}],
            min_pass_rate=0.8,
        )
        assert verdict["registered"] is True
        assert "full_test" in f.registry


# ---------- SkillRegistry ----------


class TestSkillRegistry:
    def test_add_and_get(self):
        r = SkillRegistry()
        s = Skill(name="s", description="d", template="T")
        r.add(s)
        assert r.get("s") is s

    def test_remove(self):
        r = SkillRegistry()
        r.add(Skill(name="s", description="d", template="T"))
        assert r.remove("s") is True
        assert r.get("s") is None

    def test_list_sorted(self):
        r = SkillRegistry()
        r.add(Skill(name="low", description="d", template="T", test_pass_rate=0.3))
        r.add(Skill(name="high", description="d", template="T", test_pass_rate=0.9))
        skills = r.list()
        assert skills[0].name == "high"

    def test_top_k(self):
        r = SkillRegistry()
        for i in range(10):
            r.add(Skill(name=f"s{i}", description="d", template="T", test_pass_rate=i / 10))
        top = r.top(3)
        assert len(top) == 3
        assert top[0].test_pass_rate >= top[1].test_pass_rate

    def test_stats(self):
        r = SkillRegistry()
        r.add(Skill(name="a", description="d", template="T", test_pass_rate=0.5))
        r.add(Skill(name="b", description="d", template="T", test_pass_rate=1.0))
        stats = r.stats()
        assert stats["count"] == 2
        assert stats["avg_pass_rate"] == 0.75

    def test_save_and_load(self):
        r = SkillRegistry()
        r.add(Skill(name="persist", description="d", template="T {x}", test_pass_rate=0.88))
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            r.save(path)
            r2 = SkillRegistry.load(path)
            assert "persist" in r2
            assert r2.get("persist").test_pass_rate == 0.88
        finally:
            os.unlink(path)

    def test_len_and_contains(self):
        r = SkillRegistry()
        r.add(Skill(name="x", description="d", template="T"))
        assert len(r) == 1
        assert "x" in r
        assert "y" not in r


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
