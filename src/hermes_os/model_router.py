"""
HERMES — MODEL ROUTER + ENSEMBLE (portfolio with measured history)
==================================================================
Roles: reasoning / coding / fast / vision / judge / embedding.
Each entry tracks success_rate, avg_latency, avg_cost, calibration.
route() picks max utility; ensemble() runs N models + judge vote.
Offline-safe: deterministic fallback to registered order.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("hermes.os.model_router")


@dataclass
class ModelEntry:
    model_id: str
    role: str = "fast"  # reasoning | coding | fast | vision | judge | embedding
    quality: float = 0.7
    cost_per_1k: float = 0.002
    success_rate: float = 0.5
    invocations: int = 0
    avg_latency_s: float = 5.0

    def to_dict(self) -> Dict[str, Any]:
        return {"model_id": self.model_id, "role": self.role, "quality": self.quality,
                "cost_per_1k": self.cost_per_1k, "success_rate": self.success_rate,
                "invocations": self.invocations, "avg_latency_s": self.avg_latency_s}


class ModelPortfolio:
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root
        self._file = Path(workspace_root) / ".hermes" / "model_portfolio.json"
        self._models: Dict[str, ModelEntry] = {}
        self._register_defaults()
        self._load()

    def _register_defaults(self) -> None:
        for m in (ModelEntry("hermes_managed", "reasoning", quality=0.90, cost_per_1k=0.0, avg_latency_s=15.0),
                  ModelEntry("hermes_local", "coding", quality=0.82, cost_per_1k=0.0, avg_latency_s=8.0),
                  ModelEntry("frontier_reasoner", "reasoning", quality=0.95, cost_per_1k=0.01, avg_latency_s=20.0),
                  ModelEntry("coding_model", "coding", quality=0.88, cost_per_1k=0.006, avg_latency_s=12.0),
                  ModelEntry("fast_executor", "fast", quality=0.70, cost_per_1k=0.001, avg_latency_s=2.0),
                  ModelEntry("judge_model", "judge", quality=0.90, cost_per_1k=0.008, avg_latency_s=10.0)):
            self._models[m.model_id] = m

    def _hermes_up(self) -> bool:
        try:
            from .hermes_llm import hermes_local_available
            return hermes_local_available()
        except Exception:
            return False

    def _load(self) -> None:
        try:
            if self._file.exists():
                for mid, d in json.loads(self._file.read_text(encoding="utf-8")).items():
                    if mid in self._models:
                        for k, v in d.items():
                            setattr(self._models[mid], k, v)
                    else:
                        self._models[mid] = ModelEntry(**d)
        except Exception as e:
            logger.debug("portfolio load failed: %s", e)

    def _save(self) -> None:
        try:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            self._file.write_text(json.dumps({m: e.to_dict() for m, e in self._models.items()}, indent=2), encoding="utf-8")
        except Exception:
            pass

    def register(self, entry: ModelEntry) -> None:
        self._models[entry.model_id] = entry
        self._save()

    def record(self, model_id: str, success: bool, latency_s: float = 0.0) -> None:
        m = self._models.get(model_id)
        if not m:
            return
        n = m.invocations + 1
        m.success_rate = round((m.success_rate * m.invocations + (1.0 if success else 0.0)) / n, 4)
        m.avg_latency_s = round((m.avg_latency_s * m.invocations + latency_s) / n, 2)
        m.invocations = n
        self._save()

    def route(self, task_kind: str = "general", budget: str = "balanced") -> ModelEntry:
        """Pick max utility: quality*success − cost − latency (budget shifts weights).

        Hermes-first: when a local Hermes tier was recently probed up, prefer the
        zero-cost Hermes entry for the matching role.
        """
        hermes_up = self._hermes_up()
        if hermes_up:
            prefer = {"reasoning": "hermes_managed", "coding": "hermes_local",
                      "general": "hermes_managed"}.get(task_kind)
            if prefer and prefer in self._models:
                return self._models[prefer]
        role_hint = {"reasoning": "reasoning", "coding": "coding", "vision": "vision",
                     "judge": "judge", "fast": "fast"}.get(task_kind, "")
        pool = {mid: m for mid, m in self._models.items()
                if hermes_up or not mid.startswith("hermes_")}
        if not pool:
            pool = dict(self._models)
        cands = [m for m in pool.values() if not role_hint or m.role in (role_hint, "fast")]
        if not cands:
            cands = list(pool.values())
        if budget == "cheap":
            cands.sort(key=lambda m: (m.cost_per_1k, -m.success_rate))
            return cands[0]
        if budget == "quality":
            cands.sort(key=lambda m: (-m.quality * max(0.2, m.success_rate), m.cost_per_1k))
            return cands[0]
        scored = sorted(cands, key=lambda m: (m.quality * max(0.2, m.success_rate)
                                              - m.cost_per_1k * 10 - m.avg_latency_s / 100), reverse=True)
        return scored[0] if scored else self._models["fast_executor"]

    def ensemble(self, candidates: List[str], judge_fn: Optional[Callable[[List[str]], str]] = None,
                 outputs: Optional[List[str]] = None) -> Dict[str, Any]:
        """Cross-model vote. judge_fn picks winner from outputs; fallback = majority/longest."""
        outs = outputs or []
        if judge_fn is not None:
            try:
                winner = judge_fn(outs)
                return {"winner": winner, "method": "judge", "n": len(outs)}
            except Exception as e:
                logger.debug("ensemble judge failed: %s", e)
        if not outs:
            return {"winner": "", "method": "empty", "n": 0}
        # Majority vote, tie → longest (most evidence)
        from collections import Counter
        votes = Counter(outs)
        top, count = votes.most_common(1)[0]
        if count > 1:
            return {"winner": top, "method": "majority", "n": len(outs)}
        winner = max(outs, key=len)
        return {"winner": winner, "method": "longest_fallback", "n": len(outs)}

    def calibration_report(self) -> Dict[str, Any]:
        return {mid: {"success_rate": m.success_rate, "invocations": m.invocations,
                      "avg_latency_s": m.avg_latency_s, "role": m.role}
                for mid, m in self._models.items()}
