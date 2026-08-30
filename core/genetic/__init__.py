#!/usr/bin/env python3
"""
HERMES AGI/ASI HARNESS v7.0 — GENETIC ALGORITHM EVOLUTION
===========================================================
Prompt mutation, crossover, fitness evaluation, selection mechanisms.
"""

from __future__ import annotations

import json
import logging
import random
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes_genetic")


@dataclass
class Individual:
    """An individual in the population."""
    individual_id: str
    genes: dict[str, Any]
    fitness: float = 0.0
    generation: int = 0
    parent_ids: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class GeneticEvolution:
    """Genetic algorithm evolution engine."""
    
    def __init__(self, population_size: int = 50, mutation_rate: float = 0.1):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self._population: list[Individual] = []
        self._generation = 0
        self._best_fitness = 0.0
    
    def initialize_population(self, gene_template: dict[str, Any]) -> list[Individual]:
        """Initialize population with random genes."""
        self._population = []
        for _ in range(self.population_size):
            genes = {}
            for key, value in gene_template.items():
                if isinstance(value, list):
                    genes[key] = random.choice(value)
                elif isinstance(value, tuple) and len(value) == 2:
                    genes[key] = random.uniform(value[0], value[1])
                else:
                    genes[key] = value
            
            individual = Individual(
                individual_id=str(uuid.uuid4()),
                genes=genes,
                generation=self._generation
            )
            self._population.append(individual)
        
        return self._population
    
    def evaluate_fitness(self, individual: Individual, fitness_fn: Callable) -> float:
        """Evaluate fitness of an individual."""
        try:
            fitness = fitness_fn(individual.genes)
            individual.fitness = fitness
            return fitness
        except Exception as e:
            logger.error("Fitness evaluation error: %s", e)
            return 0.0
    
    def selection(self, method: str = "tournament", tournament_size: int = 3) -> Individual:
        """Select an individual."""
        if method == "tournament":
            tournament = random.sample(self._population, min(tournament_size, len(self._population)))
            return max(tournament, key=lambda i: i.fitness)
        elif method == "roulette":
            total_fitness = sum(i.fitness for i in self._population)
            if total_fitness == 0:
                return random.choice(self._population)
            pick = random.uniform(0, total_fitness)
            current = 0
            for individual in self._population:
                current += individual.fitness
                if current >= pick:
                    return individual
            return self._population[-1]
        else:
            return max(self._population, key=lambda i: i.fitness)
    
    def crossover(self, parent1: Individual, parent2: Individual) -> Individual:
        """Crossover two parents to create offspring."""
        child_genes = {}
        for key in parent1.genes:
            if random.random() < 0.5:
                child_genes[key] = parent1.genes[key]
            else:
                child_genes[key] = parent2.genes.get(key, parent1.genes[key])
        
        return Individual(
            individual_id=str(uuid.uuid4()),
            genes=child_genes,
            generation=self._generation,
            parent_ids=[parent1.individual_id, parent2.individual_id]
        )
    
    def mutate(self, individual: Individual, gene_template: dict[str, Any]) -> Individual:
        """Mutate an individual."""
        for key in individual.genes:
            if random.random() < self.mutation_rate:
                if isinstance(gene_template.get(key), list):
                    individual.genes[key] = random.choice(gene_template[key])
                elif isinstance(gene_template.get(key), tuple) and len(gene_template[key]) == 2:
                    individual.genes[key] = random.uniform(gene_template[key][0], gene_template[key][1])
        
        return individual
    
    async def evolve(self, fitness_fn: Callable, gene_template: dict[str, Any],
                     generations: int = 10) -> Individual:
        """Run evolution for specified generations."""
        if not self._population:
            self.initialize_population(gene_template)
        
        for gen in range(generations):
            self._generation = gen
            
            # Evaluate fitness
            for individual in self._population:
                self.evaluate_fitness(individual, fitness_fn)
            
            # Sort by fitness
            self._population.sort(key=lambda i: i.fitness, reverse=True)
            
            # Update best
            self._best_fitness = max(self._best_fitness, self._population[0].fitness)
            
            # Create next generation
            new_population = self._population[:5]  # Elitism
            
            while len(new_population) < self.population_size:
                parent1 = self.selection()
                parent2 = self.selection()
                child = self.crossover(parent1, parent2)
                child = self.mutate(child, gene_template)
                new_population.append(child)
            
            self._population = new_population
        
        return self._population[0]
    
    async def health(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "generation": self._generation,
            "population_size": len(self._population),
            "best_fitness": self._best_fitness
        }
