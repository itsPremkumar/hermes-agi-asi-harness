"""compute_scaling — re-export module."""
from . import logger, ComputeBudget, ComputeScalingController, ComputeScalingPlugin

__all__ = ["ComputeBudget", "ComputeScalingController", "ComputeScalingPlugin", "logger"]
