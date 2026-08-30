"""Performance Engineering Loop - Baseline to Profile to Hypothesize to Benchmark."""
from __future__ import annotations

import uuid
from typing import Any


class PerformanceLoop:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.experiments: list[dict[str, Any]] = []
    
    def run_experiment(self, baseline: float, candidate: float, workload: str) -> dict[str, Any]:
        improvement = (candidate - baseline) / max(baseline, 0.001)
        exp = {"baseline": baseline, "candidate": candidate, "workload": workload, "improvement": improvement}
        self.experiments.append(exp)
        return exp
    
    def get_state(self) -> dict[str, Any]:
        return {"experiments": len(self.experiments)}
