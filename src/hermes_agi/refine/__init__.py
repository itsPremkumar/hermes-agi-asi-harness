"""
Hermes AGI/ASI Harness — Continual Self-Refinement Package (/refine).

Inspired by Prime Agent:
- Post-session diagnostic analysis
- Automatic generation and persistence of learned rules and prompt constraints
"""

from .engine import (
    HarnessRefiner,
    RefinementReport,
)
from .harness_state import (
    HarnessEntry,
    HarnessKind,
    HarnessScope,
    HarnessStateManager,
    RefinementEvent,
)

__all__ = [
    "HarnessRefiner",
    "RefinementReport",
    "HarnessStateManager",
    "HarnessEntry",
    "RefinementEvent",
    "HarnessKind",
    "HarnessScope",
]
