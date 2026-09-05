"""
Hermes Unified Package
======================
Exposes the main submodules:
- hermes.os: Hermes Intelligence OS (v8 Final Architecture)
- hermes.agi: Hermes AGI/ASI Harness (Unified AI Agent Runtime)
"""

from .os import HermesIntelligenceOS
from .agi import Harness, Config, load_config

__version__ = "2.0.0"

__all__ = [
    "HermesIntelligenceOS",
    "Harness",
    "Config",
    "load_config",
    "os",
    "agi",
]