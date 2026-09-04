"""
HERMES INTELLIGENCE OS — MEMORY OPERATING SYSTEM (MEMORY OS)
============================================================
The unified Memory Operating System coordinating all 8 memory subsystems
and the persistent Trajectory Archive.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .subsystems import (
    CapabilityMemory,
    DecisionMemory,
    EpisodicMemory,
    FailureMemory,
    ProceduralMemory,
    SemanticMemory,
    WorkingMemory,
    WorldStateMemory,
)
from .trajectories import Trajectory, TrajectoryArchive, TrajectoryStep

logger = logging.getLogger("hermes.memory")


class MemoryOS:
    """The central Memory Operating System."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root
        self.semantic = SemanticMemory()
        self.episodic = EpisodicMemory()
        self.procedural = ProceduralMemory()
        self.working = WorkingMemory()
        self.failure = FailureMemory()
        self.decision = DecisionMemory()
        self.world_state = WorldStateMemory()
        self.capability = CapabilityMemory()
        self.trajectories = TrajectoryArchive(workspace_root=workspace_root)

    def stats(self) -> dict[str, Any]:
        return {
            "semantic_entries": self.semantic.count(),
            "episodic_events": self.episodic.count(),
            "procedures": self.procedural.count(),
            "failures_indexed": self.failure.count(),
            "decisions_recorded": len(self.decision.all_decisions()),
            "capabilities_tracked": len(self.capability.all_capabilities()),
            "archived_trajectories": self.trajectories.count(),
        }
