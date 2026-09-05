"""Tests for adapters.py — Benchmark Adapters."""
import json
import os
import tempfile

from benchmark.adapters import (
    BenchmarkManager,
    GSM8KAdapter,
    GSM8KTask,
    HumanEvalAdapter,
    HumanEvalTask,
    MBPPAdapter,
    MBPPTask,
    MMLUAdapter,
    MMLUTask,
    SWEBenchProAdapter,
    SWEBenchProTask,
    TaskResult,
)


def _create_temp_json(data):
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f)
    return path


# ─── HumanEval Tests ──────────────────────────────────────────────────────────

class TestHumanEvalAdapter:
    def test_load(self):
        path = _create_temp_json([
            {"task_id": "he1", "description": "Add", "code": "def add(a,b): return a+b", "test_cases": ["assert add(1,2)==3"]},
        ])
        adapter = HumanEvalAdapter()
        assert adapter.load(path) == 1
        os.unlink(path)

    def test_run_correct(self):
        adapter = HumanEvalAdapter()
        adapter.tasks["he1"] = HumanEvalTask(task_id="he1", description="Add", code="def add(a,b): return a+b", test_cases=["assert add(1,2)==3"])
        r = adapter.run("he1", "def add(a,b): return a+b")
        assert r.success is True
        assert r.score == 1.0

    def test_run_incorrect(self):
        adapter = HumanEvalAdapter()
        adapter.tasks["he1"] = HumanEvalTask(task_id="he1", description="Add", code="def add(a,b): return a+b", test_cases=["assert add(1,2)==3"])
        r = adapter.run("he1", "def add(a,b): return a-b")
        assert r.success is False

    def test_run_missing(self):
        adapter = HumanEvalAdapter()
        assert adapter.run("nonexistent", "x=1") is None

    def test_get_pass_rate(self):
        adapter = HumanEvalAdapter()
        adapter.tasks["he1"] = HumanEvalTask(task_id="he1", description="Add", code="def add(a,b): return a+b", test_cases=["assert add(1,2)==3"])
        adapter.run("he1", "def add(a,b): return a+b")
        pr = adapter.get_pass_rate()
        assert pr["pass_rate"] == 1.0

    def test_get_pass_rate_empty(self):
        adapter = HumanEvalAdapter()
        pr = adapter.get_pass_rate()
        assert pr["pass_rate"] == 0.0

    def test_get_all_tasks(self):
        adapter = HumanEvalAdapter()
        adapter.tasks["he1"] = HumanEvalTask(task_id="he1", description="T", code="x=1", test_cases=[])
        assert len(adapter.get_all_tasks()) == 1


# ─── MBPP Tests ───────────────────────────────────────────────────────────────

class TestMBPPAdapter:
    def test_load(self):
        path = _create_temp_json([
            {"task_id": "mb1", "description": "Square", "code": "def sq(x): return x*x", "test_cases": ["assert sq(3)==9"]},
        ])
        adapter = MBPPAdapter()
        assert adapter.load(path) == 1
        os.unlink(path)

    def test_run_correct(self):
        adapter = MBPPAdapter()
        adapter.tasks["mb1"] = MBPPTask(task_id="mb1", description="Square", code="def sq(x): return x*x", test_cases=["assert sq(3)==9"])
        r = adapter.run("mb1", "def sq(x): return x*x")
        assert r.success is True

    def test_run_incorrect(self):
        adapter = MBPPAdapter()
        adapter.tasks["mb1"] = MBPPTask(task_id="mb1", description="Square", code="def sq(x): return x*x", test_cases=["assert sq(3)==9"])
        r = adapter.run("mb1", "def sq(x): return x+1")
        assert r.success is False

    def test_run_missing(self):
        adapter = MBPPAdapter()
        assert adapter.run("nonexistent", "x=1") is None

    def test_get_pass_rate(self):
        adapter = MBPPAdapter()
        adapter.tasks["mb1"] = MBPPTask(task_id="mb1", description="Square", code="def sq(x): return x*x", test_cases=["assert sq(3)==9"])
        adapter.run("mb1", "def sq(x): return x*x")
        pr = adapter.get_pass_rate()
        assert pr["pass_rate"] == 1.0


# ─── MMLU Tests ────────────────────────────────────────────────────────────────

class TestMMLUAdapter:
    def test_load(self):
        path = _create_temp_json([
            {"task_id": "mm1", "question": "What is 2+2?", "subject": "math", "choices": ["1", "2", "3", "4"], "answer": 3},
        ])
        adapter = MMLUAdapter()
        assert adapter.load(path) == 1
        os.unlink(path)

    def test_run_correct(self):
        adapter = MMLUAdapter()
        adapter.tasks["mm1"] = MMLUTask(task_id="mm1", question="What is 2+2?", subject="math", choices=["1", "2", "3", "4"], answer=3)
        r = adapter.run("mm1", 3)
        assert r.success is True

    def test_run_incorrect(self):
        adapter = MMLUAdapter()
        adapter.tasks["mm1"] = MMLUTask(task_id="mm1", question="What is 2+2?", subject="math", choices=["1", "2", "3", "4"], answer=3)
        r = adapter.run("mm1", 0)
        assert r.success is False

    def test_run_missing(self):
        adapter = MMLUAdapter()
        assert adapter.run("nonexistent", 0) is None

    def test_get_pass_rate(self):
        adapter = MMLUAdapter()
        adapter.tasks["mm1"] = MMLUTask(task_id="mm1", question="Q", subject="math", choices=["a", "b", "c", "d"], answer=0)
        adapter.tasks["mm2"] = MMLUTask(task_id="mm2", question="Q", subject="math", choices=["a", "b", "c", "d"], answer=1)
        adapter.run("mm1", 0)  # correct
        adapter.run("mm2", 0)  # wrong
        pr = adapter.get_pass_rate()
        assert pr["pass_rate"] == 0.5

    def test_subject_pass_rate(self):
        adapter = MMLUAdapter()
        adapter.tasks["mm1"] = MMLUTask(task_id="mm1", question="Q", subject="math", choices=["a", "b", "c", "d"], answer=0)
        adapter.tasks["mm2"] = MMLUTask(task_id="mm2", question="Q", subject="science", choices=["a", "b", "c", "d"], answer=1)
        adapter.run("mm1", 0)  # correct
        adapter.run("mm2", 0)  # wrong
        pr = adapter.get_subject_pass_rate("math")
        assert pr["pass_rate"] == 1.0


# ─── GSM8K Tests ───────────────────────────────────────────────────────────────

class TestGSM8KAdapter:
    def test_load(self):
        path = _create_temp_json([
            {"task_id": "g1", "question": "What is 5+3?", "answer": 8},
        ])
        adapter = GSM8KAdapter()
        assert adapter.load(path) == 1
        os.unlink(path)

    def test_run_correct(self):
        adapter = GSM8KAdapter()
        adapter.tasks["g1"] = GSM8KTask(task_id="g1", question="What is 5+3?", answer=8)
        r = adapter.run("g1", "The answer is 8")
        assert r.success is True

    def test_run_incorrect(self):
        adapter = GSM8KAdapter()
        adapter.tasks["g1"] = GSM8KTask(task_id="g1", question="Q", answer=42)
        r = adapter.run("g1", "The answer is 99")
        assert r.success is False

    def test_run_no_number(self):
        adapter = GSM8KAdapter()
        adapter.tasks["g1"] = GSM8KTask(task_id="g1", question="Q", answer=42)
        r = adapter.run("g1", "I don't know")
        assert r.success is False
        assert r.error is not None

    def test_run_float(self):
        adapter = GSM8KAdapter()
        adapter.tasks["g1"] = GSM8KTask(task_id="g1", question="Q", answer=3.14)
        r = adapter.run("g1", "The answer is 3.14")
        assert r.success is True

    def test_run_missing(self):
        adapter = GSM8KAdapter()
        assert adapter.run("nonexistent", "42") is None

    def test_get_pass_rate(self):
        adapter = GSM8KAdapter()
        adapter.tasks["g1"] = GSM8KTask(task_id="g1", question="Q", answer=10)
        adapter.tasks["g2"] = GSM8KTask(task_id="g2", question="Q", answer=20)
        adapter.run("g1", "The answer is 10")
        adapter.run("g2", "The answer is 999")
        pr = adapter.get_pass_rate()
        assert pr["pass_rate"] == 0.5


# ─── BenchmarkManager Tests ────────────────────────────────────────────────────

class TestBenchmarkManager:
    def test_create(self):
        mgr = BenchmarkManager()
        assert len(mgr.adapters) == 0

    def test_register(self):
        mgr = BenchmarkManager()
        adapter = HumanEvalAdapter()
        mgr.register("humaneval", adapter)
        assert "humaneval" in mgr.adapters

    def test_load(self):
        path = _create_temp_json([
            {"task_id": "he1", "description": "Add", "code": "def add(a,b): return a+b", "test_cases": ["assert add(1,2)==3"]},
        ])
        mgr = BenchmarkManager()
        mgr.register("humaneval", HumanEvalAdapter())
        assert mgr.load("humaneval", path) == 1
        os.unlink(path)

    def test_run(self):
        mgr = BenchmarkManager()
        adapter = HumanEvalAdapter()
        adapter.tasks["he1"] = HumanEvalTask(task_id="he1", description="Add", code="def add(a,b): return a+b", test_cases=["assert add(1,2)==3"])
        mgr.register("humaneval", adapter)
        r = mgr.run("humaneval", "he1", "def add(a,b): return a+b")
        assert r is not None
        assert r.success is True

    def test_get_pass_rate(self):
        mgr = BenchmarkManager()
        adapter = HumanEvalAdapter()
        adapter.tasks["he1"] = HumanEvalTask(task_id="he1", description="Add", code="def add(a,b): return a+b", test_cases=["assert add(1,2)==3"])
        adapter.run("he1", "def add(a,b): return a+b")
        mgr.register("humaneval", adapter)
        pr = mgr.get_pass_rate("humaneval")
        assert pr["pass_rate"] == 1.0

    def test_get_all_pass_rates(self):
        mgr = BenchmarkManager()
        adapter = HumanEvalAdapter()
        adapter.tasks["he1"] = HumanEvalTask(task_id="he1", description="Add", code="def add(a,b): return a+b", test_cases=["assert add(1,2)==3"])
        adapter.run("he1", "def add(a,b): return a+b")
        mgr.register("humaneval", adapter)
        rates = mgr.get_all_pass_rates()
        assert "humaneval" in rates

    def test_get_adapter(self):
        mgr = BenchmarkManager()
        adapter = HumanEvalAdapter()
        mgr.register("humaneval", adapter)
        assert mgr.get_adapter("humaneval") is adapter

    def test_get_adapter_missing(self):
        mgr = BenchmarkManager()
        assert mgr.get_adapter("nonexistent") is None

    def test_load_missing_adapter(self):
        mgr = BenchmarkManager()
        assert mgr.load("nonexistent", "/tmp/x.json") == 0

    def test_run_missing_adapter(self):
        mgr = BenchmarkManager()
        assert mgr.run("nonexistent", "t1", "x=1") is None

    def test_get_pass_rate_missing_adapter(self):
        mgr = BenchmarkManager()
        pr = mgr.get_pass_rate("nonexistent")
        assert pr["pass_rate"] == 0.0


# ─── TaskResult Tests ──────────────────────────────────────────────────────────

class TestTaskResult:
    def test_create(self):
        r = TaskResult(id="r1", task_id="t1", benchmark="humaneval", success=True, score=1.0)
        assert r.success is True
        assert r.benchmark == "humaneval"

    def test_benchmark_names(self):
        r1 = TaskResult(id="r1", task_id="t1", benchmark="humaneval", success=True, score=1.0)
        r2 = TaskResult(id="r2", task_id="t2", benchmark="mbpp", success=True, score=1.0)
        r3 = TaskResult(id="r3", task_id="t3", benchmark="mmlu", success=True, score=1.0)
        r4 = TaskResult(id="r4", task_id="t4", benchmark="gsm8k", success=True, score=1.0)
        r5 = TaskResult(id="r5", task_id="t5", benchmark="swebenchpro", success=True, score=1.0)
        assert r1.benchmark == "humaneval"
        assert r2.benchmark == "mbpp"
        assert r3.benchmark == "mmlu"
        assert r4.benchmark == "gsm8k"
        assert r5.benchmark == "swebenchpro"


# ─── SWEBenchPro Tests ──────────────────────────────────────────────────────────

class TestSWEBenchProAdapter:
    def test_load(self):
        path = _create_temp_json([
            {"instance_id": "sw1", "repo": "django/django", "base_commit": "abc", "issue_title": "Fix", "issue_description": "Bug", "patch": "p", "test_patch": "tp"},
        ])
        adapter = SWEBenchProAdapter()
        assert adapter.load(path) == 1
        os.unlink(path)

    def test_run_correct(self):
        adapter = SWEBenchProAdapter()
        adapter.tasks["sw1"] = SWEBenchProTask(instance_id="sw1", repo="django/django", base_commit="abc", issue_title="Fix", issue_description="Bug", patch="p", test_patch="tp")
        r = adapter.run("sw1", "patch", {"t1": True, "t2": True})
        assert r.success is True
        assert r.score == 1.0

    def test_run_partial(self):
        adapter = SWEBenchProAdapter()
        adapter.tasks["sw1"] = SWEBenchProTask(instance_id="sw1", repo="django/django", base_commit="abc", issue_title="Fix", issue_description="Bug", patch="p", test_patch="tp")
        r = adapter.run("sw1", "patch", {"t1": True, "t2": False})
        assert r.score == 0.5

    def test_run_missing(self):
        adapter = SWEBenchProAdapter()
        assert adapter.run("nonexistent", "patch", {"t1": True}) is None

    def test_run_no_tests(self):
        adapter = SWEBenchProAdapter()
        adapter.tasks["sw1"] = SWEBenchProTask(instance_id="sw1", repo="django/django", base_commit="abc", issue_title="Fix", issue_description="Bug", patch="p", test_patch="tp")
        r = adapter.run("sw1", "patch", {})
        assert r.score == 0.0

    def test_get_pass_rate(self):
        adapter = SWEBenchProAdapter()
        adapter.tasks["sw1"] = SWEBenchProTask(instance_id="sw1", repo="django/django", base_commit="abc", issue_title="Fix", issue_description="Bug", patch="p", test_patch="tp")
        adapter.tasks["sw2"] = SWEBenchProTask(instance_id="sw2", repo="sympy/sympy", base_commit="def", issue_title="Fix", issue_description="Bug", patch="p", test_patch="tp")
        adapter.run("sw1", "patch", {"t1": True, "t2": True})
        adapter.run("sw2", "patch", {"t1": False})
        pr = adapter.get_pass_rate()
        assert pr["pass_rate"] == 0.5

    def test_get_pass_rate_empty(self):
        adapter = SWEBenchProAdapter()
        pr = adapter.get_pass_rate()
        assert pr["pass_rate"] == 0.0

    def test_repo_pass_rate(self):
        adapter = SWEBenchProAdapter()
        adapter.tasks["sw1"] = SWEBenchProTask(instance_id="sw1", repo="django/django", base_commit="abc", issue_title="Fix", issue_description="Bug", patch="p", test_patch="tp")
        adapter.tasks["sw2"] = SWEBenchProTask(instance_id="sw2", repo="sympy/sympy", base_commit="def", issue_title="Fix", issue_description="Bug", patch="p", test_patch="tp")
        adapter.run("sw1", "patch", {"t1": True})
        adapter.run("sw2", "patch", {"t1": False})
        pr = adapter.get_repo_pass_rate("django/django")
        assert pr["pass_rate"] == 1.0

    def test_get_all_tasks(self):
        adapter = SWEBenchProAdapter()
        adapter.tasks["sw1"] = SWEBenchProTask(instance_id="sw1", repo="django/django", base_commit="abc", issue_title="Fix", issue_description="Bug", patch="p", test_patch="tp")
        assert len(adapter.get_all_tasks()) == 1


# ─── BenchmarkManager Extended Tests ────────────────────────────────────────────

class TestBenchmarkManagerExtended:
    def test_register_all_adapters(self):
        mgr = BenchmarkManager()
        mgr.register("humaneval", HumanEvalAdapter())
        mgr.register("mbpp", MBPPAdapter())
        mgr.register("mmlu", MMLUAdapter())
        mgr.register("gsm8k", GSM8KAdapter())
        mgr.register("swebenchpro", SWEBenchProAdapter())
        assert len(mgr.get_adapter_names()) == 5

    def test_get_adapter_names(self):
        mgr = BenchmarkManager()
        mgr.register("humaneval", HumanEvalAdapter())
        mgr.register("mbpp", MBPPAdapter())
        names = mgr.get_adapter_names()
        assert "humaneval" in names
        assert "mbpp" in names
