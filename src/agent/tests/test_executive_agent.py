"""Tests for executive_agent.py — Executive Agent."""
import pytest

from agent.executive_agent import ExecutiveAgent, AgentTask, AgentPlan


class MockBenchmark:
    def __init__(self, name: str, has_pass_rate: bool = True) -> None:
        self.name = name
        self.has_pass_rate = has_pass_rate
        self.loaded = False
        self.run = False

    def load_problems(self) -> int:
        self.loaded = True
        return 10

    def run_all(self) -> list:
        self.run = True
        return []

    def get_pass_rate(self) -> dict:
        return {"pass_rate": 0.8, "total": 10}


class MockBenchmarkNoPassRate:
    def load_problems(self) -> int:
        return 5

    def run_all(self) -> list:
        return []

    def get_accuracy(self) -> dict:
        return {"accuracy": 0.9}


class MockBenchmarkFailing:
    def load_problems(self) -> int:
        raise RuntimeError("Load failed")

    def run_all(self) -> list:
        return []


class TestAgentTask:
    def test_create(self):
        t = AgentTask(id="t1", benchmark="mmlu", task_type="evaluate")
        assert t.status == "pending"
        assert t.benchmark == "mmlu"

    def test_complete(self):
        t = AgentTask(id="t1", benchmark="mmlu", task_type="evaluate")
        t.complete({"score": 0.9})
        assert t.status == "completed"
        assert t.result == {"score": 0.9}
        assert t.completed_at is not None

    def test_fail(self):
        t = AgentTask(id="t1", benchmark="mmlu", task_type="evaluate")
        t.fail("Error")
        assert t.status == "failed"
        assert "error" in t.result


class TestAgentPlan:
    def test_create(self):
        tasks = [AgentTask(id="t1", benchmark="mmlu", task_type="evaluate")]
        plan = AgentPlan(id="p1", tasks=tasks)
        assert plan.total == 1
        assert plan.pending == 1

    def test_progress(self):
        tasks = [
            AgentTask(id="t1", benchmark="mmlu", task_type="evaluate"),
            AgentTask(id="t2", benchmark="gsm8k", task_type="evaluate"),
        ]
        tasks[0].complete({})
        plan = AgentPlan(id="p1", tasks=tasks)
        assert plan.progress == 0.5

    def test_progress_empty(self):
        plan = AgentPlan(id="p1", tasks=[])
        assert plan.progress == 0.0

    def test_completed_count(self):
        tasks = [
            AgentTask(id="t1", benchmark="mmlu", task_type="evaluate"),
            AgentTask(id="t2", benchmark="gsm8k", task_type="evaluate"),
        ]
        tasks[0].complete({})
        plan = AgentPlan(id="p1", tasks=tasks)
        assert plan.completed == 1
        assert plan.pending == 1


class TestExecutiveAgent:
    def test_create(self):
        agent = ExecutiveAgent()
        assert len(agent.list_benchmarks()) == 0

    def test_register_benchmark(self):
        agent = ExecutiveAgent()
        agent.register_benchmark("mmlu", MockBenchmark("mmlu"))
        assert "mmlu" in agent.list_benchmarks()

    def test_get_benchmark(self):
        agent = ExecutiveAgent()
        bench = MockBenchmark("mmlu")
        agent.register_benchmark("mmlu", bench)
        assert agent.get_benchmark("mmlu") is bench

    def test_get_benchmark_missing(self):
        agent = ExecutiveAgent()
        assert agent.get_benchmark("nonexistent") is None

    def test_create_plan(self):
        agent = ExecutiveAgent()
        agent.register_benchmark("mmlu", MockBenchmark("mmlu"))
        plan = agent.create_plan()
        assert plan.total == 1

    def test_create_plan_specific(self):
        agent = ExecutiveAgent()
        agent.register_benchmark("mmlu", MockBenchmark("mmlu"))
        agent.register_benchmark("gsm8k", MockBenchmark("gsm8k"))
        plan = agent.create_plan(["mmlu"])
        assert plan.total == 1
        assert plan.tasks[0].benchmark == "mmlu"

    def test_execute_plan(self):
        agent = ExecutiveAgent()
        agent.register_benchmark("mmlu", MockBenchmark("mmlu"))
        plan = agent.create_plan()
        results = agent.execute_plan(plan.id)
        assert "mmlu" in results

    def test_execute_plan_missing_benchmark(self):
        agent = ExecutiveAgent()
        plan = agent.create_plan(["nonexistent"])
        results = agent.execute_plan(plan.id)
        assert "error" in results["nonexistent"]

    def test_execute_plan_failing_benchmark(self):
        agent = ExecutiveAgent()
        agent.register_benchmark("failing", MockBenchmarkFailing())
        plan = agent.create_plan(["failing"])
        results = agent.execute_plan(plan.id)
        assert "error" in results["failing"]

    def test_get_plan(self):
        agent = ExecutiveAgent()
        agent.register_benchmark("mmlu", MockBenchmark("mmlu"))
        plan = agent.create_plan()
        assert agent.get_plan(plan.id) is plan

    def test_get_plan_missing(self):
        agent = ExecutiveAgent()
        assert agent.get_plan("nonexistent") is None

    def test_get_all_plans(self):
        agent = ExecutiveAgent()
        agent.register_benchmark("mmlu", MockBenchmark("mmlu"))
        agent.create_plan()
        agent.create_plan()
        assert len(agent.get_all_plans()) == 2

    def test_get_plan_results(self):
        agent = ExecutiveAgent()
        agent.register_benchmark("mmlu", MockBenchmark("mmlu"))
        plan = agent.create_plan()
        agent.execute_plan(plan.id)
        results = agent.get_plan_results(plan.id)
        assert "mmlu" in results

    def test_get_overall_progress(self):
        agent = ExecutiveAgent()
        agent.register_benchmark("mmlu", MockBenchmark("mmlu"))
        plan = agent.create_plan()
        agent.execute_plan(plan.id)
        assert agent.get_overall_progress(plan.id) == 1.0

    def test_get_plan_summary(self):
        agent = ExecutiveAgent()
        agent.register_benchmark("mmlu", MockBenchmark("mmlu"))
        plan = agent.create_plan()
        summary = agent.get_plan_summary(plan.id)
        assert summary["total_tasks"] == 1

    def test_clear_plans(self):
        agent = ExecutiveAgent()
        agent.register_benchmark("mmlu", MockBenchmark("mmlu"))
        agent.create_plan()
        agent.clear_plans()
        assert len(agent.get_all_plans()) == 0

    def test_execute_plan_with_no_pass_rate(self):
        agent = ExecutiveAgent()
        agent.register_benchmark("mmlu", MockBenchmarkNoPassRate())
        plan = agent.create_plan()
        results = agent.execute_plan(plan.id)
        assert "mmlu" in results

    def test_multiple_benchmarks(self):
        agent = ExecutiveAgent()
        agent.register_benchmark("mmlu", MockBenchmark("mmlu"))
        agent.register_benchmark("gsm8k", MockBenchmark("gsm8k"))
        agent.register_benchmark("mbpp", MockBenchmark("mbpp"))
        plan = agent.create_plan()
        results = agent.execute_plan(plan.id)
        assert len(results) == 3

    def test_plan_strategy(self):
        agent = ExecutiveAgent()
        agent.register_benchmark("mmlu", MockBenchmark("mmlu"))
        plan = agent.create_plan(strategy="sequential")
        assert plan.strategy == "sequential"
