"""AVO (Agentic Variation Operators) Engine — per NVIDIA arXiv:2603.24517.

Implements the autonomous evolutionary search architecture where the agent
IS the variation operator: observe → reason → plan → implement → test →
evaluate → revise, with persistent memory, lineage tracking, a correctness
gate, matches-or-improves commit policy, and a Supervisor for stagnation
detection and strategy redirection.

Reference: https://arxiv.org/abs/2603.24517
"""
from __future__ import annotations

from .main_agent import MainAgent, Observation, Plan, Candidate, EvaluationResult
from .memory import AVOMemory, MemoryEntry
from .lineage import Lineage, VersionRecord
from .supervisor import Supervisor, StagnationSignal
from .correctness_gate import CorrectnessGate, GateResult
from .engine import AVOEngine, AVOConfig

__all__ = [
    "AVOConfig",
    "AVOEngine",
    "AVOMemory",
    "Candidate",
    "CorrectnessGate",
    "EvaluationResult",
    "GateResult",
    "Lineage",
    "MainAgent",
    "MemoryEntry",
    "Observation",
    "Plan",
    "StagnationSignal",
    "Supervisor",
    "VersionRecord",
]
