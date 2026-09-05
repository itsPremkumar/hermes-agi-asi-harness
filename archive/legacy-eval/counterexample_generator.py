"""Counterexample Generator — find counterexamples to falsified properties."""

from __future__ import annotations

import itertools
import threading
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Counterexample:
    """A counterexample to a property."""
    id: str
    property_name: str
    values: dict[str, Any]
    description: str = ""
    severity: str = "high"  # low | medium | high | critical


class CounterexampleGenerator:
    """Generate counterexamples for falsified properties."""

    def __init__(self):
        self._lock = threading.RLock()
        self._counterexamples: dict[str, Counterexample] = {}
        self._counter = 0

    def generate(self, property_name: str, variables: list[str], constraints: dict[str, Any], max_attempts: int = 100) -> list[Counterexample]:
        """Generate counterexamples by searching for violating assignments."""
        with self._lock:
            results = []

            # Get domains for each variable
            domains = {}
            for var in variables:
                domain = constraints.get(f"{var}_domain", [0, 1, 2, -1, 100, -100])
                domains[var] = domain

            # Search for violating assignments
            for attempt in range(max_attempts):
                assignment = {}
                for var in variables:
                    import random
                    assignment[var] = random.choice(domains[var])

                # Check if this assignment violates the property
                if self._violates(property_name, assignment, constraints):
                    self._counter += 1
                    cex = Counterexample(
                        id=f"cex_{self._counter}",
                        property_name=property_name,
                        values=assignment,
                        description=f"Counterexample found: {property_name} violated with {assignment}",
                    )
                    self._counterexamples[cex.id] = cex
                    results.append(cex)

            return results

    def _violates(self, property_name: str, assignment: dict[str, Any], constraints: dict[str, Any]) -> bool:
        """Check if an assignment violates a property."""
        # Simple heuristic: check inequality violations
        if ">" in property_name:
            parts = property_name.split(">")
            if len(parts) == 2:
                left = assignment.get(parts[0].strip(), 0)
                right = assignment.get(parts[1].strip(), 0)
                if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                    return left <= right
        elif "<" in property_name:
            parts = property_name.split("<")
            if len(parts) == 2:
                left = assignment.get(parts[0].strip(), 0)
                right = assignment.get(parts[1].strip(), 0)
                if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                    return left >= right
        elif "==" in property_name:
            parts = property_name.split("==")
            if len(parts) == 2:
                left = assignment.get(parts[0].strip(), 0)
                right = assignment.get(parts[1].strip(), 0)
                return left != right

        # Default: no violation found
        return False

    def get(self, cex_id: str) -> Optional[Counterexample]:
        return self._counterexamples.get(cex_id)

    def get_all(self) -> list[Counterexample]:
        return list(self._counterexamples.values())

    def get_by_property(self, property_name: str) -> list[Counterexample]:
        return [c for c in self._counterexamples.values() if c.property_name == property_name]

    def clear(self) -> None:
        with self._lock:
            self._counterexamples.clear()
            self._counter = 0

    def count(self) -> int:
        return len(self._counterexamples)


__all__ = [
    "CounterexampleGenerator",
    "Counterexample",
]
