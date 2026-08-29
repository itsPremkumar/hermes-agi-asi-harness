
"""
Frontier Strategies — which committed branch tip to extend next.

Extracted & enhanced from agx-harness-main:
- frontier.py: argmax, top_k, epsilon_greedy, softmax, pareto_per_task, select_next_parent

Ported from evo's Frontier tab.
"""

from __future__ import annotations

import logging
import math
import random
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

StrategyFn = Callable[[dict], Optional[str]]


def _scored_tips(state: dict) -> List[str]:
    """Frontier nodes that exist and carry a score."""
    out = []
    for nid in state["frontier"]:
        n = state["tree"].get(nid)
        if n is not None and n["score"] is not None:
            out.append(nid)
    return out


def argmax(state: dict) -> Optional[str]:
    """Pick the best-scoring tip."""
    tips = _scored_tips(state)
    if not tips:
        return None
    return max(tips, key=lambda nid: (
        state["tree"][nid]["score"] if state["metric_direction"] == "maximize"
        else -float(state["tree"][nid]["score"] or 0.0)))


def top_k(state: dict, k: int = 2) -> Optional[str]:
    """Round-robin among top-k tips."""
    tips = _scored_tips(state)
    if not tips:
        return None
    ranked = sorted(tips, key=lambda nid: (
        -(state["tree"][nid]["score"] or 0.0)
        if state["metric_direction"] == "maximize"
        else (state["tree"][nid]["score"] or 0.0)))
    idx = state["round_no"] % min(k, len(ranked))
    return ranked[idx]


def epsilon_greedy(state: dict, eps: float = 0.3) -> Optional[str]:
    """Exploit best, explore with probability eps."""
    best = argmax(state)
    if best is None:
        return None
    rng = random.Random(state["rng_seed"] * 100003 + state["round_no"])
    if rng.random() < eps and len(_scored_tips(state)) > 1:
        others = [t for t in _scored_tips(state) if t != best]
        return rng.choice(others)
    return best


def softmax(state: dict, temperature: float = 0.5) -> Optional[str]:
    """Softmax sampling over tips."""
    tips = _scored_tips(state)
    if not tips:
        return None
    if len(tips) == 1:
        return tips[0]
    scores = [float(state["tree"][t]["score"] or 0.0) for t in tips]
    m = max(scores)
    exps = [math.exp((s - m) / temperature) for s in scores]
    total = sum(exps)
    probs = [e / total for e in exps]
    rng = random.Random(state["rng_seed"] * 7919 + state["round_no"])
    r, acc = rng.random(), 0.0
    for nid, p in zip(tips, probs):
        acc += p
        if r <= acc:
            return nid
    return tips[-1]


def pareto_per_task(state: dict) -> Optional[str]:
    """Keep specialists the aggregate hides (GEPA-style)."""
    tips = _scored_tips(state)
    if not tips:
        return None
    by_op: Dict[str, List[str]] = {}
    for nid in tips:
        op = state["tree"][nid].get("operator", "default").split(":")[0]
        by_op.setdefault(op, []).append(nid)
    best_per_op: Dict[str, str] = {}
    for op, nids in by_op.items():
        best_per_op[op] = max(nids, key=lambda nid: (
            state["tree"][nid]["score"]
            if state["metric_direction"] == "maximize"
            else -float(state["tree"][nid]["score"] or 0.0)))
    ops = sorted(best_per_op)
    return best_per_op[ops[state["round_no"] % len(ops)]]


STRATEGIES: Dict[str, StrategyFn] = {
    "argmax": argmax,
    "top_k": top_k,
    "epsilon_greedy": epsilon_greedy,
    "softmax": softmax,
    "pareto_per_task": pareto_per_task,
}


def select_next_parent(state: dict) -> Optional[str]:
    """Select the next parent node to extend."""
    fn = STRATEGIES.get(state["strategy"], argmax)
    pick = fn(state)
    if pick is None:
        # fall back to any gated-pass node not yet extended
        passed = [nid for nid, n in state["tree"].items()
                  if n.get("status") in ("committed", "evaluated")]
        extended = {state["tree"][c]["parent"]
                    for c in state["tree"]
                    if state["tree"][c]["parent"]}
        remaining = [n for n in passed if n not in extended]
        if remaining:
            return sorted(remaining)[0]
    return pick
