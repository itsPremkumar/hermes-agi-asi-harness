"""Core exceptions for Hermes AGI."""

from __future__ import annotations


class HarnessError(Exception):
    """Base exception for all harness errors."""
    pass


class KernelError(HarnessError):
    """Error in the kernel."""
    pass


class PluginError(HarnessError):
    """Error in a plugin."""
    pass


class SafetyError(HarnessError):
    """Safety violation."""
    pass


class BenchmarkError(HarnessError):
    """Benchmark error."""
    pass


class ConfigError(HarnessError):
    """Configuration error."""
    pass


class IntegrationError(HarnessError):
    """Integration error."""
    pass
