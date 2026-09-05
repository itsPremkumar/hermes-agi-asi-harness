"""
Hermes AGI/ASI Harness — Dynamic Causal Graph & Counterfactual Simulator.

Constructs dependency causal graphs and answers counterfactual queries:
"What if component X is modified? What downstream services break, and what
regression risks are introduced before any filesystem changes occur?"
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("hermes.causal.engine")


@dataclass
class CausalImpactReport:
    """Predictive analysis of downstream ripple effects and blast radius."""
    target_module: str
    blast_radius_count: int
    direct_dependents: list[str]
    transitive_dependents: list[str]
    risk_level: str  # low, medium, high, critical
    recommended_test_suites: list[str]
    counterfactual_prediction: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_module": self.target_module,
            "blast_radius_count": self.blast_radius_count,
            "direct_dependents": self.direct_dependents,
            "transitive_dependents": self.transitive_dependents,
            "risk_level": self.risk_level,
            "recommended_test_suites": self.recommended_test_suites,
            "counterfactual_prediction": self.counterfactual_prediction,
        }


class CausalImpactSimulator:
    """
    Predictive causal simulation engine for workspace mutations.
    Constructs an AST-based dependency graph and forecasts regression hazards.
    """

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()
        self._graph: dict[str, set[str]] = {}  # module -> set of modules it imports
        self._reverse_graph: dict[str, set[str]] = {}  # module -> set of modules that import it
        self._scan_workspace()

    def _scan_workspace(self) -> None:
        """Scan Python files in workspace to construct causal import graph."""
        py_files = list(self.workspace_root.glob("src/**/*.py"))
        for p in py_files:
            rel_name = p.stem
            self._graph[rel_name] = set()
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self._graph[rel_name].add(alias.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        self._graph[rel_name].add(node.module.split(".")[0])
            except Exception:
                continue

        # Invert graph for downstream impact analysis
        for mod, deps in self._graph.items():
            for dep in deps:
                if dep not in self._reverse_graph:
                    self._reverse_graph[dep] = set()
                self._reverse_graph[dep].add(mod)

    def simulate_mutation(self, target_module: str) -> CausalImpactReport:
        """Forecast the downstream blast radius if target_module is altered."""
        mod_key = Path(target_module).stem

        # 1. Find direct dependents
        direct = sorted(list(self._reverse_graph.get(mod_key, set())))

        # 2. Transitive BFS traversal
        visited = set(direct)
        queue = list(direct)
        while queue:
            curr = queue.pop(0)
            for neighbor in self._reverse_graph.get(curr, set()):
                if neighbor not in visited and neighbor != mod_key:
                    visited.add(neighbor)
                    queue.append(neighbor)

        transitive = sorted(list(visited - set(direct)))
        blast_radius = len(direct) + len(transitive)

        # 3. Categorize risk level
        if blast_radius == 0:
            risk = "low"
            pred = f"Isolated change: '{mod_key}' has zero downstream dependents. Low regression risk."
        elif blast_radius < 5:
            risk = "medium"
            pred = f"Moderate blast radius: '{mod_key}' affects {blast_radius} modules directly or transitively."
        else:
            risk = "high"
            pred = f"High-risk core modification: '{mod_key}' affects {blast_radius} modules across the harness."

        tests = [f"tests/test_{d}.py" for d in direct[:5]]
        if "kernel" in mod_key or "nodes" in mod_key or "state" in mod_key:
            tests.append("tests/test_kernel_integration.py")
            tests.append("tests/test_runtime.py")

        return CausalImpactReport(
            target_module=mod_key,
            blast_radius_count=blast_radius,
            direct_dependents=direct,
            transitive_dependents=transitive,
            risk_level=risk,
            recommended_test_suites=tests,
            counterfactual_prediction=pred,
        )
