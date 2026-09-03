"""Self Model — tracks empirical capabilities."""

from __future__ import annotations

import time
from typing import Any


class SelfModel:
    """Tracks empirical capability: domain, confidence, success rate."""
    
    def __init__(self):
        self._capabilities: dict[str, dict[str, Any]] = {}
    
    def update(self, domain: str, success: bool, sample_count: int = 1) -> None:
        if domain not in self._capabilities:
            self._capabilities[domain] = {"successes": 0, "total": 0, "rate": 0.0}
        cap = self._capabilities[domain]
        cap["total"] += sample_count
        if success:
            cap["successes"] += sample_count
        cap["rate"] = cap["successes"] / cap["total"] if cap["total"] > 0 else 0.0
        cap["last_updated"] = time.time()
    
    def get(self, domain: str) -> dict[str, Any]:
        return self._capabilities.get(domain, {})
    
    def status(self) -> dict:
        return {"domains": len(self._capabilities), "capabilities": self._capabilities}
