"""
HERMES INTELLIGENCE OS — CAUSAL MODEL & COUNTERFACTUAL SIMULATION
=================================================================
Models 'cause -> mechanism -> effect' relationships across environment components.
Supports Do-Calculus interventions: 'What would happen if we modify X?'
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("hermes.world_model.causal")


@dataclass
class CausalEdge:
    cause: str
    mechanism: str
    effect: str
    strength: float = 0.8  # Influence strength (0.0 to 1.0)
    confidence: float = 0.9
    evidence: list[str] = field(default_factory=list)


class CausalGraph:
    """Directed acyclic graph of causal relationships for counterfactual reasoning."""

    def __init__(self):
        self._nodes: set[str] = set()
        self._edges: list[CausalEdge] = []

    def add_relationship(
        self,
        cause: str,
        mechanism: str,
        effect: str,
        strength: float = 0.8,
        confidence: float = 0.9,
        evidence: Optional[list[str]] = None,
    ) -> CausalEdge:
        edge = CausalEdge(
            cause=cause,
            mechanism=mechanism,
            effect=effect,
            strength=strength,
            confidence=confidence,
            evidence=list(evidence or []),
        )
        self._nodes.add(cause)
        self._nodes.add(effect)
        self._edges.append(edge)
        return edge

    def get_effects_of(self, cause: str) -> list[CausalEdge]:
        return [e for e in self._edges if e.cause == cause]

    def get_causes_of(self, effect: str) -> list[CausalEdge]:
        return [e for e in self._edges if e.effect == effect]

    def simulate_intervention(self, target_node: str, intervention_value: Any) -> dict[str, Any]:
        """
        Simulate a counterfactual intervention (do(target_node = intervention_value)).
        Propagates effects downstream across the causal DAG.
        """
        outcomes: dict[str, Any] = {target_node: intervention_value}
        queue = [target_node]
        visited = set()

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            for edge in self.get_effects_of(current):
                effect_node = edge.effect
                # Estimate propagated change
                source_val = outcomes.get(current)
                predicted_effect = f"modified_by_{edge.mechanism}"
                outcomes[effect_node] = {
                    "predicted_state": predicted_effect,
                    "driven_by": current,
                    "mechanism": edge.mechanism,
                    "confidence": edge.confidence * edge.strength,
                }
                queue.append(effect_node)

        return {
            "intervention": {target_node: intervention_value},
            "downstream_impacts": outcomes,
            "impacted_nodes_count": len(outcomes) - 1,
        }

    def all_edges(self) -> list[CausalEdge]:
        return list(self._edges)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": list(self._nodes),
            "edges": [
                {
                    "cause": e.cause,
                    "mechanism": e.mechanism,
                    "effect": e.effect,
                    "strength": e.strength,
                    "confidence": e.confidence,
                }
                for e in self._edges
            ],
        }
