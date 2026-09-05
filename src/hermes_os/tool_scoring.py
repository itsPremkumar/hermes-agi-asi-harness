"""
HERMES — TOOL SELECTION SCORING (Utility = outcome − cost − risk)
=================================================================
Per-tool scorecard persisted under .hermes/tool_scores.json:
tracks success_rate, avg_latency, avg_tokens, risk penalties from
safety verdicts; CapabilitySelector consumes scores to rank tools.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("hermes.os.tool_scoring")

_RISK_PENALTY = {"low": 0.0, "medium": 0.05, "high": 0.15, "critical": 0.35}


class ToolScorecard:
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root
        self._file = Path(workspace_root) / ".hermes" / "tool_scores.json"
        self._scores: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        try:
            if self._file.exists():
                self._scores = json.loads(self._file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.debug("tool scores load failed: %s", e)

    def _save(self) -> None:
        try:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            self._file.write_text(json.dumps(self._scores, indent=2), encoding="utf-8")
        except Exception:
            pass

    def record(
        self,
        tool: str,
        success: bool,
        latency_s: float = 0.0,
        tokens: int = 0,
        risk: str = "low",
        verdict: str = "allow",
    ) -> Dict[str, Any]:
        s = self._scores.get(tool, {"n": 0, "success": 0, "latency": 0.0, "tokens": 0})
        n = s["n"] + 1
        s["n"] = n
        s["success"] = s["success"] + (1 if success else 0)
        s["latency"] = round((s["latency"] * (n - 1) + float(latency_s)) / n, 3)
        s["tokens"] = int((s["tokens"] * (n - 1) + int(tokens)) / n)
        s["success_rate"] = round(s["success"] / n, 4)
        s["risk"] = risk
        s["verdict"] = verdict
        s["updated"] = time.time()
        self._scores[tool] = s
        self._save()
        return s

    def utility(self, tool: str, risk: str = "low", est_tokens: int = 100) -> float:
        """Expected utility in [−1,1]: success − cost − risk."""
        s = self._scores.get(tool)
        base = float(s["success_rate"]) if s else 0.5
        cost = min(0.3, est_tokens / 100000)
        latency_pen = min(0.1, float(s.get("latency", 0.0)) / 300) if s else 0.0
        risk_pen = _RISK_PENALTY.get(risk, 0.05)
        return round(base - cost - latency_pen - risk_pen, 4)

    def rank(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank candidate tool dicts {name, risk, est_tokens} by utility desc."""
        out = []
        for c in candidates:
            name = c.get("name", "")
            out.append(
                {**c, "utility": self.utility(name, c.get("risk", "low"), c.get("est_tokens", 100))}
            )
        out.sort(key=lambda x: x["utility"], reverse=True)
        return out

    def all(self) -> Dict[str, Any]:
        return dict(self._scores)
