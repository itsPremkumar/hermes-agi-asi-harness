"""
HERMES — WATCHDOG (deadlock + memory + runaway guards)
=======================================================
Called each daemon tick + pre/post mission. Detects:
- waits-for cycles (A→B→C→A) across worker claims
- memory explosion (.hermes size / event buffer / queue depth)
- runaway (tool_calls / tokens over budget)
Actions: break cycle (requeue victim), freeze + forensic log, request stop.
Windows-safe: no signals, file-size based memory estimate.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("hermes.os.watchdog")


def find_cycle(waits: Dict[str, List[str]]) -> List[str]:
    WHITE, GRAY, BLACK = 0, 1, 2
    color: Dict[str, int] = {n: WHITE for n in waits}
    stack: List[str] = []

    def dfs(u: str) -> Optional[List[str]]:
        color[u] = GRAY
        stack.append(u)
        for v in waits.get(u, []):
            if v not in color:
                color[v] = WHITE
            if color[v] == GRAY:
                return stack[stack.index(v):] + [v]
            if color[v] == WHITE:
                hit = dfs(v)
                if hit:
                    return hit
        stack.pop()
        color[u] = BLACK
        return None

    for n in list(waits):
        if color[n] == WHITE:
            hit = dfs(n)
            if hit:
                return hit
    return []


class Watchdog:
    def __init__(self, workspace_root: str = ".", max_tool_calls: int = 200,
                 max_tokens: int = 1_000_000, max_hermes_mb: int = 2000,
                 max_queue: int = 500):
        self.workspace_root = workspace_root
        self.max_tool_calls = max_tool_calls
        self.max_tokens = max_tokens
        self.max_hermes_mb = max_hermes_mb
        self.max_queue = max_queue
        self._waits: Dict[str, List[str]] = {}
        self._incidents: List[Dict[str, Any]] = []

    # -- waits-for graph ------------------------------------------------
    def claim_waits(self, waiter: str, holders: List[str]) -> None:
        self._waits[waiter] = list(holders)

    def release(self, waiter: str) -> None:
        self._waits.pop(waiter, None)

    def check_deadlock(self) -> Dict[str, Any]:
        cycle = find_cycle(self._waits)
        if cycle:
            incident = {"type": "deadlock", "cycle": cycle, "ts": time.time(),
                        "action": f"break at {cycle[0]} (requeue victim)"}
            self._incidents.append(incident)
            self.release(cycle[0])
            logger.error("Watchdog deadlock %s", cycle)
            return {"deadlock": True, **incident}
        return {"deadlock": False}

    # -- resource guards -------------------------------------------------
    def hermes_mb(self) -> float:
        total = 0
        root = Path(self.workspace_root) / ".hermes"
        try:
            for p in root.rglob("*"):
                try:
                    if p.is_file():
                        total += p.stat().st_size
                except Exception:
                    pass
        except Exception:
            pass
        return round(total / 1e6, 2)

    def check_resources(self, tool_calls: int = 0, tokens: int = 0, queue_depth: int = 0) -> Dict[str, Any]:
        problems: List[str] = []
        if tool_calls > self.max_tool_calls:
            problems.append(f"tool_calls {tool_calls} > {self.max_tool_calls}")
        if tokens > self.max_tokens:
            problems.append(f"tokens {tokens} > {self.max_tokens}")
        if queue_depth > self.max_queue:
            problems.append(f"queue {queue_depth} > {self.max_queue}")
        mb = self.hermes_mb()
        if mb > self.max_hermes_mb:
            problems.append(f".hermes {mb}MB > {self.max_hermes_mb}MB")
        if problems:
            incident = {"type": "resource", "problems": problems, "ts": time.time(),
                        "action": "freeze new spawns, flush memory, request stop if critical"}
            self._incidents.append(incident)
            logger.error("Watchdog resources %s", problems)
            return {"ok": False, **incident, "hermes_mb": mb}
        return {"ok": True, "hermes_mb": mb}

    def check(self, tool_calls: int = 0, tokens: int = 0, queue_depth: int = 0) -> Dict[str, Any]:
        dl = self.check_deadlock()
        rs = self.check_resources(tool_calls, tokens, queue_depth)
        critical = bool(dl.get("deadlock")) or not rs.get("ok")
        if critical:
            self._forensic({"deadlock": dl, "resources": rs})
        return {"critical": critical, "deadlock": dl, "resources": rs}

    def _forensic(self, payload: Dict[str, Any]) -> str:
        try:
            d = Path(self.workspace_root) / ".hermes" / "forensics"
            d.mkdir(parents=True, exist_ok=True)
            p = d / f"watchdog-{int(time.time())}.json"
            p.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
            return str(p)
        except Exception as e:
            logger.debug("forensic failed: %s", e)
            return ""

    def incidents(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._incidents[-limit:]
