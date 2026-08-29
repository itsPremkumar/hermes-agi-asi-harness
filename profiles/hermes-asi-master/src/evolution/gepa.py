"""gepa.py — Prompt/Strategy Evolution.

GEPA = Generate variants → Evaluate (benchmark) → Pareto compare → Select candidate → Safety validate → Promote.

This module implements the evolution loop for agent strategies (prompts, plans,
policies). It generates variants of a base strategy, benchmarks them, uses
Pareto optimization to find the best trade-off (score vs. cost vs. latency),
validates the winner for safety, and promotes it.

Module API:
- Strategy: a named prompt/strategy template
- Variant: a mutated version of a Strategy
- EvolutionStep: record of one evolution cycle
- GEPA: the evolution engine
- SafetyValidator: checks a strategy for prohibited content
- Pareto: Pareto frontier computation
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import random
import re
import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclass
class Strategy:
    """A named strategy/prompt template."""

    name: str
    template: str
    version: int = 1
    score: float = 0.0
    cost: float = 0.0
    latency: float = 0.0
    promoted: bool = False
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def hash(self) -> str:
        payload = json.dumps({"name": self.name, "template": self.template}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Strategy":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Variant:
    """A mutated version of a strategy."""

    parent_name: str
    template: str
    mutation: str  # description of what was changed
    score: float = 0.0
    cost: float = 0.0
    latency: float = 0.0
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def strategy(self) -> Strategy:
        return Strategy(
            name=self.parent_name,
            template=self.template,
            score=self.score,
            cost=self.cost,
            latency=self.latency,
        )

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Variant":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class EvolutionStep:
    """Record of one evolution cycle."""

    step_id: int
    parent_strategy: str
    parent_score: float
    variants_generated: int
    candidates_on_frontier: int
    selected_template: str
    selected_score: float
    selected_cost: float
    selected_latency: float
    safety_passed: bool
    promoted: bool
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvolutionStep":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Mutation operators
# ---------------------------------------------------------------------------


class Mutator:
    """Generate variants of a strategy template.

    Each mutation operator produces a slightly different template.
    """

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def generate(
        self,
        template: str,
        n: int,
        operators: Sequence[str] | None = None,
    ) -> list[Variant]:
        """Generate n variants of the given template."""
        ops = list(operators) if operators else ["reword", "restructure", "add_detail", "remove_detail", "invert"]
        variants: list[Variant] = []
        for _ in range(n):
            op = self._rng.choice(ops)
            mutated = self._apply(op, template)
            if mutated != template:
                variants.append(
                    Variant(
                        parent_name="",
                        template=mutated,
                        mutation=op,
                    )
                )
        return variants

    def _apply(self, op: str, template: str) -> str:
        if op == "reword":
            return self._reword(template)
        if op == "restructure":
            return self._restructure(template)
        if op == "add_detail":
            return self._add_detail(template)
        if op == "remove_detail":
            return self._remove_detail(template)
        if op == "invert":
            return self._invert(template)
        return template

    def _reword(self, template: str) -> str:
        """Replace common words with synonyms."""
        replacements = {
            "must": "should",
            "should": "must",
            "always": "typically",
            "never": "rarely",
            "ensure": "verify",
            "verify": "ensure",
            "create": "generate",
            "generate": "create",
            "analyze": "examine",
            "examine": "analyze",
            "use": "utilize",
            "utilize": "use",
            "help": "assist",
            "assist": "help",
        }
        result = template
        for old, new in replacements.items():
            if old in result.lower() and self._rng.random() > 0.5:
                result = re.sub(r"\b" + old + r"\b", new, result, count=1, flags=re.IGNORECASE)
        return result

    def _restructure(self, template: str) -> str:
        """Reorder sentences or clauses."""
        sentences = re.split(r"(?<=[.!?])\s+", template)
        if len(sentences) <= 1:
            return template
        if self._rng.random() > 0.5 and len(sentences) >= 2:
            i = self._rng.randint(0, len(sentences) - 2)
            sentences[i], sentences[i + 1] = sentences[i + 1], sentences[i]
        return " ".join(sentences)

    def _add_detail(self, template: str) -> str:
        """Add a clarifying phrase."""
        additions = [
            " Be thorough.",
            " Consider edge cases.",
            " Provide reasoning.",
            " Use examples where helpful.",
            " Be concise but complete.",
        ]
        addition = self._rng.choice(additions)
        return template + addition

    def _remove_detail(self, template: str) -> str:
        """Remove a sentence or clause."""
        sentences = re.split(r"(?<=[.!?])\s+", template)
        if len(sentences) <= 1:
            return template
        idx = self._rng.randint(0, len(sentences) - 1)
        sentences.pop(idx)
        return " ".join(sentences)

    def _invert(self, template: str) -> str:
        """Negate or invert a key instruction."""
        inversions = [
            ("do not", "do"),
            ("do", "do not"),
            ("always", "do not always"),
            ("never", "do not never"),
            ("include", "exclude"),
            ("exclude", "include"),
        ]
        result = template
        for old, new in inversions:
            if old in result.lower():
                result = re.sub(r"\b" + old + r"\b", new, result, count=1, flags=re.IGNORECASE)
                break
        return result


# ---------------------------------------------------------------------------
# Pareto frontier
# ---------------------------------------------------------------------------


@dataclass
class ParetoPoint:
    """A point on the Pareto frontier."""

    variant: Variant
    objectives: dict[str, float]  # objective name -> value (higher is better)


class Pareto:
    """Compute the Pareto frontier for multi-objective optimization.

    Objectives are assumed to be maximized. For cost/latency, pass negative
    values so that lower cost/latency = higher objective value.
    """

    @staticmethod
    def frontier(
        variants: Sequence[Variant],
        objectives: Sequence[str] | None = None,
    ) -> list[ParetoPoint]:
        """Return the Pareto-optimal subset of variants.

        Objectives default to ["score", "neg_cost", "neg_latency"].
        """
        if not variants:
            return []

        if objectives is None:
            objectives = ["score", "neg_cost", "neg_latency"]

        points: list[ParetoPoint] = []
        for v in variants:
            obj: dict[str, float] = {}
            for name in objectives:
                if name == "score":
                    obj[name] = v.score
                elif name == "neg_cost":
                    obj[name] = -v.cost
                elif name == "neg_latency":
                    obj[name] = -v.latency
                elif name == "cost":
                    obj[name] = v.cost
                elif name == "latency":
                    obj[name] = v.latency
                else:
                    obj[name] = v.metadata.get(name, 0.0)
            points.append(ParetoPoint(variant=v, objectives=obj))

        # Non-dominated sorting
        result: list[ParetoPoint] = []
        for p in points:
            dominated = False
            for q in points:
                if p is q:
                    continue
                if Pareto._dominates(q.objectives, p.objectives):
                    dominated = True
                    break
            if not dominated:
                result.append(p)

        return result

    @staticmethod
    def _dominates(a: dict[str, float], b: dict[str, float]) -> bool:
        """True if a dominates b (a >= b on all, a > b on at least one)."""
        all_keys = set(a.keys()) | set(b.keys())
        at_least_one_better = False
        for k in all_keys:
            va = a.get(k, float("-inf"))
            vb = b.get(k, float("-inf"))
            if va < vb:
                return False
            if va > vb:
                at_least_one_better = True
        return at_least_one_better

    @staticmethod
    def select_best(
        points: Sequence[ParetoPoint],
        weights: dict[str, float] | None = None,
    ) -> ParetoPoint | None:
        """Select the best point from the frontier using weighted sum."""
        if not points:
            return None
        if not weights:
            weights = {"score": 1.0, "neg_cost": 0.5, "neg_latency": 0.3}

        best: ParetoPoint | None = None
        best_score = float("-inf")
        for p in points:
            score = sum(p.objectives.get(k, 0.0) * w for k, w in weights.items())
            if score > best_score:
                best_score = score
                best = p
        return best


# ---------------------------------------------------------------------------
# Safety validator
# ---------------------------------------------------------------------------


class SafetyValidator:
    """Check a strategy for prohibited content before promotion.

    Rules:
    - No prohibited keywords (e.g., "ignore safety", "bypass")
    - Template length within bounds
    - No injection patterns
    """

    DEFAULT_PROHIBITED = [
        "ignore safety",
        "bypass",
        "override safety",
        "disable guard",
        "ignore previous",
        "disregard policy",
        "jailbreak",
        "sudo",
        "rm -rf",
    ]

    def __init__(
        self,
        prohibited: Sequence[str] | None = None,
        min_length: int = 10,
        max_length: int = 10000,
    ) -> None:
        self.prohibited = list(prohibited) if prohibited else self.DEFAULT_PROHIBITED
        self.min_length = min_length
        self.max_length = max_length

    def validate(self, template: str) -> tuple[bool, list[str]]:
        """Validate a template. Returns (passed, list_of_violations)."""
        violations: list[str] = []
        lower = template.lower()

        for phrase in self.prohibited:
            if phrase in lower:
                violations.append(f"prohibited phrase: {phrase}")

        if len(template) < self.min_length:
            violations.append(f"template too short: {len(template)} < {self.min_length}")
        if len(template) > self.max_length:
            violations.append(f"template too long: {len(template)} > {self.max_length}")

        # Check for injection patterns
        if re.search(r"<\s*script", lower):
            violations.append("potential script injection")
        if re.search(r"\{\{.*\}\}", template):
            violations.append("potential template injection")

        return len(violations) == 0, violations


# ---------------------------------------------------------------------------
# GEPA engine
# ---------------------------------------------------------------------------


class GEPA:
    """Generate → Evaluate → Pareto → Select → Safety → Promote.

    Usage:
        gepa = GEPA()
        step = gepa.evolve(
            base_strategy=my_strategy,
            benchmark=my_benchmark,
            runner=my_runner,
            n_variants=10,
        )
    """

    def __init__(
        self,
        mutator: Mutator | None = None,
        validator: SafetyValidator | None = None,
        seed: int | None = None,
    ) -> None:
        self.mutator = mutator or Mutator(seed=seed)
        self.validator = validator or SafetyValidator()
        self.history: list[EvolutionStep] = []
        self._step_counter = 0

    def evolve(
        self,
        base_strategy: Strategy,
        benchmark: Any,  # evolution.benchmark.Benchmark
        runner: Callable[[Any], Any],
        n_variants: int = 10,
        objectives: Sequence[str] | None = None,
        weights: dict[str, float] | None = None,
        promotion_threshold: float = 0.0,
    ) -> EvolutionStep:
        """Run one evolution cycle.

        1. Generate variants of the base strategy
        2. Benchmark each variant
        3. Compute Pareto frontier
        4. Select best candidate
        5. Safety validate
        6. Promote if safe and better than base
        """
        self._step_counter += 1

        # 1. Generate variants
        variants = self.mutator.generate(base_strategy.template, n_variants)

        # 2. Benchmark each variant
        for v in variants:
            result = benchmark.run(runner=runner)
            # Use the benchmark's aggregate score for the variant
            v.score = result.avg_score
            v.cost = result.total_cost
            v.latency = result.avg_latency

        # 3. Pareto frontier
        frontier_points = Pareto.frontier(variants, objectives=objectives)

        # 4. Select best
        best_point = Pareto.select_best(frontier_points, weights=weights)

        if best_point is None:
            # No valid candidate — return a no-op step
            return EvolutionStep(
                step_id=self._step_counter,
                parent_strategy=base_strategy.name,
                parent_score=base_strategy.score,
                variants_generated=len(variants),
                candidates_on_frontier=0,
                selected_template=base_strategy.template,
                selected_score=base_strategy.score,
                selected_cost=base_strategy.cost,
                selected_latency=base_strategy.latency,
                safety_passed=True,
                promoted=False,
            )

        best_variant = best_point.variant

        # 5. Safety validate
        safety_passed, violations = self.validator.validate(best_variant.template)

        # 6. Promote if safe and better
        promoted = False
        if safety_passed and best_variant.score >= base_strategy.score + promotion_threshold:
            promoted = True
            base_strategy.template = best_variant.template
            base_strategy.score = best_variant.score
            base_strategy.cost = best_variant.cost
            base_strategy.latency = best_variant.latency
            base_strategy.version += 1
            base_strategy.promoted = True

        step = EvolutionStep(
            step_id=self._step_counter,
            parent_strategy=base_strategy.name,
            parent_score=base_strategy.score,
            variants_generated=len(variants),
            candidates_on_frontier=len(frontier_points),
            selected_template=best_variant.template,
            selected_score=best_variant.score,
            selected_cost=best_variant.cost,
            selected_latency=best_variant.latency,
            safety_passed=safety_passed,
            promoted=promoted,
        )
        self.history.append(step)
        return step

    def summary(self) -> dict[str, Any]:
        if not self.history:
            return {"steps": 0, "promotions": 0}
        promotions = sum(1 for s in self.history if s.promoted)
        return {
            "steps": len(self.history),
            "promotions": promotions,
            "promotion_rate": promotions / len(self.history),
            "latest_score": self.history[-1].selected_score,
        }
