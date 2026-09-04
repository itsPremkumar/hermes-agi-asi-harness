"""
HERMES MEMORY — ECONOMIC LEDGER (token / cost accounting)
=========================================================
Tracks token burn + estimated cost per mission/worker for P16 budgets
and continuous-operation guardrails. JSONL persisted under .hermes/memory/.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_PRICE_PER_1K = 0.002


class EconomicLedger:
    def __init__(self, workspace_root: str = ".", price_per_1k: float = DEFAULT_PRICE_PER_1K):
        self.workspace_root = workspace_root
        self.price_per_1k = price_per_1k
        self._file = Path(workspace_root) / ".hermes" / "memory" / "economic_ledger.jsonl"
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self._entries: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        try:
            if self._file.exists():
                for line in self._file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line:
                        self._entries.append(json.loads(line))
        except Exception:
            pass

    def record(self, mission_id: str, tokens: int, runtime: str = "", workers: int = 0) -> Dict[str, Any]:
        entry = {"ts": time.time(), "mission_id": mission_id, "tokens": int(tokens),
                 "cost_usd": round(int(tokens) / 1000 * self.price_per_1k, 6),
                 "runtime": runtime, "workers": workers}
        self._entries.append(entry)
        try:
            with open(self._file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass
        return entry

    def totals(self, last_n: int = 100) -> Dict[str, Any]:
        window = self._entries[-last_n:]
        return {"missions": len(window), "tokens": sum(e.get("tokens", 0) for e in window),
                "cost_usd": round(sum(e.get("cost_usd", 0.0) for e in window), 6)}
