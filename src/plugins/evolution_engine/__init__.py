#!/usr/bin/env python3
"""
Evolution Engine Plugin — Self-improvement through iterative optimization
=======================================================================
Features:
- Code mutation and evaluation
- Fitness-based selection
- Genetic algorithm for prompt/code optimization
- A/B testing of strategies
- Performance tracking
- Rollback on regression
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import logging
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("hermes_evolution_engine")

try:
    from core.runtime.plugin_base import PluginBase, PluginManifest, PluginPermissions, PluginState
    HAS_CORE = True
except ImportError:
    from enum import Enum
    
    class PluginState(str, Enum):
        REGISTERED = "registered"
        LOADED = "loaded"
        RUNNING = "running"
        PAUSED = "paused"
        ERROR = "error"
        UNLOADED = "unloaded"
    
    @dataclass
    class PluginPermissions:
        filesystem_read: str = "project"
        filesystem_write: str = "project"
        network_domains: list[str] = field(default_factory=list)
        shell_commands: list[str] = field(default_factory=list)
        secrets_access: str = "none"
        max_memory_mb: 512
        max_cpu_percent: 20
    
    @dataclass
    class PluginManifest:
        name: str = ""
        version: str = "1.0.0"
        description: str = ""
        license: str = "MIT"
        source: str = "internal"
        capabilities: list[str] = field(default_factory=list)
        cost: str = "free"
        permissions: PluginPermissions = field(default_factory=PluginPermissions)
        dependencies: list[str] = field(default_factory=list)
        path: Path | None = None
    
    class PluginBase:
        manifest: PluginManifest
        
        def __init__(self, manifest: PluginManifest = None, kernel: Any = None):
            self.manifest = manifest or PluginManifest()
            self.kernel = kernel
            self.state = PluginState.REGISTERED
        
        async def load(self) -> bool:
            self.state = PluginState.LOADED
            return True
        
        async def start(self) -> bool:
            self.state = PluginState.RUNNING
            return True
        
        async def stop(self) -> bool:
            self.state = PluginState.UNLOADED
            return True
    
    HAS_CORE = False


@dataclass
class Individual:
    """A candidate solution in the population."""
    id: str
    genome: Any  # Can be str (code), dict (params), etc.
    fitness: float = 0.0
    generation: int = 0
    parents: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvolutionConfig:
    """Configuration for evolution."""
    population_size: int = 10
    mutation_rate: float = 0.1
    crossover_rate: float = 0.5
    elite_count: int = 2
    max_generations: int = 20
    selection_pressure: float = 0.7
    mutation_scale: float = 0.5


class EvolutionEngine:
    """Genetic algorithm based evolution engine."""
    
    def __init__(self, config: EvolutionConfig = None):
        self.config = config or EvolutionConfig()
        self.population: list[Individual] = []
        self.generation = 0
        self.best_history: list[float] = []
        self.fitness_cache: dict[str, float] = {}
    
    def _hash_genome(self, genome: Any) -> str:
        """Hash a genome for caching."""
        if isinstance(genome, str):
            return hashlib.md5(genome.encode()).hexdigest()
        else:
            return hashlib.md5(str(genome).encode()).hexdigest()
    
    def initialize(self, seed_genomes: list[Any]):
        """Initialize population from seed genomes."""
        self.population = []
        for i, genome in enumerate(seed_genomes[:self.config.population_size]):
            ind = Individual(
                id=f"gen0_ind{i}",
                genome=genome,
                generation=0,
            )
            self.population.append(ind)
    
    async def evaluate(self, fitness_func: Callable[[Any], float]):
        """Evaluate fitness of all individuals."""
        for ind in self.population:
            genome_hash = self._hash_genome(ind.genome)
            if genome_hash in self.fitness_cache:
                ind.fitness = self.fitness_cache[genome_hash]
            else:
                try:
                    if asyncio.iscoroutinefunction(fitness_func):
                        fitness = await fitness_func(ind.genome)
                    else:
                        fitness = fitness_func(ind.genome)
                    ind.fitness = fitness
                    self.fitness_cache[genome_hash] = fitness
                except Exception as e:
                    logger.error(f"Fitness eval failed: {e}")
                    ind.fitness = float('-inf')
    
    def select_parents(self) -> list[Individual]:
        """Tournament selection."""
        selected = []
        population_sorted = sorted(self.population, key=lambda x: x.fitness, reverse=True)
        
        # Elitism
        for i in range(self.config.elite_count):
            if i < len(population_sorted):
                selected.append(population_sorted[i])
        
        # Tournament
        while len(selected) < self.config.population_size:
            tournament = random.sample(self.population, min(3, len(self.population)))
            winner = max(tournament, key=lambda x: x.fitness)
            selected.append(winner)
        
        return selected
    
    def mutate(self, genome: Any) -> Any:
        """Mutate a genome."""
        if isinstance(genome, str):
            # String mutation: random character changes
            chars = list(genome)
            for i in range(len(chars)):
                if random.random() < self.config.mutation_rate:
                    chars[i] = random.choice("abcdefghijklmnopqrstuvwxyz ")
            return "".join(chars)
        elif isinstance(genome, dict):
            # Dict mutation: change numeric values with an absolute-scale delta
            # (proportional deltas stall on small starting values / unbounded targets)
            new_genome = copy.deepcopy(genome)
            for key, value in new_genome.items():
                if isinstance(value, (int, float)) and random.random() < self.config.mutation_rate:
                    span = self.config.mutation_scale
                    delta = random.uniform(-span, span)
                    new_genome[key] = value + delta
            return new_genome
        elif isinstance(genome, list):
            # List mutation
            new_genome = copy.deepcopy(genome)
            for i in range(len(new_genome)):
                if random.random() < self.config.mutation_rate:
                    if isinstance(new_genome[i], (int, float)):
                        new_genome[i] += random.uniform(-0.1, 0.1)
            return new_genome
        else:
            return genome
    
    def crossover(self, parent1: Individual, parent2: Individual) -> Any:
        """Crossover two genomes."""
        if isinstance(parent1.genome, dict) and isinstance(parent2.genome, dict):
            child = {}
            for key in parent1.genome:
                if key in parent2.genome:
                    child[key] = random.choice([parent1.genome[key], parent2.genome[key]])
                else:
                    child[key] = parent1.genome[key]
            return child
        elif isinstance(parent1.genome, list) and isinstance(parent2.genome, list):
            mid = min(len(parent1.genome), len(parent2.genome)) // 2
            return parent1.genome[:mid] + parent2.genome[mid:]
        else:
            # Default: random selection
            return random.choice([parent1.genome, parent2.genome])
    
    async def evolve(self, fitness_func: Callable[[Any], float]) -> dict[str, Any]:
        """Run full evolution."""
        if not self.population:
            raise ValueError("Population not initialized")
        
        for generation in range(self.config.max_generations):
            self.generation = generation
            
            # Evaluate
            await self.evaluate(fitness_func)
            
            # Track best
            best = max(self.population, key=lambda x: x.fitness)
            self.best_history.append(best.fitness)
            
            # Select parents
            parents = self.select_parents()
            
            # Create next generation
            new_population = parents[:self.config.elite_count].copy()
            
            while len(new_population) < self.config.population_size:
                if random.random() < self.config.crossover_rate and len(parents) >= 2:
                    p1, p2 = random.sample(parents, 2)
                    child_genome = self.crossover(p1, p2)
                    # Mutate child
                    if random.random() < self.config.mutation_rate:
                        child_genome = self.mutate(child_genome)
                else:
                    parent = random.choice(parents)
                    child_genome = self.mutate(parent.genome)
                
                child = Individual(
                    id=f"gen{generation+1}_ind{len(new_population)}",
                    genome=child_genome,
                    generation=generation + 1,
                )
                new_population.append(child)
            
            self.population = new_population
            
            logger.info(f"Generation {generation}: best fitness = {best.fitness:.4f}")
        
        # Final evaluation
        await self.evaluate(fitness_func)
        best = max(self.population, key=lambda x: x.fitness)
        
        return {
            "success": True,
            "best_genome": best.genome,
            "best_fitness": best.fitness,
            "generations": self.config.max_generations,
            "fitness_history": self.best_history,
            "improvement": self.best_history[-1] - self.best_history[0] if self.best_history else 0,
        }
    
    def get_best(self) -> Individual | None:
        """Get the best individual."""
        if not self.population:
            return None
        return max(self.population, key=lambda x: x.fitness)


# ═══════════════════════════════════════════════════════════════════════════════════
# PLUGIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════════

class Plugin(PluginBase):
    """Evolution Engine Plugin"""
    
    def __init__(self):
        self.state = PluginState.REGISTERED
        self.manifest = PluginManifest(
            name="evolution_engine",
            version="1.0.0",
            description="Genetic algorithm based self-improvement with mutation, crossover, and fitness evaluation",
            license="MIT",
            source="internal",
            capabilities=["evolution", "optimization", "genetic_algorithm", "self_improvement"],
            cost="free",
            permissions=PluginPermissions(
                filesystem_read="workspace",
                filesystem_write="workspace",
                network_domains=[],
                shell_commands=[],
                secrets_access="none",
                max_memory_mb=512,
                max_cpu_percent=20,
            ),
        )
        self.engine: EvolutionEngine | None = None
    
    async def load(self) -> bool:
        self.engine = EvolutionEngine()
        self.state = PluginState.LOADED
        return True
    
    async def start(self) -> bool:
        if not self.engine:
            self.engine = EvolutionEngine()
        self.state = PluginState.RUNNING
        return True
    
    async def stop(self) -> bool:
        self.state = PluginState.UNLOADED
        return True
    
    async def health(self) -> dict[str, Any]:
        healthy = self.state in (PluginState.LOADED, PluginState.RUNNING)
        return {
            "status": "healthy" if healthy else "degraded",
            "plugin": self.manifest.name,
            "version": self.manifest.version,
            "state": self.state.value,
            "healthy": healthy,
            "ready": self.engine is not None,
            "generation": self.engine.generation if self.engine else 0,
        }
    
    # ── PUBLIC API ──────────────────────────────────────────────────────
    
    def configure(self, population_size: int = 10, mutation_rate: float = 0.1, 
                  crossover_rate: float = 0.5, max_generations: int = 20):
        """Configure evolution."""
        from plugins.evolution_engine import EvolutionConfig
        self.engine = EvolutionEngine(EvolutionConfig(
            population_size=population_size,
            mutation_rate=mutation_rate,
            crossover_rate=crossover_rate,
            max_generations=max_generations,
        ))
    
    def initialize(self, seed_genomes: list[Any]):
        self.engine.initialize(seed_genomes)
    
    async def evolve(self, fitness_func: Callable[[Any], float]) -> dict[str, Any]:
        return await self.engine.evolve(fitness_func)
    
    def get_best(self) -> Any | None:
        best = self.engine.get_best()
        return best.genome if best else None
    
    def get_fitness_history(self) -> list[float]:
        return self.engine.best_history
    
    def get_capabilities(self) -> list[str]:
        return self.manifest.capabilities

async def create(kernel: Any) -> Plugin:
    p = Plugin()
    await p.start()
    return p

