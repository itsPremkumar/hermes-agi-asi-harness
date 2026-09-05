"""Hermes ASI Master — Phase 8: Evolution Engine.

Controlled self-improvement layer. Builds on Phase 7 learning.

Modules:
- gepa: prompt/strategy evolution (generate variants → benchmark → Pareto compare → select → safety validate → promote)
- benchmarks: run task suites, measure score/latency/cost/failure rate, track baselines
- strategy_search: search over planning strategies (grid, random, evolutionary, beam)
- evolution_loop: observe weakness → hypothesis → sandbox → benchmark → safety gate → promote/rollback
- plugin: plugin system for pluggable evolution modules
- approval: human approval gate for Level 10 modifications
"""

__version__ = "1.0.0"
__all__ = [
    "gepa",
    "benchmarks",
    "strategy_search",
    "evolution_loop",
    "plugin",
    "approval",
]
