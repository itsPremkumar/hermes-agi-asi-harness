"""Hermes AGI/ASI Harness — Advanced AI Agent Runtime."""

from __future__ import annotations

__version__ = "2.0.0"

from .config import Config, load_config
from .exceptions import HarnessError, KernelError, PluginError, SafetyError, BenchmarkError

__all__ = [
    "Config",
    "load_config",
    "HarnessError",
    "KernelError",
    "PluginError",
    "SafetyError",
    "BenchmarkError",
]
