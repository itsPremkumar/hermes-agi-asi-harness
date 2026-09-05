"""
HERMES — ARCHITECTURE SEARCH ENGINE (param sweeps + Pareto + A/B)
==================================================================
SearchSpace over planner/memory/routing/verification params;
run_search(grid|random|evolutionary) with benchmark_fn(config)->(score,cost,latency);
pareto_front() on (score↑, cost↓, latency↓); ab_compare(A,B) with BaselineTracker.
"""

from __future__ import annotations

import itertools
import logging
import random
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple

logger = logging.getLogger("hermes.os.arch_search")


@dataclass
class ArchCandidate:
    cand_id: str
    config: Dict[str, Any]
    score: float = 0.0
    cost: float = 0.0
    latency: float = 0.0
    status: str = "pending"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cand_id": self.cand_id,
            "config": self.config,
            "score": self.score,
            "cost": self.cost,
            "latency": self.latency,
            "status": self.status,
        }


class SearchSpace:
    def __init__(self):
        self._params: Dict[str, List[Any]] = {}

    def add_param(self, name: str, values: List[Any]) -> None:
        self._params[name] = list(values)

    def configs(self, mode: str = "grid", limit: int = 16, seed: int = 7) -> List[Dict[str, Any]]:
        keys = list(self._params.keys())
        if not keys:
            return [{}]
        if mode == "grid":
            out = [
                dict(zip(keys, combo))
                for combo in itertools.product(*[self._params[k] for k in keys])
            ]
            return out[:limit]
        rng = random.Random(seed)
        out = []
        for _ in range(limit):
            out.append({k: rng.choice(self._params[k]) for k in keys})
        return out


def pareto_front(cands: List[ArchCandidate]) -> List[ArchCandidate]:
    front = []
    for c in cands:
        dominated = any(
            o.score >= c.score
            and o.cost <= c.cost
            and o.latency <= c.latency
            and (o.score > c.score or o.cost < c.cost or o.latency < c.latency)
            for o in cands
        )
        if not dominated:
            front.append(c)
    return front


class ArchSearchEngine:
    def run_search(
        self,
        space: SearchSpace,
        benchmark_fn: Callable[[Dict[str, Any]], Tuple[float, float, float]],
        mode: str = "grid",
        limit: int = 12,
    ) -> Dict[str, Any]:
        cands = [
            ArchCandidate(cand_id=f"arch-{uuid.uuid4().hex[:6]}", config=cfg)
            for cfg in space.configs(mode, limit)
        ]
        for c in cands:
            try:
                s, co, la = benchmark_fn(c.config)
                c.score, c.cost, c.latency, c.status = float(s), float(co), float(la), "scored"
            except Exception as e:
                c.status = f"failed: {e}"
        scored = [c for c in cands if c.status == "scored"]
        front = pareto_front(scored)
        best = max(scored, key=lambda c: c.score) if scored else None
        return {
            "candidates": [c.to_dict() for c in cands],
            "pareto": [c.to_dict() for c in front],
            "best": best.to_dict() if best else None,
        }

    def ab_compare(
        self,
        a: Dict[str, Any],
        b: Dict[str, Any],
        benchmark_fn: Callable[[Dict[str, Any]], Tuple[float, float, float]],
        baseline_tracker: Any = None,
    ) -> Dict[str, Any]:
        ra = self.run_search(_FixedSpace(a), benchmark_fn, limit=1)
        rb = self.run_search(_FixedSpace(b), benchmark_fn, limit=1)
        sa = ra["candidates"][0]["score"] if ra["candidates"] else 0.0
        sb = rb["candidates"][0]["score"] if rb["candidates"] else 0.0
        winner = "A" if sa >= sb else "B"
        reg = None
        if baseline_tracker is not None:
            try:
                reg = baseline_tracker.check_regression(max(sa, sb))
            except Exception as e:
                reg = {"error": str(e)}
        return {"score_a": sa, "score_b": sb, "winner": winner, "regression": reg}


class _FixedSpace(SearchSpace):
    def __init__(self, cfg: Dict[str, Any]):
        super().__init__()
        self._cfg = cfg

    def configs(self, mode: str = "grid", limit: int = 16, seed: int = 7) -> List[Dict[str, Any]]:
        return [dict(self._cfg)]
