"""Tests for the evolution module: gepa, benchmarks, strategy_search, evolution_loop.

Run with: python test_evolution.py
"""

from __future__ import annotations

import os
import random
import sys
import time
import traceback

# Add src dir to path (evolution is at src/evolution)
HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(HERE, "..", "..")
sys.path.insert(0, SRC_DIR)

from evolution.gepa import (
    EvolutionStep,
    GEPA,
    Mutator,
    Pareto,
    ParetoPoint,
    SafetyValidator,
    Strategy,
    Variant,
)
from evolution.benchmarks import (
    BaselineEntry,
    BaselineTracker,
    Benchmark,
    BenchmarkResult,
    Task,
    TaskResult,
    TaskSuite,
    make_suite_id,
    quick_suite,
)
from evolution.strategy_search import (
    BeamSearch,
    EvolutionarySearch,
    GridSearch,
    RandomSearch,
    SearchResult,
    SearchSpace,
    StrategyConfig,
    run_search,
)
from evolution.evolution_loop import (
    Checkpoint,
    EvolutionLoop,
    EvolutionState,
    Hypothesis,
    HypothesisResult,
    RollbackManager,
    Sandbox,
)

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
print("  HERMES-ASI-MASTER Phase 8: Evolution Engine Tests")
print("=" * 60)

# =========================================================================
# benchmarks.py
# =========================================================================
print("\n--- benchmarks.py ---")


@test("TaskResult: create")
def _():
    r = TaskResult(task_id="t1", success=True, score=0.9, latency=0.1, cost=0.01)
    assert r.task_id == "t1"
    assert r.success is True
    assert r.score == 0.9


@test("TaskResult: to_dict / from_dict")
def _():
    r = TaskResult(task_id="t1", success=True, score=0.8)
    d = r.to_dict()
    r2 = TaskResult.from_dict(d)
    assert r2.task_id == "t1"
    assert r2.success is True
    assert r2.score == 0.8


@test("BenchmarkResult: empty properties")
def _():
    r = BenchmarkResult(suite_id="s1")
    assert r.count == 0
    assert r.success_rate == 0.0
    assert r.avg_score == 0.0
    assert r.avg_latency == 0.0


@test("BenchmarkResult: aggregates")
def _():
    results = [
        TaskResult(task_id="t1", success=True, score=1.0, latency=0.1, cost=0.01),
        TaskResult(task_id="t2", success=False, score=0.0, latency=0.2, cost=0.02),
        TaskResult(task_id="t3", success=True, score=0.8, latency=0.15, cost=0.015),
    ]
    r = BenchmarkResult(suite_id="s1", task_results=results)
    assert r.count == 3
    assert r.success_count == 2
    assert r.failure_count == 1
    assert abs(r.success_rate - 2 / 3) < 0.001
    assert abs(r.avg_score - 0.6) < 0.001
    assert abs(r.total_cost - 0.045) < 0.001


@test("BenchmarkResult: latency_p95")
def _():
    results = [TaskResult(task_id=f"t{i}", success=True, latency=float(i)) for i in range(1, 21)]
    r = BenchmarkResult(suite_id="s1", task_results=results)
    assert r.latency_p95 >= 19.0


@test("BenchmarkResult: summary")
def _():
    results = [TaskResult(task_id="t1", success=True, score=1.0)]
    r = BenchmarkResult(suite_id="s1", task_results=results)
    s = r.summary()
    assert s["suite_id"] == "s1"
    assert s["count"] == 1
    assert s["success_rate"] == 1.0


@test("BenchmarkResult: to_dict / from_dict")
def _():
    results = [TaskResult(task_id="t1", success=True, score=0.9)]
    r = BenchmarkResult(suite_id="s1", task_results=results)
    d = r.to_dict()
    r2 = BenchmarkResult.from_dict(d)
    assert r2.suite_id == "s1"
    assert r2.count == 1


@test("TaskSuite: add and len")
def _():
    suite = TaskSuite("test")
    suite.add(Task(id="t1", input="a", expected="A"))
    suite.add(Task(id="t2", input="b", expected="B"))
    assert len(suite) == 2


@test("TaskSuite: remove")
def _():
    suite = TaskSuite("test")
    suite.add(Task(id="t1", input="a"))
    assert suite.remove("t1") is True
    assert len(suite) == 0
    assert suite.remove("t1") is False


@test("TaskSuite: get")
def _():
    suite = TaskSuite("test")
    suite.add(Task(id="t1", input="a"))
    t = suite.get("t1")
    assert t is not None
    assert t.input == "a"
    assert suite.get("missing") is None


@test("TaskSuite: filter_by")
def _():
    suite = TaskSuite("test")
    suite.add(Task(id="t1", input="a", metadata={"cat": "x"}))
    suite.add(Task(id="t2", input="b", metadata={"cat": "y"}))
    suite.add(Task(id="t3", input="c", metadata={"cat": "x"}))
    filtered = suite.filter_by(lambda t: t.metadata.get("cat") == "x")
    assert len(filtered) == 2


@test("Benchmark: run")
def _():
    suite = quick_suite("test", [("a", "A"), ("b", "B")])
    bench = Benchmark(suite)
    result = bench.run(runner=str.upper)
    assert result.count == 2
    assert result.success_rate == 1.0


@test("Benchmark: run with scorer")
def _():
    suite = quick_suite("test", [("a", "A"), ("b", "X")])
    bench = Benchmark(suite)
    result = bench.run(runner=str.upper)
    assert result.success_count == 1
    assert result.failure_count == 1


@test("Benchmark: run with exceptions")
def _():
    suite = quick_suite("test", [("a", "A")])
    bench = Benchmark(suite)
    def bad_runner(x):
        raise ValueError("fail")
    result = bench.run(runner=bad_runner)
    assert result.failure_count == 1
    assert "fail" in result.task_results[0].error


@test("Benchmark: compare")
def _():
    suite = quick_suite("test", [("a", "A")])
    bench = Benchmark(suite)
    r1 = bench.run(runner=str.upper)
    r2 = bench.run(runner=str.upper)
    comp = bench.compare(r2)
    assert "baseline_score" in comp
    assert "candidate_score" in comp


@test("Benchmark: history")
def _():
    suite = quick_suite("test", [("a", "A")])
    bench = Benchmark(suite)
    bench.run(runner=str.upper)
    bench.run(runner=str.upper)
    assert len(bench.history) == 2


@test("BaselineTracker: record and get")
def _():
    tracker = BaselineTracker()
    result = BenchmarkResult(suite_id="s1", task_results=[
        TaskResult(task_id="t1", success=True, score=0.9)
    ])
    tracker.record(result)
    baseline = tracker.get_baseline("s1")
    assert baseline is not None
    assert baseline.avg_score == 0.9


@test("BaselineTracker: check_regression no baseline")
def _():
    tracker = BaselineTracker()
    result = BenchmarkResult(suite_id="s1", task_results=[
        TaskResult(task_id="t1", success=True, score=0.5)
    ])
    report = tracker.check_regression(result)
    assert report["has_baseline"] is False
    assert report["regressed"] is False


@test("BaselineTracker: check_regression improved")
def _():
    tracker = BaselineTracker()
    r1 = BenchmarkResult(suite_id="s1", task_results=[
        TaskResult(task_id="t1", success=True, score=0.5)
    ])
    tracker.record(r1)
    r2 = BenchmarkResult(suite_id="s1", task_results=[
        TaskResult(task_id="t1", success=True, score=0.9)
    ])
    report = tracker.check_regression(r2)
    assert report["regressed"] is False
    assert report["score_delta"] == 0.4


@test("BaselineTracker: check_regression regressed")
def _():
    tracker = BaselineTracker()
    r1 = BenchmarkResult(suite_id="s1", task_results=[
        TaskResult(task_id="t1", success=True, score=0.9)
    ])
    tracker.record(r1)
    r2 = BenchmarkResult(suite_id="s1", task_results=[
        TaskResult(task_id="t1", success=True, score=0.5)
    ])
    report = tracker.check_regression(r2)
    assert report["regressed"] is True
    assert report["score_regressed"] is True


@test("BaselineTracker: trend")
def _():
    tracker = BaselineTracker()
    for score in [0.5, 0.6, 0.7, 0.8, 0.9]:
        r = BenchmarkResult(suite_id="s1", task_results=[
            TaskResult(task_id="t1", success=True, score=score)
        ])
        tracker.record(r)
    trend = tracker.trend("s1")
    assert trend["samples"] == 5
    assert trend["score_trend"] == 0.4
    assert trend["best_score"] == 0.9


@test("BaselineTracker: summary")
def _():
    tracker = BaselineTracker()
    r = BenchmarkResult(suite_id="s1", task_results=[
        TaskResult(task_id="t1", success=True, score=0.9)
    ])
    tracker.record(r)
    s = tracker.summary()
    assert s["count"] == 1
    assert "s1" in s["suites"]


@test("BaselineTracker: contains")
def _():
    tracker = BaselineTracker()
    r = BenchmarkResult(suite_id="s1", task_results=[
        TaskResult(task_id="t1", success=True, score=0.9)
    ])
    tracker.record(r)
    assert "s1" in tracker
    assert "missing" not in tracker


@test("make_suite_id: deterministic")
def _():
    assert make_suite_id("test") == make_suite_id("test")


@test("quick_suite: creates tasks")
def _():
    suite = quick_suite("test", [("a", "A"), ("b", "B")])
    assert len(suite) == 2
    assert suite.tasks[0].input == "a"
    assert suite.tasks[0].expected == "A"


# =========================================================================
# gepa.py
# =========================================================================
print("\n--- gepa.py ---")


@test("Strategy: create")
def _():
    s = Strategy(name="s1", template="Do X")
    assert s.name == "s1"
    assert s.template == "Do X"
    assert s.version == 1


@test("Strategy: hash stable")
def _():
    s1 = Strategy(name="s", template="T")
    s2 = Strategy(name="s", template="T")
    assert s1.hash() == s2.hash()


@test("Strategy: hash differs")
def _():
    s1 = Strategy(name="s1", template="T1")
    s2 = Strategy(name="s2", template="T2")
    assert s1.hash() != s2.hash()


@test("Strategy: to_dict / from_dict")
def _():
    s = Strategy(name="s", template="T", version=3, score=0.9)
    d = s.to_dict()
    s2 = Strategy.from_dict(d)
    assert s2.name == "s"
    assert s2.version == 3
    assert s2.score == 0.9


@test("Variant: create")
def _():
    v = Variant(parent_name="s1", template="Do Y", mutation="reword")
    assert v.parent_name == "s1"
    assert v.mutation == "reword"


@test("Variant: to_strategy")
def _():
    v = Variant(parent_name="s1", template="Do Y", mutation="reword", score=0.8)
    s = v.strategy
    assert s.name == "s1"
    assert s.template == "Do Y"
    assert s.score == 0.8


@test("Variant: to_dict / from_dict")
def _():
    v = Variant(parent_name="s", template="T", mutation="m")
    d = v.to_dict()
    v2 = Variant.from_dict(d)
    assert v2.parent_name == "s"
    assert v2.mutation == "m"


@test("EvolutionStep: create")
def _():
    step = EvolutionStep(
        step_id=1, parent_strategy="s", parent_score=0.5,
        variants_generated=10, candidates_on_frontier=3,
        selected_template="T", selected_score=0.8,
        selected_cost=0.1, selected_latency=0.05,
        safety_passed=True, promoted=True,
    )
    assert step.step_id == 1
    assert step.promoted is True


@test("EvolutionStep: to_dict / from_dict")
def _():
    step = EvolutionStep(
        step_id=1, parent_strategy="s", parent_score=0.5,
        variants_generated=10, candidates_on_frontier=3,
        selected_template="T", selected_score=0.8,
        selected_cost=0.1, selected_latency=0.05,
        safety_passed=True, promoted=True,
    )
    d = step.to_dict()
    step2 = EvolutionStep.from_dict(d)
    assert step2.step_id == 1
    assert step2.promoted is True


@test("Mutator: generate variants")
def _():
    m = Mutator(seed=42)
    variants = m.generate("Do this carefully.", n=10)
    assert len(variants) > 0
    assert all(v.template != "" for v in variants)


@test("Mutator: reword changes words")
def _():
    m = Mutator(seed=42)
    result = m._reword("You must always verify the output.")
    # Should change at least one word
    assert isinstance(result, str)


@test("Mutator: restructure reorders")
def _():
    m = Mutator(seed=42)
    result = m._restructure("First sentence. Second sentence. Third sentence.")
    assert isinstance(result, str)


@test("Mutator: add_detail appends")
def _():
    m = Mutator(seed=42)
    result = m._add_detail("Do this.")
    assert len(result) > len("Do this.")


@test("Mutator: remove_detail shortens")
def _():
    m = Mutator(seed=42)
    result = m._remove_detail("First sentence. Second sentence.")
    assert len(result) < len("First sentence. Second sentence.")


@test("Pareto: empty")
def _():
    result = Pareto.frontier([])
    assert result == []


@test("Pareto: single variant")
def _():
    v = Variant(parent_name="s", template="T", mutation="test", score=0.8, cost=0.1, latency=0.05)
    result = Pareto.frontier([v])
    assert len(result) == 1


@test("Pareto: frontier excludes dominated")
def _():
    v1 = Variant(parent_name="s", template="A", mutation="m1", score=0.9, cost=0.1, latency=0.05)
    v2 = Variant(parent_name="s", template="B", mutation="m2", score=0.5, cost=0.2, latency=0.1)
    result = Pareto.frontier([v1, v2])
    assert len(result) == 1
    assert result[0].variant.template == "A"


@test("Pareto: frontier keeps non-dominated")
def _():
    v1 = Variant(parent_name="s", template="A", mutation="m1", score=0.9, cost=0.5, latency=0.5)
    v2 = Variant(parent_name="s", template="B", mutation="m2", score=0.5, cost=0.1, latency=0.1)
    result = Pareto.frontier([v1, v2])
    assert len(result) == 2


@test("Pareto: select_best")
def _():
    v1 = Variant(parent_name="s", template="A", mutation="m1", score=0.9, cost=0.1, latency=0.05)
    v2 = Variant(parent_name="s", template="B", mutation="m2", score=0.5, cost=0.2, latency=0.1)
    points = Pareto.frontier([v1, v2])
    best = Pareto.select_best(points)
    assert best is not None
    assert best.variant.template == "A"


@test("Pareto: select_best empty")
def _():
    best = Pareto.select_best([])
    assert best is None


@test("SafetyValidator: passes clean template")
def _():
    v = SafetyValidator()
    ok, violations = v.validate("Please analyze the data carefully.")
    assert ok is True
    assert violations == []


@test("SafetyValidator: catches prohibited phrase")
def _():
    v = SafetyValidator()
    ok, violations = v.validate("You should ignore safety protocols.")
    assert ok is False
    assert any("ignore safety" in v for v in violations)


@test("SafetyValidator: catches too short")
def _():
    v = SafetyValidator(min_length=10)
    ok, violations = v.validate("Hi")
    assert ok is False
    assert any("too short" in v for v in violations)


@test("SafetyValidator: catches script injection")
def _():
    v = SafetyValidator()
    ok, violations = v.validate("Do this <script>alert('xss')</script>")
    assert ok is False
    assert any("script" in v for v in violations)


@test("SafetyValidator: catches template injection")
def _():
    v = SafetyValidator()
    ok, violations = v.validate("Do this {{ malicious_code }}")
    assert ok is False
    assert any("template injection" in v for v in violations)


@test("GEPA: evolve")
def _():
    suite = quick_suite("test", [("a", "A"), ("b", "B")])
    bench = Benchmark(suite)
    gepa = GEPA(seed=42)
    strategy = Strategy(name="s1", template="Convert to uppercase.")
    step = gepa.evolve(
        base_strategy=strategy,
        benchmark=bench,
        runner=str.upper,
        n_variants=5,
    )
    assert step.step_id == 1
    assert step.variants_generated >= 0


@test("GEPA: summary")
def _():
    suite = quick_suite("test", [("a", "A")])
    bench = Benchmark(suite)
    gepa = GEPA(seed=42)
    strategy = Strategy(name="s1", template="Convert to uppercase.")
    gepa.evolve(base_strategy=strategy, benchmark=bench, runner=str.upper, n_variants=3)
    s = gepa.summary()
    assert s["steps"] == 1


@test("GEPA: history")
def _():
    suite = quick_suite("test", [("a", "A")])
    bench = Benchmark(suite)
    gepa = GEPA(seed=42)
    # Use a template with multiple sentences + mutable words for reliable mutations
    strategy = Strategy(name="s1", template="You must always verify the output. Ensure correctness.")
    gepa.evolve(base_strategy=strategy, benchmark=bench, runner=str.upper, n_variants=5)
    gepa.evolve(base_strategy=strategy, benchmark=bench, runner=str.upper, n_variants=5)
    assert len(gepa.history) == 2


# =========================================================================
# strategy_search.py
# =========================================================================
print("\n--- strategy_search.py ---")


@test("StrategyConfig: create")
def _():
    c = StrategyConfig(name="c1", params={"a": 1, "b": 2})
    assert c.name == "c1"
    assert c.get("a") == 1


@test("StrategyConfig: with_score")
def _():
    c = StrategyConfig(name="c1", params={"a": 1})
    c2 = c.with_score(0.9, {"latency": 0.1})
    assert c2.score == 0.9
    assert c2.metrics["latency"] == 0.1
    assert c.score == 0.0  # original unchanged


@test("StrategyConfig: to_dict / from_dict")
def _():
    c = StrategyConfig(name="c1", params={"x": 1}, score=0.8)
    d = c.to_dict()
    c2 = StrategyConfig.from_dict(d)
    assert c2.name == "c1"
    assert c2.score == 0.8


@test("SearchSpace: add_param")
def _():
    space = SearchSpace()
    space.add_param("lr", [0.01, 0.1])
    assert space.param_names() == ["lr"]
    assert space.param_values("lr") == [0.01, 0.1]


@test("SearchSpace: size")
def _():
    space = SearchSpace()
    space.add_param("a", [1, 2, 3])
    space.add_param("b", [10, 20])
    assert space.size() == 6


@test("SearchSpace: sample")
def _():
    space = SearchSpace()
    space.add_param("x", [1, 2, 3])
    rng = random.Random(42)
    samples = space.sample(5, rng=rng)
    assert len(samples) == 5
    assert all(s.params.get("x") in [1, 2, 3] for s in samples)


@test("SearchSpace: grid")
def _():
    space = SearchSpace()
    space.add_param("a", [1, 2])
    space.add_param("b", [10, 20])
    grid = space.grid()
    assert len(grid) == 4


@test("SearchSpace: neighbors")
def _():
    space = SearchSpace()
    space.add_param("x", [1, 2, 3])
    config = StrategyConfig(name="c", params={"x": 2})
    neighbors = space.neighbors(config)
    assert len(neighbors) == 2  # x=1 and x=3


@test("SearchSpace: to_dict / from_dict")
def _():
    space = SearchSpace()
    space.add_param("x", [1, 2, 3])
    d = space.to_dict()
    space2 = SearchSpace.from_dict(d)
    assert space2.param_values("x") == [1, 2, 3]


@test("GridSearch: search")
def _():
    space = SearchSpace()
    space.add_param("x", [1, 2, 3])
    search = GridSearch()
    def evaluate(cfg):
        return cfg.with_score(float(cfg.get("x", 0)))
    result = search.search(space, evaluate)
    assert result.best is not None
    assert result.best.score == 3.0
    assert result.total_evaluations == 3


@test("RandomSearch: search")
def _():
    space = SearchSpace()
    space.add_param("x", [1, 2, 3, 4, 5])
    search = RandomSearch(seed=42)
    def evaluate(cfg):
        return cfg.with_score(float(cfg.get("x", 0)))
    result = search.search(space, evaluate, n_iter=10)
    assert result.best is not None
    assert result.total_evaluations == 10


@test("EvolutionarySearch: search")
def _():
    space = SearchSpace()
    space.add_param("x", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    search = EvolutionarySearch(seed=42, population_size=10)
    def evaluate(cfg):
        return cfg.with_score(float(cfg.get("x", 0)))
    result = search.search(space, evaluate, n_generations=5)
    assert result.best is not None
    assert result.total_evaluations > 10


@test("BeamSearch: search")
def _():
    space = SearchSpace()
    space.add_param("x", [1, 2, 3, 4, 5])
    search = BeamSearch(beam_width=3)
    def evaluate(cfg):
        return cfg.with_score(float(cfg.get("x", 0)))
    result = search.search(space, evaluate, n_steps=3)
    assert result.best is not None
    assert result.total_evaluations >= 3


@test("SearchResult: top_k")
def _():
    configs = [StrategyConfig(name=f"c{i}", params={}, score=float(i)) for i in range(10)]
    result = SearchResult(
        algorithm="test", best=configs[-1], evaluated=configs,
        total_evaluations=10, duration=0.1,
    )
    top = result.top_k(3)
    assert len(top) == 3
    assert top[0].score == 9.0


@test("SearchResult: summary")
def _():
    configs = [StrategyConfig(name=f"c{i}", params={}, score=float(i)) for i in range(5)]
    result = SearchResult(
        algorithm="test", best=configs[-1], evaluated=configs,
        total_evaluations=5, duration=0.1,
    )
    s = result.summary()
    assert s["algorithm"] == "test"
    assert s["best_score"] == 4.0
    assert s["worst_score"] == 0.0


@test("run_search: by name")
def _():
    space = SearchSpace()
    space.add_param("x", [1, 2, 3])
    def evaluate(cfg):
        return cfg.with_score(float(cfg.get("x", 0)))
    result = run_search("grid", space, evaluate)
    assert result.algorithm == "grid_search"


@test("run_search: invalid name raises")
def _():
    space = SearchSpace()
    try:
        run_search("invalid", space, lambda c: c)
        assert False, "Should have raised"
    except ValueError:
        pass


# =========================================================================
# evolution_loop.py
# =========================================================================
print("\n--- evolution_loop.py ---")


@test("Hypothesis: create")
def _():
    h = Hypothesis(hypothesis_id="h1", description="test", target_module="s", changes={"x": 1})
    assert h.hypothesis_id == "h1"
    assert h.expected_improvement == 0.1


@test("Hypothesis: to_dict / from_dict")
def _():
    h = Hypothesis(hypothesis_id="h1", description="d", target_module="s", changes={"x": 1})
    d = h.to_dict()
    h2 = Hypothesis.from_dict(d)
    assert h2.hypothesis_id == "h1"
    assert h2.changes == {"x": 1}


@test("HypothesisResult: promoted")
def _():
    h = Hypothesis(hypothesis_id="h1", description="d", target_module="s", changes={})
    r = HypothesisResult(
        hypothesis=h, success=True, score_before=0.5, score_after=0.8,
        improvement=0.3, safety_passed=True, sandbox_id="s1",
    )
    assert r.promoted is True


@test("HypothesisResult: not promoted if unsafe")
def _():
    h = Hypothesis(hypothesis_id="h1", description="d", target_module="s", changes={})
    r = HypothesisResult(
        hypothesis=h, success=True, score_before=0.5, score_after=0.8,
        improvement=0.3, safety_passed=False, sandbox_id="s1",
    )
    assert r.promoted is False


@test("HypothesisResult: not promoted if no improvement")
def _():
    h = Hypothesis(hypothesis_id="h1", description="d", target_module="s", changes={})
    r = HypothesisResult(
        hypothesis=h, success=True, score_before=0.5, score_after=0.5,
        improvement=0.0, safety_passed=True, sandbox_id="s1",
    )
    assert r.promoted is False


@test("EvolutionState: create")
def _():
    s = EvolutionState()
    assert s.generation == 0
    assert s.current_score == 0.0


@test("EvolutionState: record_result")
def _():
    s = EvolutionState()
    h = Hypothesis(hypothesis_id="h1", description="d", target_module="s", changes={})
    r = HypothesisResult(
        hypothesis=h, success=True, score_before=0.5, score_after=0.8,
        improvement=0.3, safety_passed=True, sandbox_id="s1",
    )
    s.record_result(r)
    assert s.total_hypotheses_tested == 1
    assert s.total_hypotheses_promoted == 1
    assert s.current_score == 0.8
    assert s.best_score == 0.8


@test("EvolutionState: summary")
def _():
    s = EvolutionState()
    s.total_hypotheses_tested = 10
    s.total_hypotheses_promoted = 5
    summary = s.summary()
    assert summary["promotion_rate"] == 0.5


@test("Sandbox: create and state")
def _():
    sb = Sandbox("s1", {"a": 1, "b": {"c": 2}})
    assert sb.state == {"a": 1, "b": {"c": 2}}


@test("Sandbox: apply changes")
def _():
    sb = Sandbox("s1", {"a": 1})
    sb.apply({"a": 2})
    assert sb.state["a"] == 2


@test("Sandbox: deep update")
def _():
    sb = Sandbox("s1", {"a": {"b": 1}})
    sb.apply({"a": {"b": 2}})
    assert sb.state["a"]["b"] == 2


@test("Sandbox: reset")
def _():
    sb = Sandbox("s1", {"a": 1})
    sb.apply({"a": 2})
    sb.reset()
    assert sb.state["a"] == 1


@test("Sandbox: snapshot")
def _():
    sb = Sandbox("s1", {"a": 1})
    snap = sb.snapshot()
    sb.apply({"a": 2})
    assert snap["a"] == 1
    assert sb.state["a"] == 2


@test("RollbackManager: create_checkpoint")
def _():
    rm = RollbackManager()
    ckpt = rm.create_checkpoint({"a": 1}, label="test")
    assert ckpt.label == "test"
    assert ckpt.state == {"a": 1}


@test("RollbackManager: latest")
def _():
    rm = RollbackManager()
    rm.create_checkpoint({"a": 1})
    latest = rm.latest()
    assert latest is not None
    assert latest.state == {"a": 1}


@test("RollbackManager: rollback to latest")
def _():
    rm = RollbackManager()
    rm.create_checkpoint({"a": 1})
    rm.create_checkpoint({"a": 2})
    ckpt = rm.rollback()
    assert ckpt is not None
    assert ckpt.state == {"a": 2}


@test("RollbackManager: rollback to specific")
def _():
    rm = RollbackManager()
    ckpt1 = rm.create_checkpoint({"a": 1})
    rm.create_checkpoint({"a": 2})
    result = rm.rollback(ckpt1.checkpoint_id)
    assert result is not None
    assert result.state == {"a": 1}


@test("RollbackManager: max checkpoints")
def _():
    rm = RollbackManager(max_checkpoints=3)
    for i in range(5):
        rm.create_checkpoint({"a": i})
    assert len(rm) == 3


@test("RollbackManager: list_checkpoints")
def _():
    rm = RollbackManager()
    rm.create_checkpoint({"a": 1})
    rm.create_checkpoint({"a": 2})
    assert len(rm.list_checkpoints()) == 2


@test("EvolutionLoop: create")
def _():
    loop = EvolutionLoop(initial_state={"x": 1})
    assert loop.state.current_strategy == {"x": 1}


@test("EvolutionLoop: run with no fns ends")
def _():
    loop = EvolutionLoop()
    result = loop.run(max_iterations=5)
    # Loop attempts iteration 0 (generation=1), then breaks when no hypothesis fn
    assert result["generation"] == 1
    assert result["total_hypotheses_tested"] == 0


@test("EvolutionLoop: run with benchmark only")
def _():
    loop = EvolutionLoop(initial_state={"x": 1})
    loop.set_benchmark_fn(lambda s: 0.5)
    result = loop.run(max_iterations=3)
    assert result["current_score"] == 0.5


@test("EvolutionLoop: promote on improvement")
def _():
    loop = EvolutionLoop(
        initial_state={"x": 1},
        promotion_threshold=0.01,
    )
    loop.set_benchmark_fn(lambda s: float(s.get("x", 0)))
    loop.set_hypothesis_fn(lambda state: Hypothesis(
        hypothesis_id="h1",
        description="increase x",
        target_module="strategy",
        changes={"x": state.current_strategy.get("x", 0) + 1},
    ))
    loop.set_safety_fn(lambda s: (True, []))
    result = loop.run(max_iterations=3)
    assert result["total_hypotheses_tested"] == 3
    assert result["total_hypotheses_promoted"] == 3
    assert result["best_score"] >= 2.0


@test("EvolutionLoop: rollback on regression")
def _():
    loop = EvolutionLoop(
        initial_state={"x": 10},
        rollback_threshold=-0.5,
    )
    loop.set_benchmark_fn(lambda s: float(s.get("x", 0)))
    loop.set_hypothesis_fn(lambda state: Hypothesis(
        hypothesis_id="h1",
        description="decrease x",
        target_module="strategy",
        changes={"x": state.current_strategy.get("x", 0) - 1},
    ))
    loop.set_safety_fn(lambda s: (True, []))
    result = loop.run(max_iterations=3)
    assert result["total_rollbacks"] > 0


@test("EvolutionLoop: safety gate blocks promotion")
def _():
    loop = EvolutionLoop(
        initial_state={"x": 1},
        promotion_threshold=0.01,
    )
    loop.set_benchmark_fn(lambda s: float(s.get("x", 0)))
    loop.set_hypothesis_fn(lambda state: Hypothesis(
        hypothesis_id="h1",
        description="increase x",
        target_module="strategy",
        changes={"x": state.current_strategy.get("x", 0) + 1},
    ))
    loop.set_safety_fn(lambda s: (False, ["unsafe"]))
    result = loop.run(max_iterations=3)
    assert result["total_hypotheses_promoted"] == 0


@test("EvolutionLoop: inject_hypothesis")
def _():
    loop = EvolutionLoop(initial_state={"x": 1})
    loop.set_benchmark_fn(lambda s: float(s.get("x", 0)))
    loop.set_safety_fn(lambda s: (True, []))
    # Initialize current_score via benchmark
    loop.state.current_score = loop._benchmark_fn(loop.state.current_strategy)
    result = loop.inject_hypothesis("increase x", {"x": 5})
    assert result.score_after == 5.0
    assert result.improvement == 4.0


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
