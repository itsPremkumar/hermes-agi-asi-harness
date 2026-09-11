"""
Hermes AGI/ASI Harness — NVIDIA AVO Lineage Tree Memory.

Tracks evolutionary ancestry, candidate mutations, parentage, compiler logs,
and multi-objective fitness scores across generations.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LineageNode:
    """A single candidate solution in the evolutionary lineage DAG."""
    node_id: str
    parent_ids: list[str]  # Empty for seed; 1 for mutation; 2+ for crossover
    generation: int
    code: str
    mutation_description: str
    fitness_scores: dict[str, float] = field(default_factory=dict)
    composite_fitness: float = 0.0
    compiler_feedback: str = ""
    operator_type: str = "seed"  # seed, agentic_mutation, agentic_crossover, repair
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "parent_ids": self.parent_ids,
            "generation": self.generation,
            "mutation_description": self.mutation_description,
            "composite_fitness": round(self.composite_fitness, 4),
            "fitness_scores": {k: round(v, 4) for k, v in self.fitness_scores.items()},
            "operator_type": self.operator_type,
            "timestamp": self.timestamp,
        }


class LineageDAG:
    """
    Directed Acyclic Graph (DAG) preserving complete evolutionary history.
    Allows the agent to consult successful lineages and avoid past failed paths.
    """

    def __init__(self):
        self.nodes: dict[str, LineageNode] = {}
        self.generation_map: dict[int, list[str]] = {}

    def add_node(self, node: LineageNode) -> None:
        """Register a node in the lineage memory."""
        self.nodes[node.node_id] = node
        gen = node.generation
        if gen not in self.generation_map:
            self.generation_map[gen] = []
        self.generation_map[gen].append(node.node_id)

    def get_node(self, node_id: str) -> LineageNode | None:
        return self.nodes.get(node_id)

    def get_best_nodes(self, k: int = 3) -> list[LineageNode]:
        """Return top-k fittest candidates in the entire evolutionary history."""
        sorted_nodes = sorted(
            self.nodes.values(),
            key=lambda n: n.composite_fitness,
            reverse=True,
        )
        return sorted_nodes[:k]

    def get_generation_nodes(self, gen: int) -> list[LineageNode]:
        """Get all candidates evaluated in a specific generation."""
        ids = self.generation_map.get(gen, [])
        return [self.nodes[nid] for nid in ids if nid in self.nodes]

    def get_ancestors(self, node_id: str, max_depth: int = 5) -> list[LineageNode]:
        """Retrieve ancestral lineage leading up to node_id."""
        ancestors: list[LineageNode] = []
        curr_id = node_id
        depth = 0

        while curr_id and depth < max_depth:
            node = self.nodes.get(curr_id)
            if not node or not node.parent_ids:
                break
            # Follow primary parent
            curr_id = node.parent_ids[0]
            parent_node = self.nodes.get(curr_id)
            if parent_node:
                ancestors.append(parent_node)
            depth += 1

        return ancestors

    def compute_population_entropy(self, gen: int | None = None) -> float:
        """
        Compute Shannon entropy of the population to detect search stagnation.
        Low entropy indicates population convergence/stagnation.
        """
        target_nodes = self.get_generation_nodes(gen) if gen is not None else list(self.nodes.values())
        if len(target_nodes) <= 1:
            return 1.0

        scores = [max(0.001, n.composite_fitness) for n in target_nodes]
        total = sum(scores)
        probs = [s / total for s in scores]

        entropy = -sum(p * math.log2(p) for p in probs if p > 0)
        max_entropy = math.log2(len(scores)) if len(scores) > 1 else 1.0
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 1.0

        return round(normalized_entropy, 4)

    def get_lineage_summary_for_prompt(self, node_id: str) -> str:
        """Format an ancestral summary to inject into the agent's variation prompt."""
        node = self.nodes.get(node_id)
        if not node:
            return "No prior lineage available."

        ancestors = self.get_ancestors(node_id, max_depth=3)
        lines = [f"Parent Candidate [{node.node_id}]: Fitness = {node.composite_fitness:.4f}"]
        lines.append(f"- Strategy: {node.mutation_description}")

        if ancestors:
            lines.append("Ancestral Predecessors:")
            for anc in ancestors:
                lines.append(f"  - [{anc.node_id}] (Gen {anc.generation}): Fitness = {anc.composite_fitness:.4f} ({anc.mutation_description})")

        return "\n".join(lines)
