"""
Hermes AGI/ASI Harness — NVIDIA AVO Master Evolutionary Engine.

Coordinates the full AVO lifecycle:
- Population initialization & Lineage DAG tracking
- Supervisor anti-stagnation monitoring & diversity entropy
- Agentic Variation Operators (mutation & crossover with in-harness repair)
- Generation-by-generation Darwinian selection
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .knowledge_base import DomainKnowledgeBase
from .lineage import LineageDAG, LineageNode
from .operator import AgenticVariationOperator
from .supervisor import AVOSupervisor, SupervisorIntervention

logger = logging.getLogger("hermes.avo.engine")


@dataclass
class AVOResult:
    """The outcome of an NVIDIA AVO autonomous evolutionary search."""
    objective: str
    generations_completed: int
    total_candidates_evaluated: int
    best_candidate: LineageNode
    initial_fitness: float
    final_fitness: float
    fitness_gain_percent: float
    interventions_issued: int
    elapsed_seconds: float
    lineage_nodes_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective": self.objective,
            "generations_completed": self.generations_completed,
            "total_candidates_evaluated": self.total_candidates_evaluated,
            "best_candidate": self.best_candidate.to_dict(),
            "initial_fitness": round(self.initial_fitness, 4),
            "final_fitness": round(self.final_fitness, 4),
            "fitness_gain_percent": round(self.fitness_gain_percent, 2),
            "interventions_issued": self.interventions_issued,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "lineage_nodes_count": self.lineage_nodes_count,
        }


class AVOEvolutionEngine:
    """
    NVIDIA AVO Autonomous Evolutionary Search Engine.
    Executes population evolution driven by Agentic Variation Operators.
    """

    def __init__(
        self,
        workspace_root: str = ".",
        population_size: int = 4,
    ):
        self.workspace_root = workspace_root
        self.population_size = population_size
        self.lineage = LineageDAG()
        self.kb = DomainKnowledgeBase()
        self.supervisor = AVOSupervisor()
        self.operator = AgenticVariationOperator(knowledge_base=self.kb, workspace_root=workspace_root)
        self.current_generation = 0
        self.interventions_count = 0

    def initialize_population(self, seed_code: str, objective: str) -> None:
        """Create initial seed generation in Lineage DAG."""
        self.current_generation = 0
        seed_node = LineageNode(
            node_id=f"seed-{uuid.uuid4().hex[:6]}",
            parent_ids=[],
            generation=0,
            code=seed_code,
            mutation_description=f"Initial seed implementation for '{objective}'",
            fitness_scores={"accuracy": 0.80, "efficiency": 0.70},
            composite_fitness=0.770,
            operator_type="seed",
        )
        self.lineage.add_node(seed_node)

        # Generate initial population variants via mutation
        for i in range(self.population_size - 1):
            mutated = self.operator.mutate(
                parent=seed_node,
                generation=0,
                objective=objective,
            )
            self.lineage.add_node(mutated)

    def step_generation(self, objective: str) -> list[LineageNode]:
        """Advance evolution by one generation using AVO."""
        self.current_generation += 1
        gen = self.current_generation

        # 1. Supervisor evaluates search progress and diversity entropy
        prev_nodes = self.lineage.get_generation_nodes(gen - 1)
        intervention = self.supervisor.evaluate_search_progress(self.lineage, gen - 1)
        if intervention.stagnation_detected:
            self.interventions_count += 1

        # 2. Select top parents from prior generation
        parents = sorted(prev_nodes, key=lambda n: n.composite_fitness, reverse=True)
        survivors = parents[:max(1, self.population_size // 2)]

        new_generation: list[LineageNode] = []

        # 3. Apply Agentic Crossover if supervisor flags low entropy or stagnation
        if intervention.recommended_action == "crossover_distant" and len(survivors) >= 2:
            xover_child = self.operator.crossover(
                parent_a=survivors[0],
                parent_b=survivors[-1],
                generation=gen,
                objective=objective,
                intervention=intervention,
            )
            new_generation.append(xover_child)
            self.lineage.add_node(xover_child)

        # 4. Apply Agentic Mutations for remaining slots
        while len(new_generation) < self.population_size:
            parent = survivors[len(new_generation) % len(survivors)]
            mut_child = self.operator.mutate(
                parent=parent,
                generation=gen,
                objective=objective,
                intervention=intervention,
            )
            new_generation.append(mut_child)
            self.lineage.add_node(mut_child)

        return new_generation

    def run(self, objective: str, seed_code: str, generations: int = 3) -> AVOResult:
        """Run full autonomous evolution over multiple generations."""
        start_time = time.time()
        self.initialize_population(seed_code=seed_code, objective=objective)

        initial_best = self.lineage.get_best_nodes(1)[0].composite_fitness

        for _ in range(generations):
            self.step_generation(objective=objective)

        final_best_node = self.lineage.get_best_nodes(1)[0]
        final_best = final_best_node.composite_fitness
        gain_pct = ((final_best - initial_best) / initial_best) * 100 if initial_best > 0 else 0.0

        return AVOResult(
            objective=objective,
            generations_completed=generations,
            total_candidates_evaluated=len(self.lineage.nodes),
            best_candidate=final_best_node,
            initial_fitness=initial_best,
            final_fitness=final_best,
            fitness_gain_percent=gain_pct,
            interventions_issued=self.interventions_count,
            elapsed_seconds=time.time() - start_time,
            lineage_nodes_count=len(self.lineage.nodes),
        )
