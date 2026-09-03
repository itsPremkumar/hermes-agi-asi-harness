"""
Hermes AGI/ASI Harness — Autonomous Overnight Endurance Engine.

Inspired by gnhf ("Good Night, Have Fun"):
- Clean Git Working Tree Validation
- Branch & Worktree Isolation
- Atomic Commits on Success
- Hard Reset (`git reset --hard`) on Failure
- Shared `notes.md` Memory Compaction
- 3-Consecutive Failure Circuit Breakers
- Exit Diff Summary & Review Commands
"""

from .controller import (
    OvernightConfig,
    OvernightLoopController,
    OvernightSummary,
)
from .git_manager import GitManager
from .notes_curator import NotesCurator

__all__ = [
    "OvernightConfig",
    "OvernightLoopController",
    "OvernightSummary",
    "GitManager",
    "NotesCurator",
]
