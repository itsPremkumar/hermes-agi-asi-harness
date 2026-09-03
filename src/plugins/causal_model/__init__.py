"""
Causal Model Plugin — Temporal and Causal World Modeling

Implements section 15 of the v7 spec:
- State(t-n) ... State(t) temporal storage
- Causal relations separate from correlation
- Counterfactual simulation
- "What happens if action X changes variable A?"
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CausalRelation:
    """A causal or correlational relation between variables."""
    id: str
    source: str
    target: str
    relation_type: str  # "causes", "correlates", "inhibits", "enables"
    strength: float  # 0-1
    evidence: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: float | None = None
    confidence: float = 0.5


@dataclass
class WorldStateSnapshot:
    """A snapshot of world state at a point in time."""
    timestamp: float
    state: dict[str, Any]
    source: str = "observed"  # observed, inferred, assumed, predicted
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CounterfactualSimulation:
    """A what-if simulation result."""
    id: str
    description: str
    original_state: dict[str, Any]
    intervention: dict[str, Any]
    predicted_outcome: dict[str, Any]
    confidence: float = 0.5
    created_at: float = field(default_factory=time.time)


class CausalModelEngine:
    """Temporal and causal world modeling engine."""

    def __init__(self):
        self._causal_relations: dict[str, CausalRelation] = {}
        self._temporal_states: dict[str, list[WorldStateSnapshot]] = {}
        self._variables: dict[str, Any] = {}
        self._counterfactuals: list[CounterfactualSimulation] = []

    def add_causal_relation(
        self,
        source: str,
        target: str,
        relation_type: str,
        strength: float = 0.5,
        evidence: list[str] | None = None,
    ) -> CausalRelation:
        """Add a causal or correlational relation."""
        relation = CausalRelation(
            id=str(uuid.uuid4()),
            source=source,
            target=target,
            relation_type=relation_type,
            strength=max(0.0, min(1.0, strength)),
            evidence=evidence or [],
        )
        self._causal_relations[relation.id] = relation
        logger.debug(f"Causal relation: {source} --{relation_type}--> {target}")
        return relation

    def record_state(self, variable: str, state: Any, source: str = "observed", confidence: float = 1.0):
        """Record a state snapshot for a variable over time."""
        if variable not in self._temporal_states:
            self._temporal_states[variable] = []
        
        snapshot = WorldStateSnapshot(
            timestamp=time.time(),
            state={variable: state},
            source=source,
            confidence=confidence,
        )
        self._temporal_states[variable].append(snapshot)
        self._variables[variable] = state
        
        # Keep only last 100 snapshots per variable
        if len(self._temporal_states[variable]) > 100:
            self._temporal_states[variable] = self._temporal_states[variable][-100:]

    def get_temporal_chain(self, variable: str, n: int = 5) -> list[WorldStateSnapshot]:
        """Get the last n state snapshots for a variable."""
        states = self._temporal_states.get(variable, [])
        return states[-n:]

    def get_causal_relations(self, variable: str | None = None, relation_type: str | None = None) -> list[CausalRelation]:
        """Get causal relations, optionally filtered."""
        results = list(self._causal_relations.values())
        if variable:
            results = [r for r in results if r.source == variable or r.target == variable]
        if relation_type:
            results = [r for r in results if r.relation_type == relation_type]
        return results

    def simulate_intervention(self, intervention: dict[str, Any], description: str = "") -> CounterfactualSimulation:
        """
        Simulate "What happens if we change variable A?"
        Uses causal graph to propagate effects.
        """
        # Build affected variables through causal chain
        affected = {}
        visited = set()
        queue = list(intervention.keys())
        
        while queue:
            var = queue.pop(0)
            if var in visited:
                continue
            visited.add(var)
            
            for rel in self._causal_relations.values():
                if rel.source == var and rel.target not in visited:
                    # Propagate effect
                    if var in intervention:
                        effect = intervention[var] * rel.strength
                        affected[var] = intervention[var]
                        # Simple linear propagation
                        current_val = self._variables.get(rel.target, 0)
                        if isinstance(current_val, (int, float)):
                            new_val = current_val + effect * 0.1
                            affected[rel.target] = new_val
                            queue.append(rel.target)
        
        sim = CounterfactualSimulation(
            id=str(uuid.uuid4()),
            description=description or f"Intervention on {list(intervention.keys())}",
            original_state=dict(self._variables),
            intervention=intervention,
            predicted_outcome=affected,
            confidence=0.5,  # Simple model = low confidence
        )
        self._counterfactuals.append(sim)
        return sim

    def get_downstream_effects(self, variable: str, max_depth: int = 3) -> dict[str, float]:
        """Get all downstream effects of a variable through causal chain."""
        effects = {}
        visited = set()
        queue = [(variable, 1.0, 0)]
        
        while queue:
            current, strength, depth = queue.pop(0)
            if depth >= max_depth or current in visited:
                continue
            visited.add(current)
            
            for rel in self._causal_relations.values():
                if rel.source == current and rel.target not in visited:
                    new_strength = strength * rel.strength
                    effects[rel.target] = max(effects.get(rel.target, 0), new_strength)
                    queue.append((rel.target, new_strength, depth + 1))
        
        return effects

    def detect_correlation_vs_causation(self, var_a: str, var_b: str) -> dict[str, Any]:
        """Analyze whether relation between A and B is causal or correlational."""
        a_states = self._temporal_states.get(var_a, [])
        b_states = self._temporal_states.get(var_b, [])
        
        if len(a_states) < 3 or len(b_states) < 3:
            return {"verdict": "insufficient_data", "confidence": 0.0}
        
        # Check for explicit causal relation
        causal = [r for r in self._causal_relations.values() 
                  if (r.source == var_a and r.target == var_b) or 
                     (r.source == var_b and r.target == var_a)]
        
        if causal:
            return {
                "verdict": "causal",
                "confidence": max(r.confidence for r in causal),
                "relations": [r.id for r in causal],
            }
        
        return {
            "verdict": "unknown",
            "confidence": 0.1,
            "note": "No explicit causal relation recorded",
        }

    def get_stats(self) -> dict[str, Any]:
        """Get engine statistics."""
        return {
            "causal_relations": len(self._causal_relations),
            "variables_tracked": len(self._variables),
            "temporal_chains": len(self._temporal_states),
            "counterfactuals_run": len(self._counterfactuals),
            "by_relation_type": {
                rtype: sum(1 for r in self._causal_relations.values() if r.relation_type == rtype)
                for rtype in {r.relation_type for r in self._causal_relations.values()}
            },
        }


class CausalModelPlugin:
    """Plugin wrapper for causal model engine."""

    def __init__(self):
        self.engine = CausalModelEngine()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {"status": "healthy", **self.engine.get_stats()}


async def create(kernel=None):
    plugin = CausalModelPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
