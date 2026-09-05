"""
Hermes AGI/ASI Harness — Deep Coding Package.
"""

from .loop import CodingResult, DeepCodingLoop
from .winjob import ProcessIsolationManager

__all__ = [
    "DeepCodingLoop",
    "CodingResult",
    "ProcessIsolationManager",
]
