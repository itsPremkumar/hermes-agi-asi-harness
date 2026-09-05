"""Variation Operator — Generate → Evaluate → Revise cycle.

The core of AVO: the agent IS the variation operator.
Generates candidate solutions, evaluates them, and evolves better ones.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List


@dataclass
class Candidate:
    """A candidate solution."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    content: str = ""
    score: float = 0.0
    feedback: str = ""
    generation: int = 0
    parent_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class VariationOperator:
    """Generates and evolves candidate solutions."""

    def __init__(
        self,
        generator: Callable | None = None,
        evaluator: Callable | None = None,
        mutator: Callable | None = None,
        max_generations: int = 10,
        population_size: int = 5,
        elite_ratio: float = 0.2,
    ):
        self._generator = generator
        self._evaluator = evaluator
        self._mutator = mutator
        self._max_generations = max_generations
        self._population_size = population_size
        self._elite_ratio = elite_ratio
        self._history: List[List[Candidate]] = []

    def evolve(
        self,
        task: str,
        context: Dict[str, Any] | None = None,
    ) -> List[Candidate]:
        """Evolve solutions through multiple generations."""
        population = self._initialize(task, context)

        for gen in range(self._max_generations):
            # Evaluate
            for candidate in population:
                if candidate.score == 0.0:
                    candidate.score, candidate.feedback = self._evaluate_candidate(
                        candidate, task, context
                    )

            # Sort by score
            population.sort(key=lambda c: c.score, reverse=True)

            # Store generation
            self._history.append(population[:])

            # Check for completion
            if population[0].score >= 1.0:
                return population

            # Evolve next generation
            population = self._evolve_population(population, task, context, gen + 1)

        # Return final population
        population.sort(key=lambda c: c.score, reverse=True)
        return population

    def _initialize(
        self,
        task: str,
        context: Dict[str, Any] | None,
    ) -> List[Candidate]:
        """Initialize population with candidates."""
        population = []
        for i in range(self._population_size):
            if self._generator:
                content = self._generator(task, context, i)
            else:
                content = f"Candidate {i} for: {task}"
            population.append(Candidate(content=content, generation=0))
        return population

    def _evaluate_candidate(
        self,
        candidate: Candidate,
        task: str,
        context: Dict[str, Any] | None,
    ) -> tuple[float, str]:
        """Evaluate a candidate."""
        if self._evaluator:
            return self._evaluator(candidate, task, context)
        return 0.0, "No evaluator registered"

    def _evolve_population(
        self,
        population: List[Candidate],
        task: str,
        context: Dict[str, Any] | None,
        generation: int,
    ) -> List[Candidate]:
        """Create next generation."""
        elite_count = max(1, int(len(population) * self._elite_ratio))
        elites = population[:elite_count]

        new_population = elites[:]

        # Generate mutations
        while len(new_population) < self._population_size:
            parent = elites[len(new_population) % len(elites)]
            if self._mutator:
                content = self._mutator(parent, task, context, generation)
            else:
                content = parent.content + f" (mutated gen {generation})"
            new_population.append(Candidate(
                content=content,
                generation=generation,
                parent_id=parent.id,
            ))

        return new_population

    def get_history(self) -> List[List[Candidate]]:
        """Get evolution history."""
        return self._history.copy()

    def get_best(self) -> Candidate | None:
        """Get best candidate across all generations."""
        if not self._history:
            return None
        best = None
        for gen in self._history:
            if gen and (best is None or gen[0].score > best.score):
                best = gen[0]
        return best
