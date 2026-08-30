
"""
AVO-style Supervisor — the plateau monitor that redirects the search.

Extracted & enhanced from agx-harness-main:
- supervisor.py: trajectory_summary, supervisor_redirect, _parse, _apply

When the kernel's stagnation supervisor returns 'replan', this module asks
the brain's 'supervise' role to review the trajectory + memory and return a
strategic redirect.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

VALID_STRATEGIES = {"argmax", "top_k", "epsilon_greedy", "softmax", "pareto_per_task"}

_FIELD_RE = re.compile(r"(?im)^\s*(DIRECTIVE|STRATEGY|SUBGOALS)\s*:\s*(.*)$")


def trajectory_summary(state: dict) -> str:
    """Compact view of the search trajectory for the supervisor."""
    nodes = list(state.get("tree", {}).values())
    recent = []
    for n in nodes[-8:]:
        recent.append("- {} [{}] score={}".format(
            (n.get("hypothesis") or "")[:60],
            n.get("status"), n.get("score")))
    return (
        "round=%s best_score=%s stagnation=%s frontier=%d nodes=%d\n"
        "recent attempts:\n%s"
        % (state.get("round_no"), state.get("best_score"),
           state.get("stagnation"), len(state.get("frontier", []) or []),
           len(nodes), "\n".join(recent) or "(none)"))


def _parse(out: str) -> dict:
    res = {"directive": "", "strategy": None, "subgoals": None}
    for m in _FIELD_RE.finditer(out or ""):
        key, val = m.group(1).lower(), m.group(2).strip()
        if key == "directive":
            res["directive"] = val
        elif key == "strategy":
            res["strategy"] = val if val.lower() != "keep" else None
        elif key == "subgoals":
            res["subgoals"] = None if val.lower() == "keep" else val
    return res


def _apply(state: dict, parsed: dict) -> None:
    if parsed["strategy"] and parsed["strategy"] in VALID_STRATEGIES:
        state["strategy"] = parsed["strategy"]
    if parsed["subgoals"]:
        parts = [p.strip() for p in parsed["subgoals"].split(";") if p.strip()]
        state["subgoals"] = [{"id": "sg%d" % i, "desc": p}
                             for i, p in enumerate(parts, 1)]
    state.setdefault("shared_state", {})["supervisor_directive"] = parsed["directive"] or ""


def supervisor_redirect(state: dict, brain) -> str | None:
    """Ask the supervisor role to redirect; apply STRATEGY/SUBGOALS/DIRECTIVE."""
    if not hasattr(brain, "supervise"):
        return None
    summary = trajectory_summary(state)
    mem = state.get("shared_state", {}).get("memory", {})
    mem_str = "\n".join(f"- {k}: {v}" for k, v in mem.items()) if isinstance(mem, dict) else str(mem)
    try:
        out = brain.supervise(
            state["goal"], state.get("goal_criterion", ""), summary, mem_str)
    except Exception:
        return None
    if not out:
        return None
    parsed = _parse(out)
    _apply(state, parsed)
    return parsed["directive"] or None
