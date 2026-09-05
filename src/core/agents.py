
"""
Sub-agent Lifecycle — spawn / terminate / monitor specialized agents.

Extracted & enhanced from agx-harness-main:
- agents.py: AgentRegistry, spawn, terminate, active
"""

from __future__ import annotations

import builtins
import logging
import time

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry of live sub-agents."""

    def __init__(self) -> None:
        self.agents: dict[str, dict[str, object]] = {}

    def spawn(self, role: str, agent_id: str | None = None) -> str:
        aid = agent_id or ("agent_%d" % (len(self.agents) + 1))
        now = int(time.time())
        self.agents[aid] = {"role": role, "status": "active",
                            "spawned": now, "last_seen": now}
        logger.info("Agent spawned: %s (role=%s)", aid, role)
        return aid

    def terminate(self, agent_id: str) -> bool:
        if agent_id in self.agents:
            self.agents[agent_id]["status"] = "terminated"
            logger.info("Agent terminated: %s", agent_id)
            return True
        return False

    def heartbeat(self, agent_id: str) -> bool:
        if agent_id in self.agents:
            self.agents[agent_id]["last_seen"] = int(time.time())
            return True
        return False

    def active(self) -> builtins.list[str]:
        return [a for a, b in self.agents.items() if b["status"] == "active"]

    def list(self) -> dict[str, dict[str, object]]:
        return self.agents


def spawn(state: dict, role: str, agent_id: str | None = None) -> str:
    reg = state.setdefault("shared_state", {}).setdefault("_agents", AgentRegistry())
    return reg.spawn(role, agent_id)


def terminate(state: dict, agent_id: str) -> bool:
    reg = state.get("shared_state", {}).get("_agents")
    return reg.terminate(agent_id) if reg else False


def active(state: dict) -> list[str]:
    reg = state.get("shared_state", {}).get("_agents")
    return reg.active() if reg else []
