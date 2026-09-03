"""
Hermes AGI/ASI Harness — NVIDIA AVO (Agentic Variation Operators) Package.

Implements autonomous evolutionary search where traditional fixed operators
are replaced by self-directed AI agents with:
- Lineage DAG Memory (ancestry, fitness deltas, compiler feedback)
- Domain Knowledge Base (hardware bounds & algorithmic patterns)
- Agentic Variation Operators (mutation & crossover with in-harness multi-turn repair)
- AVOSupervisor (anti-stagnation monitoring & diversity entropy steering)
"""

from .engine import AVOEvolutionEngine, AVOResult
from .knowledge_base import DomainKnowledgeBase
from .lineage import LineageDAG, LineageNode
from .operator import AgenticVariationOperator
from .supervisor import AVOSupervisor, SupervisorIntervention

__all__ = [
    "AVOEvolutionEngine",
    "AVOResult",
    "LineageDAG",
    "LineageNode",
    "DomainKnowledgeBase",
    "AgenticVariationOperator",
    "AVOSupervisor",
    "SupervisorIntervention",
]
