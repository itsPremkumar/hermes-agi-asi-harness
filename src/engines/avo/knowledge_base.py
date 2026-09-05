"""
Hermes AGI/ASI Harness — NVIDIA AVO Domain Knowledge Base.

Stores domain-specific technical invariants, hardware constraints, and proven
algorithmic patterns that the agent consults before proposing variations.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("hermes.avo.knowledge_base")


class DomainKnowledgeBase:
    """Repository of domain constraints, hardware limits, and algorithmic patterns."""

    def __init__(self):
        self._rules: dict[str, list[str]] = self._default_knowledge()

    def _default_knowledge(self) -> dict[str, list[str]]:
        return {
            "runtime_optimization": [
                "Memory Coalescing: Ensure contiguous array reads to maximize L1/L2 cache hit rate.",
                "Zero-Copy Slicing: Prefer memoryview or itertools generators over list duplicates.",
                "Algorithmic Complexity: Prioritize reducing time complexity (O(N) vs O(N^2)) before micro-optimizations.",
                "Thread Safety: Protect shared mutating state using fine-grained locks or lock-free atomics.",
                "Bounded Queues: Always set maxlen on buffers to eliminate unbounded memory growth.",
            ],
            "arc_agi_3": [
                "Color Permutation Invariance: Treat color indices as categorical labels, not cardinal magnitudes.",
                "Spatial Symmetries: Test for 90-degree rotations, horizontal/vertical reflections, and diagonal transpositions.",
                "Connected Components: Group contiguous non-background cells into persistent object entities.",
                "Boundary Gravity: Check if objects align to bounding borders or converge toward centroids.",
                "Topological Invariants: Preserve enclosure, hole count, and Euler characteristics under transformation.",
            ],
            "hardware_constraints": [
                "L1 Cache Line: Typically 64 bytes; align struct layouts to avoid false sharing.",
                "Context Window Bounds: Compact historical prompts to avoid quadratic attention degradation.",
                "Subprocess I/O: Always enforce UTF-8 decoding with explicit timeout limits.",
            ],
        }

    def get_rules(self, domain: str) -> list[str]:
        """Retrieve all rules for a given domain."""
        return self._rules.get(domain, [])

    def query(self, context_keywords: list[str], max_results: int = 4) -> list[str]:
        """Retrieve the most relevant rules matching context keywords."""
        matches: list[tuple[int, str]] = []
        kw_set = {k.lower() for k in context_keywords}

        for domain, rules in self._rules.items():
            for rule in rules:
                score = sum(1 for kw in kw_set if kw in rule.lower())
                if score > 0:
                    matches.append((score, rule))

        matches.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in matches[:max_results]] if matches else self._rules.get("runtime_optimization", [])[:max_results]

    def add_rule(self, domain: str, rule: str) -> None:
        """Dynamically learn and record a new domain rule."""
        if domain not in self._rules:
            self._rules[domain] = []
        if rule not in self._rules[domain]:
            self._rules[domain].append(rule)
