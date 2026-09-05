"""AVO (Agentic Variation Operators) Engine — per NVIDIA arXiv:2603.24517.

Implements the autonomous evolutionary search architecture where the agent
IS the variation operator: observe → reason → plan → implement → test →
evaluate → revise, with persistent memory, lineage tracking, a correctness
gate, matches-or-improves commit policy, and a Supervisor for stagnation
detection and strategy redirection.

Reference: https://arxiv.org/abs/2603.24517
"""
from __future__ import annotations

from .correctness_gate import CorrectnessGate, GateResult
from .engine import AVOConfig, AVOEngine
from .lineage import Lineage, VersionRecord
from .main_agent import Candidate, EvaluationResult, MainAgent, Observation, Plan
from .memory import AVOMemory, MemoryEntry
from .supervisor import StagnationSignal, Supervisor

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
