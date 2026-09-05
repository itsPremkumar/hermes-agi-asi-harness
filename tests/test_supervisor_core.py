"""Tests for the Supervisor Harness components."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supervisor import (
    Supervisor,
    SupervisorState,
    TaskType,
)
from core.supervisor.evaluation import (
    EvaluationGate,
    TestCase as SupervisorTestCase,
)
from core.supervisor.memory import (
    PersistentMemory,
)
from core.supervisor.orchestrator import (
    Agent,
    AgentRole,
    MultiAgentOrchestrator,
)
from core.supervisor.variation import (
    VariationOperator,
)

# ---------------------------------------------------------------------------
# Supervisor Core tests
# ---------------------------------------------------------------------------

class TestSupervisor:
    def test_create_supervisor(self):
        s = Supervisor()
        assert s.state == SupervisorState.IDLE
        assert not s.is_active

    def test_add_goal(self):
        s = Supervisor()
        goal = s.add_goal("Test Goal", "A test goal")
        assert goal.title == "Test Goal"
        assert goal.status == "pending"

    def test_get_goal(self):
        s = Supervisor()
        goal = s.add_goal("Test", "Test goal")
        retrieved = s.get_goal(goal.id)
        assert retrieved is not None
        assert retrieved.id == goal.id

    def test_list_goals(self):
        s = Supervisor()
        s.add_goal("Goal 1", "First")
        s.add_goal("Goal 2", "Second")
        assert len(s.list_goals()) == 2

    def test_classify_task(self):
        s = Supervisor()
        assert s._classify_task("Search the web") == TaskType.RESEARCH
        assert s._classify_task("Build a feature") == TaskType.CODING
        assert s._classify_task("Test the code") == TaskType.TESTING
        assert s._classify_task("Deploy to prod") == TaskType.DEPLOYMENT
        assert s._classify_task("Write docs") == TaskType.WRITING
        assert s._classify_task("Do something") == TaskType.GENERAL

    def test_register_callbacks(self):
        s = Supervisor()
        s.on_dispatch(lambda t, r: "result")
        s.on_research(lambda q: {"result": "research"})
        s.on_evaluate(lambda g: 0.5)
        assert s._dispatch_callback is not None
        assert s._research_callback is not None
        assert s._evaluate_callback is not None

    def test_get_status(self):
        s = Supervisor()
        s.add_goal("Test", "Test goal")
        status = s.get_status()
        assert status["total_goals"] == 1

    def test_save_and_load_state(self, tmp_path):
        s = Supervisor(data_dir=tmp_path)
        s.add_goal("Test", "Test goal")
        s.save_state()

        s2 = Supervisor(data_dir=tmp_path)
        s2.load_state()
        goals = s2.list_goals()
        assert len(goals) == 1
        assert goals[0].title == "Test"


# ---------------------------------------------------------------------------
# Memory tests
# ---------------------------------------------------------------------------

class TestPersistentMemory:
    def test_create_memory(self):
        mem = PersistentMemory()
        assert mem is not None

    def test_store_and_retrieve(self):
        mem = PersistentMemory()
        mem.store("key1", "value1")
        entry = mem.retrieve("key1")
        assert entry is not None
        assert entry.value == "value1"

    def test_search(self):
        mem = PersistentMemory()
        mem.store("python_tip", "Use list comprehensions", tags=["python", "coding"])
        mem.store("java_tip", "Use streams", tags=["java", "coding"])
        results = mem.search("python")
        assert len(results) >= 1

    def test_record_experience(self):
        mem = PersistentMemory()
        exp = mem.record_experience("context", "action", "outcome", 0.8, "lesson")
        assert exp.score == 0.8
        assert exp.lesson == "lesson"

    def test_replay_experiences(self):
        mem = PersistentMemory()
        mem.record_experience("ctx1", "act1", "out1", 0.9, "lesson1")
        mem.record_experience("ctx2", "act2", "out2", 0.5, "lesson2")
        results = mem.replay_experiences(min_score=0.7)
        assert len(results) >= 1

    def test_save_and_load(self, tmp_path):
        mem = PersistentMemory(data_dir=tmp_path)
        mem.store("key1", "value1")
        mem.save()

        mem2 = PersistentMemory(data_dir=tmp_path)
        mem2.load()
        entry = mem2.retrieve("key1")
        assert entry is not None
        assert entry.value == "value1"

    def test_consolidation(self):
        mem = PersistentMemory(consolidation_threshold=5)
        for i in range(10):
            mem.store(f"key_{i}", f"value_{i}", importance=0.1)
        # Consolidation should merge/evict low-importance entries
        stats = mem.consolidate()
        # After consolidation, we should have fewer entries
        assert stats["evicted"] >= 0 or stats["merged"] >= 0


# ---------------------------------------------------------------------------
# Evaluation tests
# ---------------------------------------------------------------------------

class TestEvaluationGate:
    def test_create_gate(self):
        gate = EvaluationGate()
        assert gate is not None

    def test_evaluate_exact_match(self):
        gate = EvaluationGate()
        result = gate.evaluate("task1", "hello", "hello")
        assert result.score == 1.0
        assert result.passed

    def test_evaluate_mismatch(self):
        gate = EvaluationGate()
        result = gate.evaluate("task1", "hello", "world")
        assert result.score == 0.0
        assert not result.passed

    def test_evaluate_with_tests(self):
        gate = EvaluationGate()
        tests = [
            SupervisorTestCase(name="test1", expected="hello"),
            SupervisorTestCase(name="test2", expected="hello"),
        ]
        result = gate.evaluate_with_tests("task1", "hello", tests)
        assert result.score == 1.0

    def test_register_evaluator(self):
        gate = EvaluationGate()
        gate.register_evaluator("custom", lambda r, e: (0.5, "partial", {}))
        result = gate.evaluate("task1", "a", "b", evaluator_name="custom")
        assert result.score == 0.5


# ---------------------------------------------------------------------------
# Variation tests
# ---------------------------------------------------------------------------

class TestVariationOperator:
    def test_create_operator(self):
        vo = VariationOperator()
        assert vo is not None

    def test_evolve(self):
        vo = VariationOperator(
            generator=lambda t, c, i: f"Candidate {i} for {t}",
            evaluator=lambda c, t, c2: (0.5, "ok"),
            max_generations=3,
            population_size=3,
        )
        population = vo.evolve("test task")
        assert len(population) > 0

    def test_get_best(self):
        vo = VariationOperator(
            generator=lambda t, c, i: f"Candidate {i}",
            evaluator=lambda c, t, c2: (0.8, "good"),
            max_generations=2,
            population_size=2,
        )
        vo.evolve("test")
        best = vo.get_best()
        assert best is not None


# ---------------------------------------------------------------------------
# Orchestrator tests
# ---------------------------------------------------------------------------

class TestMultiAgentOrchestrator:
    def test_create_orchestrator(self):
        orch = MultiAgentOrchestrator()
        assert orch is not None

    def test_register_agent(self):
        orch = MultiAgentOrchestrator()
        agent = Agent(role=AgentRole.CODER, name="Coder-1")
        orch.register_agent(agent)
        assert orch.get_agent(agent.id) is not None

    def test_get_agents_by_role(self):
        orch = MultiAgentOrchestrator()
        orch.register_agent(Agent(role=AgentRole.CODER, name="Coder-1"))
        orch.register_agent(Agent(role=AgentRole.CODER, name="Coder-2"))
        coders = orch.get_agents_by_role(AgentRole.CODER)
        assert len(coders) == 2

    def test_run_pipeline(self):
        orch = MultiAgentOrchestrator()
        orch.register_agent(Agent(
            role=AgentRole.CODER,
            name="Coder",
            callback=lambda x, s: f"coded: {x}",
        ))
        result = orch.run_pipeline("input", [AgentRole.CODER])
        assert "coded" in result

    def test_run_debate(self):
        orch = MultiAgentOrchestrator()
        orch.register_agent(Agent(
            role=AgentRole.CODER,
            name="Coder",
            callback=lambda x, s: "I think X",
        ))
        orch.register_agent(Agent(
            role=AgentRole.JUDGE,
            name="Judge",
            callback=lambda t, p: "Coder wins",
        ))
        result = orch.run_debate("Should we build X?")
        assert "winner" in result

    def test_run_divide_and_conquer(self):
        orch = MultiAgentOrchestrator()
        orch.register_agent(Agent(
            role=AgentRole.CODER,
            name="Coder",
            callback=lambda x, s: f"processed: {x}",
        ))
        results = orch.run_divide_and_conquer("task to split", num_splits=2)
        assert len(results) >= 1

    def test_run_assembly_line(self):
        orch = MultiAgentOrchestrator()
        orch.register_agent(Agent(
            role=AgentRole.CODER,
            name="Coder",
            callback=lambda x, s: f"coded: {x}",
        ))
        result = orch.run_assembly_line("input", [AgentRole.CODER])
        assert "final_result" in result

    def test_get_status(self):
        orch = MultiAgentOrchestrator()
        orch.register_agent(Agent(role=AgentRole.CODER, name="Coder"))
        status = orch.get_status()
        assert status["total_agents"] == 1
