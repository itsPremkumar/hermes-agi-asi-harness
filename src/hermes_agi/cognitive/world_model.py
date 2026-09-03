"""World Model — maintains WORLD_STATE."""

from __future__ import annotations

import time
from typing import Any


class WorldModel:
    """Maintains world state, entities, relationships, forecasts."""
    
    def __init__(self):
        self._state: dict[str, Any] = {}
        self._last_updated = time.time()
    
    def update(self, key: str, value: Any) -> None:
        self._state[key] = value
        self._last_updated = time.time()
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)
    
    def status(self) -> dict:
        return {"entities": len(self._state), "last_updated": self._last_updated}
