"""Benchmarks package — evaluation suite."""

from __future__ import annotations

from .runner import BENCHMARK_REGISTRY, BenchmarkRunner

__all__ = ["BenchmarkRunner", "BENCHMARK_REGISTRY"]
