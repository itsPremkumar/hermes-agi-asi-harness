"""
Hermes AGI/ASI Harness — Adaptive Spatiotemporal Runtime Modes.

Inspired by DeepSeek Harness (dsh):
- RuntimeMode enum (REACTIVE, DEEP_REASON, ENDURANCE_CODE, SELF_EVOLVE)
- Dynamic environment configuration & tool whitelisting
"""

from .controller import (
    RuntimeMode,
    ModeConfig,
    ModeController,
)

__all__ = [
    "RuntimeMode",
    "ModeConfig",
    "ModeController",
]
