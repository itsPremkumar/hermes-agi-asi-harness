"""
Hermes AGI/ASI Harness — NVIDIA AVO Supervisor Agent (Anti-Stagnation).

Monitors population fitness curves, tracks diversity entropy, detects local optima
stagnation, and injects high-level steering directives to guide long-horizon evolution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .lineage import LineageDAG

logger = logging.getLogger("hermes.avo.supervisor")


@dataclass
class SupervisorIntervention:
    """A strategic guidance directive injected when search stagnates."""
    stagnation_detected: bool
    stagnant_generations: int
    current_entropy: float
    steering_directive: str
    recommended_action: str  # diversify, mutate_macro, crossover_distant, explore_boundary


class AVOSupervisor:
    """
    Supervisor Agent that guides long-horizon evolutionary search.
    Prevents convergence onto deceptive local optima.
    """

    def __init__(
        self,
        stagnation_window: int = 3,
        improvement_threshold: float = 0.01,
        entropy_threshold: float = 0.40,
    ):
        self.stagnation_window = stagnation_window
        self.improvement_threshold = improvement_threshold
        self.entropy_threshold = entropy_threshold
        self.fitness_history: list[float] = []

    def evaluate_search_progress(self, lineage: LineageDAG, current_gen: int) -> SupervisorIntervention:
        """Analyze population progress and issue steering directives if needed."""
        nodes = lineage.get_generation_nodes(current_gen)
        if not nodes:
            return SupervisorIntervention(
                stagnation_detected=False,
                stagnant_generations=0,
                current_entropy=1.0,
                steering_directive="Initial generation. Proceed with baseline exploration.",
                recommended_action="explore_boundary",
            )

        best_node = max(nodes, key=lambda n: n.composite_fitness)
        curr_best = best_node.composite_fitness
        self.fitness_history.append(curr_best)

        entropy = lineage.compute_population_entropy(current_gen)

        # Check for stagnation over window
        stagnant_count = 0
        if len(self.fitness_history) >= 2:
            recent = self.fitness_history[-self.stagnation_window:]
            if len(recent) >= 2 and (recent[-1] - recent[0]) < self.improvement_threshold:
                stagnant_count = len(recent)

        stagnation_detected = (stagnant_count >= self.stagnation_window) or (entropy < self.entropy_threshold)

        if stagnation_detected:
            if entropy < self.entropy_threshold:
                directive = (
                    f"CRITICAL STAGNATION: Population diversity collapsed (entropy={entropy:.3f} < {self.entropy_threshold}). "
                    "Abandon local hill-climbing. Force distant structural crossover across divergent parents."
                )
                action = "crossover_distant"
            else:
                directive = (
                    f"SEARCH PLATEAU: Zero significant fitness gain over {stagnant_count} generations. "
                    "Pivot hypothesis from localized parameter tuning to fundamental algorithmic refactoring."
                )
                action = "mutate_macro"
            logger.warning("AVO Supervisor issued intervention: %s", directive)
        else:
            directive = f"Search progressing nominally (Fitness={curr_best:.4f}, Entropy={entropy:.3f}). Continue exploitation."
            action = "diversify"

        return SupervisorIntervention(
            stagnation_detected=stagnation_detected,
            stagnant_generations=stagnant_count,
            current_entropy=entropy,
            steering_directive=directive,
            recommended_action=action,
        )
