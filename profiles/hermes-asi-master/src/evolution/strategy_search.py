"""strategy_search.py — Systematic strategy space exploration.

This module implements systematic exploration of a strategy space using
multiple search algorithms: grid search, random search, evolutionary search,
and beam search. It finds optimal strategy configurations for given objectives.

Module API:
- StrategyConfig: a configuration point in strategy space
- SearchSpace: defines the space of strategies to explore
- StrategySearch: base class for search algorithms
- GridSearch: exhaustive grid search over parameter space
- RandomSearch: random sampling of the strategy space
- EvolutionarySearch: population-based evolutionary search
- BeamSearch: beam search over strategy sequences
- SearchResult: result of a search run
"""

from __future__ import annotations

import dataclasses
import random
import statistics
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclass
class StrategyConfig:
    """A single strategy configuration (point in search space)."""

    name: str
    params: dict[str, Any]
    score: float = 0.0
    metrics: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def get(self, key: str, default: Any = None) -> Any:
        return self.params.get(key, default)

    def with_score(self, score: float, metrics: dict[str, float] | None = None) -> "StrategyConfig":
        """Return a new config with score set."""
        new_metrics = dict(self.metrics)
        if metrics:
            new_metrics.update(metrics)
        return StrategyConfig(
            name=self.name,
            params=dict(self.params),
            score=score,
            metrics=new_metrics,
            metadata=dict(self.metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StrategyConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SearchResult:
    """Result of a search run."""

    algorithm: str
    best: StrategyConfig | None
    evaluated: list[StrategyConfig]
    total_evaluations: int
    duration: float
    converged: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def top_k(self, k: int = 5) -> list[StrategyConfig]:
        """Return top-k configs by score."""
        return sorted(self.evaluated, key=lambda c: c.score, reverse=True)[:k]

    def summary(self) -> dict[str, Any]:
        scores = [c.score for c in self.evaluated]
        return {
            "algorithm": self.algorithm,
            "total_evaluations": self.total_evaluations,
            "duration": self.duration,
            "converged": self.converged,
            "best_score": max(scores) if scores else 0.0,
            "worst_score": min(scores) if scores else 0.0,
            "avg_score": statistics.mean(scores) if scores else 0.0,
            "score_std": statistics.stdev(scores) if len(scores) >= 2 else 0.0,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "best": self.best.to_dict() if self.best else None,
            "evaluated": [c.to_dict() for c in self.evaluated],
            "total_evaluations": self.total_evaluations,
            "duration": self.duration,
            "converged": self.converged,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Search Space
# ---------------------------------------------------------------------------


class SearchSpace:
    """Defines the space of strategies to explore.

    Usage:
        space = SearchSpace()
        space.add_param("temperature", [0.1, 0.5, 0.9])
        space.add_param("max_tokens", [100, 500, 1000])
    """

    def __init__(self) -> None:
        self._params: dict[str, list[Any]] = {}

    def add_param(self, name: str, values: Sequence[Any]) -> "SearchSpace":
        """Add a parameter with its possible values."""
        self._params[name] = list(values)
        return self

    def param_names(self) -> list[str]:
        return list(self._params.keys())

    def param_values(self, name: str) -> list[Any]:
        return self._params.get(name, [])

    def size(self) -> int:
        """Total number of combinations (may be huge)."""
        if not self._params:
            return 0
        total = 1
        for values in self._params.values():
            total *= len(values)
        return total

    def sample(self, n: int, rng: random.Random | None = None) -> list[StrategyConfig]:
        """Sample n random configurations from the space."""
        rng = rng or random.Random()
        configs = []
        for i in range(n):
            params = {}
            for name, values in self._params.items():
                params[name] = rng.choice(values)
            configs.append(StrategyConfig(name=f"config-{i}", params=params))
        return configs

    def grid(self) -> list[StrategyConfig]:
        """Generate all configurations (exhaustive grid)."""
        if not self._params:
            return []

        names = list(self._params.keys())
        values_list = [self._params[n] for n in names]

        def _expand(idx: int, current: dict[str, Any]) -> list[dict[str, Any]]:
            if idx == len(names):
                return [dict(current)]
            results = []
            for v in values_list[idx]:
                current[names[idx]] = v
                results.extend(_expand(idx + 1, current))
            return results

        param_dicts = _expand(0, {})
        return [StrategyConfig(name=f"grid-{i}", params=p) for i, p in enumerate(param_dicts)]

    def neighbors(self, config: StrategyConfig, step_size: int = 1) -> list[StrategyConfig]:
        """Generate neighboring configurations by varying one parameter."""
        neighbors = []
        for name, values in self._params.items():
            current_val = config.params.get(name)
            if current_val is None:
                continue
            idx = values.index(current_val) if current_val in values else -1
            for delta in [-step_size, step_size]:
                new_idx = idx + delta
                if 0 <= new_idx < len(values):
                    new_params = dict(config.params)
                    new_params[name] = values[new_idx]
                    neighbors.append(
                        StrategyConfig(name=f"neighbor-{name}", params=new_params)
                    )
        return neighbors

    def to_dict(self) -> dict[str, Any]:
        return {"params": self._params}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SearchSpace":
        space = cls()
        for name, values in data.get("params", {}).items():
            space.add_param(name, values)
        return space


# ---------------------------------------------------------------------------
# Search Algorithms
# ---------------------------------------------------------------------------


class StrategySearch(ABC):
    """Base class for strategy search algorithms."""

    @abstractmethod
    def search(
        self,
        space: SearchSpace,
        evaluate: Callable[[StrategyConfig], StrategyConfig],
        **kwargs: Any,
    ) -> SearchResult:
        """Run search. Returns a SearchResult."""
        ...


class GridSearch(StrategySearch):
    """Exhaustive grid search over the parameter space."""

    def search(
        self,
        space: SearchSpace,
        evaluate: Callable[[StrategyConfig], StrategyConfig],
        max_evals: int | None = None,
        **kwargs: Any,
    ) -> SearchResult:
        """Evaluate all configurations in the grid."""
        start = time.time()
        configs = space.grid()
        if max_evals:
            configs = configs[:max_evals]

        evaluated = []
        best = None
        for cfg in configs:
            scored = evaluate(cfg)
            evaluated.append(scored)
            if best is None or scored.score > best.score:
                best = scored

        return SearchResult(
            algorithm="grid_search",
            best=best,
            evaluated=evaluated,
            total_evaluations=len(evaluated),
            duration=time.time() - start,
            converged=True,
        )


class RandomSearch(StrategySearch):
    """Random sampling of the strategy space."""

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def search(
        self,
        space: SearchSpace,
        evaluate: Callable[[StrategyConfig], StrategyConfig],
        n_iter: int = 20,
        **kwargs: Any,
    ) -> SearchResult:
        """Sample and evaluate n_iter random configurations."""
        start = time.time()
        configs = space.sample(n_iter, rng=self._rng)

        evaluated = []
        best = None
        for cfg in configs:
            scored = evaluate(cfg)
            evaluated.append(scored)
            if best is None or scored.score > best.score:
                best = scored

        return SearchResult(
            algorithm="random_search",
            best=best,
            evaluated=evaluated,
            total_evaluations=len(evaluated),
            duration=time.time() - start,
            converged=False,
        )


class EvolutionarySearch(StrategySearch):
    """Population-based evolutionary search.

    Uses tournament selection, crossover, and mutation to evolve a population
    of strategy configurations toward higher scores.
    """

    def __init__(
        self,
        seed: int | None = None,
        population_size: int = 20,
        mutation_rate: float = 0.2,
        crossover_rate: float = 0.5,
        elite_fraction: float = 0.2,
    ) -> None:
        self._rng = random.Random(seed)
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elite_fraction = elite_fraction

    def search(
        self,
        space: SearchSpace,
        evaluate: Callable[[StrategyConfig], StrategyConfig],
        n_generations: int = 10,
        **kwargs: Any,
    ) -> SearchResult:
        """Run evolutionary search."""
        start = time.time()
        all_evaluated: list[StrategyConfig] = []

        # Initialize population
        population = space.sample(self.population_size, rng=self._rng)
        population = [evaluate(cfg) for cfg in population]
        all_evaluated.extend(population)

        for gen in range(n_generations):
            # Sort by score (descending)
            population.sort(key=lambda c: c.score, reverse=True)

            # Elitism: keep top fraction
            n_elite = max(1, int(self.elite_fraction * len(population)))
            new_population = population[:n_elite]

            # Fill rest with offspring
            while len(new_population) < self.population_size:
                parent1 = self._tournament_select(population)
                if self._rng.random() < self.crossover_rate:
                    parent2 = self._tournament_select(population)
                    child = self._crossover(parent1, parent2)
                else:
                    child = StrategyConfig(
                        name=f"offspring-{gen}",
                        params=dict(parent1.params),
                    )
                if self._rng.random() < self.mutation_rate:
                    child = self._mutate(child, space)
                scored = evaluate(child)
                new_population.append(scored)
                all_evaluated.append(scored)

            population = new_population

        population.sort(key=lambda c: c.score, reverse=True)
        best = population[0] if population else None

        return SearchResult(
            algorithm="evolutionary_search",
            best=best,
            evaluated=all_evaluated,
            total_evaluations=len(all_evaluated),
            duration=time.time() - start,
            converged=False,
            metadata={"generations": n_generations, "final_best_score": best.score if best else 0.0},
        )

    def _tournament_select(self, population: list[StrategyConfig], k: int = 3) -> StrategyConfig:
        """Tournament selection."""
        candidates = self._rng.sample(population, min(k, len(population)))
        return max(candidates, key=lambda c: c.score)

    def _crossover(self, p1: StrategyConfig, p2: StrategyConfig) -> StrategyConfig:
        """Uniform crossover between two parents."""
        params = {}
        all_keys = set(p1.params.keys()) | set(p2.params.keys())
        for key in all_keys:
            if key in p1.params and key in p2.params:
                params[key] = self._rng.choice([p1.params[key], p2.params[key]])
            elif key in p1.params:
                params[key] = p1.params[key]
            else:
                params[key] = p2.params[key]
        return StrategyConfig(name="crossover", params=params)

    def _mutate(self, config: StrategyConfig, space: SearchSpace) -> StrategyConfig:
        """Mutate a random parameter."""
        params = dict(config.params)
        if not space.param_names():
            return config
        name = self._rng.choice(space.param_names())
        values = space.param_values(name)
        if values:
            params[name] = self._rng.choice(values)
        return StrategyConfig(name="mutated", params=params)


class BeamSearch(StrategySearch):
    """Beam search over strategy configurations.

    Maintains a beam of top-k configurations at each step, expanding each
    to neighbors and selecting the best.
    """

    def __init__(self, beam_width: int = 5) -> None:
        self.beam_width = beam_width

    def search(
        self,
        space: SearchSpace,
        evaluate: Callable[[StrategyConfig], StrategyConfig],
        n_steps: int = 5,
        initial: StrategyConfig | None = None,
        **kwargs: Any,
    ) -> SearchResult:
        """Run beam search."""
        start = time.time()
        all_evaluated: list[StrategyConfig] = []

        # Initialize beam
        if initial is not None:
            beam = [evaluate(initial)]
        else:
            beam = [evaluate(cfg) for cfg in space.sample(self.beam_width)]
        all_evaluated.extend(beam)

        for step in range(n_steps):
            # Expand each beam candidate
            candidates: list[StrategyConfig] = []
            for cfg in beam:
                neighbors = space.neighbors(cfg)
                for n in neighbors:
                    if not any(n.params == e.params for e in all_evaluated):
                        scored = evaluate(n)
                        candidates.append(scored)
                        all_evaluated.append(scored)

            if not candidates:
                break

            # Select top beam_width
            candidates.sort(key=lambda c: c.score, reverse=True)
            beam = candidates[: self.beam_width]

        all_evaluated.sort(key=lambda c: c.score, reverse=True)
        best = all_evaluated[0] if all_evaluated else None

        return SearchResult(
            algorithm="beam_search",
            best=best,
            evaluated=all_evaluated,
            total_evaluations=len(all_evaluated),
            duration=time.time() - start,
            converged=False,
            metadata={"steps": n_steps, "beam_width": self.beam_width},
        )


# ---------------------------------------------------------------------------
# Convenience runner
# ---------------------------------------------------------------------------


def run_search(
    algorithm: str,
    space: SearchSpace,
    evaluate: Callable[[StrategyConfig], StrategyConfig],
    **kwargs: Any,
) -> SearchResult:
    """Run a search algorithm by name.

    Args:
        algorithm: one of "grid", "random", "evolutionary", "beam"
        space: the search space
        evaluate: function that scores a StrategyConfig
        **kwargs: passed to the search algorithm
    """
    algorithms: dict[str, StrategySearch] = {
        "grid": GridSearch(),
        "random": RandomSearch(seed=kwargs.pop("seed", None)),
        "evolutionary": EvolutionarySearch(seed=kwargs.pop("seed", None)),
        "beam": BeamSearch(),
    }

    if algorithm not in algorithms:
        raise ValueError(f"Unknown algorithm: {algorithm}. Choose from {list(algorithms.keys())}")

    return algorithms[algorithm].search(space, evaluate, **kwargs)
