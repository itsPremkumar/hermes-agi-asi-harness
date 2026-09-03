"""
Unit tests for NVIDIA AVO (Agentic Variation Operators) Architecture:
- Lineage DAG Memory (Ancestry & Population Entropy)
- Domain Knowledge Base
- Agentic Mutation & In-Harness Multi-Turn Repair
- Agentic Crossover across Distant Parents
- AVOSupervisor Anti-Stagnation Steering
- AVOEvolutionEngine End-to-End Search
"""

from __future__ import annotations

import pytest

from engines.avo import (
    AVOEvolutionEngine,
    AVOResult,
    LineageDAG,
    LineageNode,
    DomainKnowledgeBase,
    AgenticVariationOperator,
    AVOSupervisor,
    SupervisorIntervention,
)


class TestLineageDAG:
    """Test Lineage DAG and ancestral memory tracking."""

    def test_add_and_retrieve_ancestors(self):
        dag = LineageDAG()
        parent = LineageNode(
            node_id="root-1",
            parent_ids=[],
            generation=0,
            code="def f(): return 1",
            mutation_description="Root seed",
            composite_fitness=0.80,
        )
        child = LineageNode(
            node_id="child-1",
            parent_ids=["root-1"],
            generation=1,
            code="def f(): return 2",
            mutation_description="Gen 1 mutation",
            composite_fitness=0.88,
        )
        dag.add_node(parent)
        dag.add_node(child)

        ancestors = dag.get_ancestors("child-1")
        assert len(ancestors) == 1
        assert ancestors[0].node_id == "root-1"

    def test_population_entropy(self):
        dag = LineageDAG()
        for i in range(4):
            node = LineageNode(
                node_id=f"n-{i}",
                parent_ids=[],
                generation=0,
                code="x = 1",
                mutation_description="seed",
                composite_fitness=0.5 + (0.1 * i),
            )
            dag.add_node(node)

        entropy = dag.compute_population_entropy(gen=0)
        assert 0.0 <= entropy <= 1.0


class TestDomainKnowledgeBase:
    """Test Domain Knowledge Base retrieval."""

    def test_query_knowledge(self):
        kb = DomainKnowledgeBase()
        rules = kb.query(["memory", "cache", "coalescing"])
        assert len(rules) > 0
        assert any("coalescing" in r.lower() or "cache" in r.lower() for r in rules)


class TestAgenticOperator:
    """Test Agentic Mutation, Crossover, and In-Harness Repair."""

    def test_agentic_mutation(self):
        op = AgenticVariationOperator()
        parent = LineageNode(
            node_id="parent-0",
            parent_ids=[],
            generation=0,
            code="def execute():\n    return {'val': 10}\n",
            mutation_description="Seed",
            composite_fitness=0.75,
        )
        mutated = op.mutate(parent=parent, generation=1, objective="improve cache locality")
        assert isinstance(mutated, LineageNode)
        assert mutated.generation == 1
        assert mutated.parent_ids == ["parent-0"]
        assert mutated.composite_fitness > 0.0

    def test_agentic_crossover(self):
        op = AgenticVariationOperator()
        p1 = LineageNode("p1", [], 0, "def part_a(): pass", "Trait A", composite_fitness=0.80)
        p2 = LineageNode("p2", [], 0, "def part_b(): pass", "Trait B", composite_fitness=0.82)
        child = op.crossover(p1, p2, generation=1, objective="hybrid optimization")
        assert isinstance(child, LineageNode)
        assert child.operator_type == "agentic_crossover"
        assert len(child.parent_ids) == 2


class TestAVOSupervisor:
    """Test Supervisor Anti-Stagnation monitoring."""

    def test_nominal_search(self):
        supervisor = AVOSupervisor(stagnation_window=3)
        dag = LineageDAG()
        for i in range(3):
            dag.add_node(LineageNode(f"n-{i}", [], 0, "code", "desc", composite_fitness=0.80 + i * 0.05))
        intervention = supervisor.evaluate_search_progress(dag, current_gen=0)
        assert isinstance(intervention, SupervisorIntervention)
        assert intervention.stagnation_detected is False


class TestAVOEvolutionEngine:
    """Test master AVO evolutionary engine."""

    def test_engine_evolution_run(self):
        engine = AVOEvolutionEngine(population_size=3)
        res = engine.run(
            objective="optimize matrix tiling",
            seed_code="def tile(): return [1, 2, 3]\n",
            generations=2,
        )
        assert isinstance(res, AVOResult)
        assert res.generations_completed == 2
        assert res.total_candidates_evaluated >= 6
        assert res.best_candidate is not None
