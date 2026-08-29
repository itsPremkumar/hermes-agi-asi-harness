"""Combined test runner — runs all learning module tests via Python unittest.

Usage:
    python test_all.py
"""

from __future__ import annotations

import os
import sys
import traceback

# Add src/learning to path
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))

from learning.self_eval import ConfidenceTracker, Review, SelfEvaluator
from learning.skill_forge import (
    ForgeLog,
    Skill,
    SkillForge,
    SkillParameter,
    SkillRegistry,
)
from learning.curriculum import (
    CapabilityGap,
    Curriculum,
    CurriculumBuilder,
    PracticeResult,
    PracticeTask,
    make_task_id,
    simple_task_pool,
)
from learning.experience_replay import (
    ExperienceBuffer,
    Mission,
    Replayer,
    Step,
    generate_synthetic_missions,
    make_mission_id,
)

import tempfile

passed = 0
failed = 0
errors = []


def test(name):
    def decorator(fn):
        global passed, failed, errors
        try:
            fn()
            passed += 1
            print(f"  PASS  {name}")
        except Exception as e:
            failed += 1
            errors.append((name, traceback.format_exc()))
            print(f"  FAIL  {name}: {e}")
        return fn
    return decorator


print("=" * 60)
print("  HERMES-ASI-MASTER Phase 7: Learning System Tests")
print("=" * 60)

# =========================================================================
# self_eval
# =========================================================================
print("\n--- self_eval.py ---")


@test("Review: create")
def _():
    r = Review(goal="sort", prediction="sorted", outcome="sorted", success=True, confidence=0.9)
    assert r.goal == "sort"
    assert r.success is True
    assert r.confidence == 0.9


@test("Review: default values")
def _():
    r = Review(goal="g", prediction="p", outcome="o", success=False, confidence=0.1)
    assert r.error == ""
    assert r.correction == ""
    assert r.capability == "general"


@test("Review: to_dict / from_dict")
def _():
    r = Review(goal="g", prediction="p", outcome="o", success=True, confidence=0.8, capability="sort")
    d = r.to_dict()
    r2 = Review.from_dict(d)
    assert r2.goal == "g"
    assert r2.success is True
    assert r2.capability == "sort"


@test("Review: frozen (immutable)")
def _():
    r = Review(goal="g", prediction="p", outcome="o", success=True, confidence=0.5)
    try:
        r.goal = "changed"
        assert False, "Should have raised"
    except AttributeError:
        pass


@test("ConfidenceTracker: default")
def _():
    ct = ConfidenceTracker()
    assert ct.get("sorting") == 0.5


@test("ConfidenceTracker: update increases on success")
def _():
    ct = ConfidenceTracker(alpha=0.5)
    new = ct.update("cap", True)
    assert new > 0.5


@test("ConfidenceTracker: update decreases on failure")
def _():
    ct = ConfidenceTracker(alpha=0.5)
    new = ct.update("cap", False)
    assert new < 0.5


@test("ConfidenceTracker: clamps to [0, 1]")
def _():
    ct = ConfidenceTracker(alpha=1.0)
    ct.update("cap", True)
    assert ct.get("cap") == 1.0
    ct.update("cap", False)
    assert ct.get("cap") == 0.0


@test("ConfidenceTracker: history")
def _():
    ct = ConfidenceTracker(alpha=0.3)
    ct.update("x", True)
    ct.update("x", False)
    ct.update("x", True)
    assert len(ct.history("x")) == 3


@test("ConfidenceTracker: reset")
def _():
    ct = ConfidenceTracker()
    ct.update("x", True)
    ct.reset("x")
    assert ct.get("x") == 0.5


@test("ConfidenceTracker: all")
def _():
    ct = ConfidenceTracker()
    ct.update("a", True)
    ct.update("b", False)
    result = ct.all()
    assert "a" in result
    assert "b" in result


@test("SelfEvaluator: empty")
def _():
    ev = SelfEvaluator()
    assert len(ev) == 0
    report = ev.analyse()
    assert report["count"] == 0


@test("SelfEvaluator: review adds")
def _():
    ev = SelfEvaluator()
    ev.review(goal="g", prediction="p", outcome="o", success=True, capability="x")
    assert len(ev) == 1


@test("SelfEvaluator: analyse count")
def _():
    ev = SelfEvaluator()
    for _ in range(5):
        ev.review(goal="g", prediction="p", outcome="o", success=True, capability="x")
    report = ev.analyse("x")
    assert report["count"] == 5


@test("SelfEvaluator: analyse accuracy")
def _():
    ev = SelfEvaluator()
    for _ in range(3):
        ev.review(goal="g", prediction="p", outcome="o", success=True, capability="x")
    for _ in range(1):
        ev.review(goal="g", prediction="p", outcome="o", success=False, capability="x")
    report = ev.analyse("x")
    assert report["accuracy"] == 0.75


@test("SelfEvaluator: weak_points")
def _():
    ev = SelfEvaluator()
    for _ in range(10):
        ev.review(goal="g", prediction="p", outcome="o", success=True, capability="good")
    for _ in range(10):
        ev.review(goal="g", prediction="p", outcome="o", success=False, capability="bad")
    weak = ev.weak_points(top_k=1)
    assert weak[0][0] == "bad"


@test("SelfEvaluator: forget")
def _():
    ev = SelfEvaluator()
    ev.review(goal="g", prediction="p", outcome="o", success=True, capability="x")
    ev.reviews[0] = Review(
        goal="g", prediction="p", outcome="o", success=True, confidence=0.5, timestamp=1000.0
    )
    removed = ev.forget(before=2000.0)
    assert removed == 1


@test("SelfEvaluator: save/load")
def _():
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


@test("SelfEvaluator: calibration")
def _():
    ev = SelfEvaluator()
    ev.review(goal="g", prediction="p", outcome="o", success=True, confidence=0.9)
    ev.review(goal="g", prediction="p", outcome="o", success=False, confidence=0.1)
    cal = ev.prediction_error_calibration()
    assert cal["bin_count"] == 2


@test("SelfEvaluator: trajectory")
def _():
    ev = SelfEvaluator()
    for _ in range(5):
        ev.review(goal="g", prediction="p", outcome="o", success=True, capability="x")
    traj = ev.improvement_trajectory("x")
    assert len(traj) == 5
    assert traj[-1] >= traj[0]

print(f"\n--- skill_forge.py ---")

# =========================================================================
# skill_forge
# =========================================================================


@test("SkillParameter: create")
def _():
    p = SkillParameter(name="path", description="file path", required=True)
    assert p.name == "path"
    assert p.required is True


@test("SkillParameter: to_dict / from_dict")
def _():
    p = SkillParameter(name="x", default="val")
    d = p.to_dict()
    p2 = SkillParameter.from_dict(d)
    assert p2.name == "x"
    assert p2.default == "val"


@test("Skill: instantiate basic")
def _():
    s = Skill(
        name="write",
        description="write file",
        template="Write {content} to {path}",
        parameters=[SkillParameter(name="content"), SkillParameter(name="path")],
    )
    result = s.instantiate(content="hello", path="/tmp/a")
    assert result == "Write hello to /tmp/a"


@test("Skill: instantiate missing required raises")
def _():
    s = Skill(
        name="write",
        description="d",
        template="Write {content} to {path}",
        parameters=[SkillParameter(name="content", required=True), SkillParameter(name="path")],
    )
    try:
        s.instantiate(content="hello")
        assert False
    except ValueError:
        pass


@test("Skill: instantiate with default")
def _():
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


@test("Skill: hash stable")
def _():
    s1 = Skill(name="a", description="d", template="T {x}")
    s2 = Skill(name="a", description="d", template="T {x}")
    assert s1.hash() == s2.hash()


@test("Skill: hash differs")
def _():
    s1 = Skill(name="a", description="d", template="T {x}")
    s2 = Skill(name="b", description="d", template="T {y}")
    assert s1.hash() != s2.hash()


@test("Skill: to_dict roundtrip")
def _():
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


@test("SkillForge: extract with template")
def _():
    f = SkillForge()
    s = f.extract("my_skill", description="d", template="Action {p1}")
    assert s.template == "Action {p1}"


@test("SkillForge: extract auto template")
def _():
    f = SkillForge()
    trace = [{"action": "read", "path": "/tmp/file"}]
    s = f.extract("auto", source_trace=trace)
    assert "{action}" in s.template


@test("SkillForge: test all pass")
def _():
    f = SkillForge()
    s = Skill(name="echo", description="d", template="echo {msg}",
              parameters=[SkillParameter(name="msg")])
    cases = [{"msg": "hi", "expected": "echo hi"}]
    logs = f.test(s, cases)
    assert all(l.success for l in logs)
    assert s.test_pass_rate == 1.0


@test("SkillForge: test some fail")
def _():
    f = SkillForge()
    s = Skill(name="echo", description="d", template="echo {msg}",
              parameters=[SkillParameter(name="msg")])
    cases = [
        {"msg": "hi", "expected": "echo hi"},
        {"msg": "bye", "expected": "WRONG"},
    ]
    logs = f.test(s, cases)
    assert sum(1 for l in logs if l.success) == 1


@test("SkillForge: review pass")
def _():
    f = SkillForge()
    s = Skill(name="s", description="d", template="T {x}")
    s.test_count = 10
    f.logs = [ForgeLog(skill_name="s", inputs={}, output="", success=True) for _ in range(10)]
    verdict = f.review(s, min_pass_rate=0.8)
    assert verdict["pass"] is True


@test("SkillForge: review fail")
def _():
    f = SkillForge()
    s = Skill(name="s", description="d", template="T {x}")
    s.test_count = 10
    verdict = f.review(s, min_pass_rate=0.8)
    assert verdict["pass"] is False


@test("SkillForge: register success")
def _():
    f = SkillForge()
    s = Skill(name="good", description="d", template="T {x}")
    s.test_count = 5
    f.logs = [ForgeLog(skill_name="good", inputs={}, output="", success=True) for _ in range(5)]
    assert f.register(s, min_pass_rate=0.8) is True


@test("SkillForge: forge pipeline")
def _():
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


@test("SkillRegistry: add and get")
def _():
    r = SkillRegistry()
    s = Skill(name="s", description="d", template="T")
    r.add(s)
    assert r.get("s") is s


@test("SkillRegistry: remove")
def _():
    r = SkillRegistry()
    r.add(Skill(name="s", description="d", template="T"))
    assert r.remove("s") is True


@test("SkillRegistry: list sorted")
def _():
    r = SkillRegistry()
    r.add(Skill(name="low", description="d", template="T", test_pass_rate=0.3))
    r.add(Skill(name="high", description="d", template="T", test_pass_rate=0.9))
    skills = r.list()
    assert skills[0].name == "high"


@test("SkillRegistry: top k")
def _():
    r = SkillRegistry()
    for i in range(10):
        r.add(Skill(name=f"s{i}", description="d", template="T", test_pass_rate=i / 10))
    top = r.top(3)
    assert len(top) == 3


@test("SkillRegistry: stats")
def _():
    r = SkillRegistry()
    r.add(Skill(name="a", description="d", template="T", test_pass_rate=0.5))
    r.add(Skill(name="b", description="d", template="T", test_pass_rate=1.0))
    stats = r.stats()
    assert stats["count"] == 2


@test("SkillRegistry: save/load")
def _():
    r = SkillRegistry()
    r.add(Skill(name="persist", description="d", template="T {x}", test_pass_rate=0.88))
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        r.save(path)
        r2 = SkillRegistry.load(path)
        assert "persist" in r2
    finally:
        os.unlink(path)


# =========================================================================
# curriculum
# =========================================================================
print(f"\n--- curriculum.py ---")


@test("CapabilityGap: gap_size")
def _():
    g = CapabilityGap(capability="x", current_score=0.3, target_score=0.8)
    assert g.gap_size == 0.5


@test("CapabilityGap: gap_size clamped")
def _():
    g = CapabilityGap(capability="x", current_score=0.9, target_score=0.8)
    assert g.gap_size == 0.0


@test("CapabilityGap: priority higher for larger gap")
def _():
    big = CapabilityGap(capability="big", current_score=0.1, target_score=0.9, difficulty=0.5)
    small = CapabilityGap(capability="small", current_score=0.7, target_score=0.9, difficulty=0.5)
    assert big.priority > small.priority


@test("CapabilityGap: to_dict / from_dict")
def _():
    g = CapabilityGap(capability="c", current_score=0.5, target_score=0.8, difficulty=0.3)
    d = g.to_dict()
    g2 = CapabilityGap.from_dict(d)
    assert g2.capability == "c"


@test("PracticeTask: create")
def _():
    t = PracticeTask(id="t1", capability="sort", description="sort", difficulty=0.3, expected_outcome="sorted")
    assert t.id == "t1"
    assert t.max_attempts == 3


@test("PracticeTask: to_dict / from_dict")
def _():
    t = PracticeTask(id="t1", capability="c", description="d", difficulty=0.5)
    d = t.to_dict()
    t2 = PracticeTask.from_dict(d)
    assert t2.id == "t1"


@test("Curriculum: add and remaining")
def _():
    c = Curriculum(id="c1")
    c.add_task(PracticeTask(id="t1", capability="c", description="d", difficulty=0.3))
    c.add_task(PracticeTask(id="t2", capability="c", description="d", difficulty=0.5))
    remaining = c.remaining({"t1"})
    assert len(remaining) == 1


@test("Curriculum: completion rate")
def _():
    c = Curriculum(id="c1")
    for i in range(3):
        c.add_task(PracticeTask(id=f"t{i}", capability="c", description="d", difficulty=0.3))
    assert c.completion_rate({"t0", "t2"}) == 2 / 3


@test("Curriculum: to_dict")
def _():
    c = Curriculum(id="c1")
    c.add_task(PracticeTask(id="t1", capability="c", description="d", difficulty=0.3))
    d = c.to_dict()
    assert d["id"] == "c1"


@test("CurriculumBuilder: discover gaps")
def _():
    b = CurriculumBuilder(target_score=0.8, gap_threshold=0.1)
    scores = {"good": 0.9, "bad": 0.3, "medium": 0.65}
    gaps = b.discover_gaps(scores)
    caps = [g.capability for g in gaps]
    assert "bad" in caps
    assert "good" not in caps


@test("CurriculumBuilder: gaps sorted by priority")
def _():
    b = CurriculumBuilder(target_score=0.8, gap_threshold=0.1)
    scores = {"low": 0.1, "mid": 0.5}
    gaps = b.discover_gaps(scores)
    assert gaps[0].priority >= gaps[-1].priority


@test("CurriculumBuilder: difficulty models")
def _():
    b1 = CurriculumBuilder(difficulty_model="inverse_score")
    assert b1._estimate_difficulty("x", 0.2) > 0.7
    b2 = CurriculumBuilder(difficulty_model="linear", target_score=0.8)
    assert abs(b2._estimate_difficulty("x", 0.3) - 0.5) < 0.01
    b3 = CurriculumBuilder(difficulty_model="constant")
    assert b3._estimate_difficulty("x", 0.5) == 0.5


@test("CurriculumBuilder: build")
def _():
    b = CurriculumBuilder(target_score=0.8, gap_threshold=0.1)
    gaps = [CapabilityGap(capability="sort", current_score=0.3, target_score=0.8, difficulty=0.5)]
    pool = simple_task_pool(["sort", "search"])
    curr = b.build(gaps, pool, max_tasks=3)
    assert len(curr.tasks) > 0


@test("CurriculumBuilder: build_sparse")
def _():
    b = CurriculumBuilder(seed=42)
    gaps = [
        CapabilityGap(capability="a", current_score=0.2, target_score=0.8, difficulty=0.5),
        CapabilityGap(capability="b", current_score=0.3, target_score=0.8, difficulty=0.5),
    ]
    pool = simple_task_pool(["a", "b"])
    curr = b.build_sparse(gaps, pool, max_tasks=4)
    assert len(curr.tasks) > 0


@test("CurriculumBuilder: evaluate")
def _():
    b = CurriculumBuilder()
    curr = Curriculum(id="c1")
    curr.add_task(PracticeTask(id="t1", capability="x", description="d", difficulty=0.3))
    curr.add_task(PracticeTask(id="t2", capability="y", description="d", difficulty=0.5))
    results = [
        PracticeResult(task_id="t1", success=True, score=0.9),
        PracticeResult(task_id="t2", success=False, score=0.3),
    ]
    report = b.evaluate(curr, results)
    assert report["pass_rate"] == 0.5
    assert "x" in report["per_capability"]


@test("make_task_id: deterministic")
def _():
    assert make_task_id("same") == make_task_id("same")


@test("make_task_id: unique")
def _():
    assert make_task_id("first") != make_task_id("second")


@test("simple_task_pool: creates tasks")
def _():
    pool = simple_task_pool(["sort", "search"])
    assert len(pool) >= 8


# =========================================================================
# experience_replay
# =========================================================================
print(f"\n--- experience_replay.py ---")


@test("Step: create")
def _():
    s = Step(observation="see obj", action="move left", reward=0.5)
    assert s.observation == "see obj"
    assert s.action == "move left"


@test("Step: to_dict / from_dict")
def _():
    s = Step(observation="o", action="a", reward=1.0)
    d = s.to_dict()
    s2 = Step.from_dict(d)
    assert s2.reward == 1.0


@test("Mission: add_step and length")
def _():
    m = Mission(id="m1", goal="solve x")
    m.add_step("obs1", "act1", 0.5)
    assert m.length == 1


@test("Mission: total_reward")
def _():
    m = Mission(id="m1", goal="g")
    m.add_step("o1", "a1", 1.0)
    m.add_step("o2", "a2", 0.5)
    m.final_reward = 2.0
    assert m.total_reward == 3.5


@test("Mission: average_reward")
def _():
    m = Mission(id="m1", goal="g")
    m.add_step("o1", "a1", 1.0)
    m.add_step("o2", "a2", 0.5)
    m.final_reward = 0.5
    assert abs(m.average_reward - 2.0 / 3) < 0.001


@test("Mission: to_dict")
def _():
    m = Mission(id="m1", goal="g", capability="sort")
    m.add_step("o", "a", 0.5)
    d = m.to_dict()
    assert d["id"] == "m1"


@test("Mission: from_dict")
def _():
    d = {"id": "m2", "goal": "g", "success": True, "final_reward": 3.0}
    m = Mission.from_dict(d)
    assert m.id == "m2"


@test("ExperienceBuffer: store and len")
def _():
    buf = ExperienceBuffer()
    buf.store(Mission(id="m1", goal="g"))
    assert len(buf) == 1


@test("ExperienceBuffer: extend")
def _():
    buf = ExperienceBuffer()
    buf.extend([Mission(id="m1", goal="g"), Mission(id="m2", goal="g")])
    assert len(buf) == 2


@test("ExperienceBuffer: capacity evicts")
def _():
    buf = ExperienceBuffer(capacity=2)
    for i in range(5):
        buf.store(Mission(id=f"m{i}", goal="g"))
    assert len(buf) == 2


@test("ExperienceBuffer: sample")
def _():
    buf = ExperienceBuffer()
    for i in range(10):
        buf.store(Mission(id=f"m{i}", goal="g"))
    batch = buf.sample(3)
    assert len(batch) == 3


@test("ExperienceBuffer: sample empty")
def _():
    buf = ExperienceBuffer()
    assert buf.sample(5) == []


@test("ExperienceBuffer: sample_steps")
def _():
    buf = ExperienceBuffer()
    m = Mission(id="m1", goal="g")
    for i in range(5):
        m.add_step(f"o{i}", f"a{i}")
    buf.store(m)
    steps = buf.sample_steps(3)
    assert len(steps) == 3


@test("ExperienceBuffer: filter_by capability")
def _():
    buf = ExperienceBuffer()
    buf.store(Mission(id="m1", goal="g", capability="sort"))
    buf.store(Mission(id="m2", goal="g", capability="search"))
    buf.store(Mission(id="m3", goal="g", capability="sort"))
    assert len(buf.filter_by(capability="sort")) == 2


@test("ExperienceBuffer: filter_by success")
def _():
    buf = ExperienceBuffer()
    buf.store(Mission(id="m1", goal="g", success=True))
    buf.store(Mission(id="m2", goal="g", success=False))
    assert len(buf.filter_by(success=True)) == 1


@test("ExperienceBuffer: get")
def _():
    buf = ExperienceBuffer()
    buf.store(Mission(id="m1", goal="g"))
    m = buf.get("m1")
    assert m is not None
    assert m.goal == "g"


@test("ExperienceBuffer: stats")
def _():
    buf = ExperienceBuffer()
    m = Mission(id="m1", goal="g", capability="sort", success=True)
    m.add_step("o", "a", 1.0)
    m.final_reward = 2.0
    buf.store(m)
    stats = buf.stats()
    assert stats["count"] == 1
    assert "sort" in stats["by_capability"]


@test("ExperienceBuffer: reward_distribution")
def _():
    buf = ExperienceBuffer()
    for i in range(10):
        m = Mission(id=f"m{i}", goal="g", final_reward=float(i))
        buf.store(m)
    dist = buf.reward_distribution(bins=5)
    assert sum(dist) == 10


@test("ExperienceBuffer: prune oldest")
def _():
    buf = ExperienceBuffer()
    for i in range(10):
        buf.store(Mission(id=f"m{i}", goal="g"))
    removed = buf.prune(oldest=3)
    assert removed == 7
    assert len(buf) == 3


@test("ExperienceBuffer: prune min_reward")
def _():
    buf = ExperienceBuffer()
    for i in range(5):
        m = Mission(id=f"m{i}", goal="g", final_reward=float(i))
        buf.store(m)
    removed = buf.prune(min_reward=3.0)
    assert removed == 3


@test("ExperienceBuffer: clear")
def _():
    buf = ExperienceBuffer()
    buf.store(Mission(id="m1", goal="g"))
    buf.clear()
    assert len(buf) == 0


@test("ExperienceBuffer: save/load")
def _():
    buf = ExperienceBuffer()
    buf.store(Mission(id="m1", goal="g", capability="sort"))
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        buf.save(path)
        buf2 = ExperienceBuffer.load(path)
        assert len(buf2) == 1
    finally:
        os.unlink(path)


@test("ExperienceBuffer: contains")
def _():
    buf = ExperienceBuffer()
    buf.store(Mission(id="m1", goal="g"))
    assert "m1" in buf
    assert "m2" not in buf


@test("Replayer: replay mission")
def _():
    buf = ExperienceBuffer()
    m = Mission(id="m1", goal="g")
    m.add_step("obs1", "act1")
    m.add_step("obs2", "act2")
    buf.store(m)
    r = Replayer(buf)
    report = r.replay("m1", runner=lambda obs, act: act)
    assert report["total_steps"] == 2
    assert report["accuracy"] == 1.0


@test("Replayer: replay mission not found")
def _():
    buf = ExperienceBuffer()
    r = Replayer(buf)
    report = r.replay("missing", runner=lambda o, a: a)
    assert "error" in report


@test("Replayer: replay_all")
def _():
    buf = ExperienceBuffer()
    for i in range(3):
        m = Mission(id=f"m{i}", goal="g")
        m.add_step("o", "a")
        buf.store(m)
    r = Replayer(buf)
    report = r.replay_all(runner=lambda obs, act: act)
    assert report["missions_replayed"] == 3


@test("Replayer: replay_all by capability")
def _():
    buf = ExperienceBuffer()
    buf.store(Mission(id="m1", goal="g", capability="sort"))
    buf.store(Mission(id="m2", goal="g", capability="search"))
    r = Replayer(buf)
    report = r.replay_all(runner=lambda o, a: a, capability="sort")
    assert report["missions_replayed"] == 1


@test("Replayer: compare_runners")
def _():
    buf = ExperienceBuffer()
    m = Mission(id="m1", goal="g")
    m.add_step("obs", "act")
    buf.store(m)
    r = Replayer(buf)
    result = r.compare_runners("m1", {
        "perfect": lambda o, a: a,
        "wrong": lambda o, a: "different",
    })
    assert result["runner_count"] == 2
    assert result["results"]["perfect"]["accuracy"] == 1.0


@test("Replayer: fuzzy_match")
def _():
    assert Replayer._fuzzy_match("move left", "move left") is True
    assert Replayer._fuzzy_match("completely different", "nothing alike") is False


@test("make_mission_id: deterministic")
def _():
    assert make_mission_id("goal", ts=1000.0) == make_mission_id("goal", ts=1000.0)


@test("make_mission_id: unique")
def _():
    assert make_mission_id("goal_a", ts=1000.0) != make_mission_id("goal_b", ts=1000.0)


@test("generate_synthetic_missions: count")
def _():
    missions = generate_synthetic_missions(5, ["sort", "search"], seed=42)
    assert len(missions) == 5


@test("generate_synthetic_missions: capabilities")
def _():
    missions = generate_synthetic_missions(10, ["sort", "search"], seed=42)
    caps = {m.capability for m in missions}
    assert caps.issubset({"sort", "search"})


@test("generate_synthetic_missions: steps in range")
def _():
    missions = generate_synthetic_missions(10, ["a"], steps_range=(2, 5), seed=42)
    for m in missions:
        assert 2 <= m.length <= 5


# =========================================================================
# Summary
# =========================================================================
print("\n" + "=" * 60)
print(f"  RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
if errors:
    print("\n--- FAILURES ---")
    for name, tb in errors:
        print(f"\n{name}:")
        print(tb)
print("=" * 60)

sys.exit(1 if failed else 0)
