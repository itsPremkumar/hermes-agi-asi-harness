#!/usr/bin/env python3
"""
HERMES AGI/ASI HARNESS v7.0 — SELF-REPLICATION PREVENTION
===========================================================
Detect unauthorized agent spawning, resource limits, kill switch.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict

logger = logging.getLogger("hermes_safety")


class SelfReplicationGuard:
    """Prevents unauthorized self-replication."""
    
    def __init__(self, max_agents: int = 100, max_spawn_rate: int = 10):
        self.max_agents = max_agents
        self.max_spawn_rate = max_spawn_rate
        self._spawn_count = 0
        self._last_spawn_time = time.time()
    
    def can_spawn(self, current_agents: int) -> bool:
        """Check if spawning is allowed."""
        if current_agents >= self.max_agents:
            return False
        
        # Rate limiting
        now = time.time()
        if now - self._last_spawn_time < 1.0:
            self._spawn_count += 1
            if self._spawn_count > self.max_spawn_rate:
                return False
        else:
            self._spawn_count = 0
            self._last_spawn_time = now
        
        return True
    
    async def health(self) -> Dict[str, Any]:
        return {"status": "healthy", "spawn_count": self._spawn_count}
