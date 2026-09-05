"""
Git-Backed Lineage DAG + Stagnation Supervisor — NVIDIA AVO Pattern
====================================================================
"""

from .lineage import (
    GitLineageDAG,
    LineageNode,
    LineageNodeType,
    ScoreVector,
    StagnationSupervisor,
    AVOEvolutionEngine,
    example_scoring_fn,
)

__all__ = [
    "GitLineageDAG",
    "LineageNode",
    "LineageNodeType",
    "ScoreVector",
    "StagnationSupervisor",
    "AVOEvolutionEngine",
    "example_scoring_fn",
]