
"""
Governance — the three law gates inherited from hermes-harness-plugins.

Extracted & enhanced from agx-harness-main:
- governance.py: plan_hash, check_plan, require_goal, checklist_veto, supervise, round_budget_ok

Exit codes:
  4  plan drift: plan file changed without re-approval
  6  completion checklist veto: "complete" claimed with unproven items
  7  goal required: no user goal recorded
"""

from __future__ import annotations

import hashlib
import json
import logging

logger = logging.getLogger(__name__)

# Governance exit codes
EXIT_PLAN_DRIFT = 4
EXIT_CHECKLIST_VETO = 6
EXIT_GOAL_REQUIRED = 7

STAGNATION_LIMIT = 5


def plan_hash(plan_md: str) -> str:
    """Hash a plan text for drift detection."""
    return hashlib.sha256(plan_md.encode("utf-8")).hexdigest()[:16]


def check_plan(state: dict, approved_hash: str) -> tuple[bool, int]:
    """Exit 4 if current plan text hash != approved hash."""
    cur = state.get("plan_hash", "")
    if not cur or not approved_hash:
        return True, 0
    if cur != approved_hash:
        return False, EXIT_PLAN_DRIFT
    return True, 0


def require_goal(goal: str) -> tuple[bool, int]:
    """Exit 7 if empty/placeholder goal."""
    if not goal or not goal.strip() or goal.strip().lower() in {"todo", "tbd"}:
        return False, EXIT_GOAL_REQUIRED
    return True, 0


def checklist_veto(checklist: list[dict[str, str]]) -> tuple[bool, int]:
    """Every item must carry proof=pass to declare COMPLETE. Exit 6 otherwise."""
    for item in checklist:
        if item.get("proof") != "pass":
            return False, EXIT_CHECKLIST_VETO
    return True, 0


def supervise(state: dict) -> str | None:
    """Returns an action for the kernel: None | 'replan' | 'await_human'."""
    if state["stagnation"] >= STAGNATION_LIMIT:
        return "await_human"
    if state["stagnation"] >= max(2, STAGNATION_LIMIT // 2):
        # mid-stagnation: force strategy rotation before giving up
        order = ["argmax", "top_k", "epsilon_greedy", "softmax", "pareto_per_task"]
        idx = order.index(state["strategy"]) if state["strategy"] in order else 0
        state["strategy"] = order[(idx + 1) % len(order)]
        return "replan"
    return None


def round_budget_ok(state: dict, elapsed_min: float) -> bool:
    """Check if we're within budget."""
    b = state["budget"]
    if state["round_no"] >= b["max_rounds"]:
        return False
    if elapsed_min > float(b["wall_clock_min"]):
        return False
    return len(state["tree"]) < b["max_nodes"]


def trend_converged(state: dict, window: int = 5, min_delta: float = 1e-9) -> bool:
    """Statistical convergence: best score flat across the last window rounds."""
    scores = [n.get("score") for n in state["tree"].values()
              if n.get("status") in ("committed", "evaluated")
              and n.get("score") is not None]
    if len(scores) < window:
        return False
    recent = scores[-window:]
    return max(recent) - min(recent) <= min_delta


def dump_state_safely(state: dict) -> str:
    """JSON string for lineage ledger; never includes secrets by construction."""
    return json.dumps(state, indent=2, sort_keys=True)


import logging
