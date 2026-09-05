"""Predictive Caching Engine Plugin — Re-export module."""
from . import Predictive_cachePlugin, create

predictive_cache = Predictive_cachePlugin

__all__ = ["Predictive_cachePlugin", "create", "predictive_cache"]
