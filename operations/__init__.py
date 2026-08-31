"""Operations Workstream — Watchdog, Scheduler, Checkpointing, Economic Ledger."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    RUNNING = "running"
    STALLED = "stalled"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentHealth:
    agent_id: str
    pid: int | None
    status: AgentStatus
    last_heartbeat: float
    memory_mb: float
    cpu_percent: float
    task_count: int


@dataclass
class Checkpoint:
    checkpoint_id: str
    agent_id: str
    state: dict[str, Any]
    timestamp: float
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class EconomicEntry:
    timestamp: float
    agent_id: str
    action: str
    cost: float
    value: float
    task_id: str
    details: dict[str, Any] = field(default_factory=dict)


class Watchdog:
    """Monitors agent health and restarts stalled agents."""

    def __init__(self, heartbeat_timeout: float = 120.0, max_restarts: int = 3):
        self.heartbeat_timeout = heartbeat_timeout
        self.max_restarts = max_restarts
        self._agents: dict[str, AgentHealth] = {}
        self._restart_counts: dict[str, int] = {}

    def register(self, agent_id: str, pid: int | None = None) -> None:
        self._agents[agent_id] = AgentHealth(
            agent_id=agent_id,
            pid=pid,
            status=AgentStatus.RUNNING,
            last_heartbeat=time.time(),
            memory_mb=0.0,
            cpu_percent=0.0,
            task_count=0,
        )
        self._restart_counts[agent_id] = 0

    def heartbeat(self, agent_id: str, **metrics: Any) -> None:
        if agent_id in self._agents:
            self._agents[agent_id].last_heartbeat = time.time()
            for k, v in metrics.items():
                if hasattr(self._agents[agent_id], k):
                    setattr(self._agents[agent_id], k, v)

    def check_health(self) -> list[AgentHealth]:
        """Return agents that have exceeded heartbeat timeout."""
        now = time.time()
        stalled = []
        for agent in self._agents.values():
            if agent.status == AgentStatus.RUNNING and (now - agent.last_heartbeat) > self.heartbeat_timeout:
                agent.status = AgentStatus.STALLED
                stalled.append(agent)
        return stalled

    def should_restart(self, agent_id: str) -> bool:
        """Check if agent should be restarted (under max restart limit)."""
        return self._restart_counts.get(agent_id, 0) < self.max_restarts

    def restart(self, agent_id: str) -> bool:
        """Record a restart attempt."""
        if not self.should_restart(agent_id):
            return False
        self._restart_counts[agent_id] = self._restart_counts.get(agent_id, 0) + 1
        if agent_id in self._agents:
            self._agents[agent_id].status = AgentStatus.RUNNING
            self._agents[agent_id].last_heartbeat = time.time()
        return True


class Scheduler:
    """Priority-based task scheduler for agent dispatch."""

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self._queue: asyncio.PriorityQueue[tuple[int, float, str, dict]] = asyncio.PriorityQueue()
        self._running: dict[str, dict] = {}

    async def submit(self, task_id: str, priority: int = 5, payload: dict | None = None) -> None:
        """Submit a task. Lower priority number = higher priority."""
        await self._queue.put((priority, time.time(), task_id, payload or {}))

    async def get_next(self) -> tuple[str, dict] | None:
        """Get the next task if under concurrency limit."""
        if len(self._running) >= self.max_concurrent or self._queue.empty():
            return None
        _, _, task_id, payload = await self._queue.get()
        self._running[task_id] = payload
        return task_id, payload

    def complete(self, task_id: str) -> None:
        self._running.pop(task_id, None)

    @property
    def running_count(self) -> int:
        return len(self._running)

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()


class CheckpointManager:
    """Saves and restores agent state for crash recovery."""

    def __init__(self, checkpoint_dir: str | Path):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save(self, checkpoint: Checkpoint) -> Path:
        path = self.checkpoint_dir / f"{checkpoint.agent_id}_{checkpoint.checkpoint_id}.json"
        path.write_text(json.dumps({
            "checkpoint_id": checkpoint.checkpoint_id,
            "agent_id": checkpoint.agent_id,
            "state": checkpoint.state,
            "timestamp": checkpoint.timestamp,
            "metadata": checkpoint.metadata,
        }, indent=2))
        return path

    def load(self, agent_id: str, checkpoint_id: str) -> Checkpoint | None:
        path = self.checkpoint_dir / f"{agent_id}_{checkpoint_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return Checkpoint(**data)

    def latest(self, agent_id: str) -> Checkpoint | None:
        """Find the latest checkpoint for an agent."""
        checkpoints = list(self.checkpoint_dir.glob(f"{agent_id}_*.json"))
        if not checkpoints:
            return None
        latest_path = max(checkpoints, key=lambda p: (p.stat().st_mtime, p.stem.split('_')[-1] if '_' in p.stem else ''))
        data = json.loads(latest_path.read_text())
        return Checkpoint(**data)

    def list_checkpoints(self, agent_id: str | None = None) -> list[Checkpoint]:
        pattern = f"{agent_id}_*.json" if agent_id else "*.json"
        return [Checkpoint(**json.loads(p.read_text())) for p in self.checkpoint_dir.glob(pattern)]


class EconomicLedger:
    """Tracks cost/value of agent operations."""

    def __init__(self, ledger_path: str | Path):
        self.ledger_path = Path(ledger_path)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: list[EconomicEntry] = []
        self._load()

    def _load(self) -> None:
        if self.ledger_path.exists():
            for line in self.ledger_path.read_text().splitlines():
                if line.strip():
                    data = json.loads(line)
                    self._entries.append(EconomicEntry(**data))

    def record(self, entry: EconomicEntry) -> None:
        self._entries.append(entry)
        with open(self.ledger_path, "a") as f:
            f.write(json.dumps({
                "timestamp": entry.timestamp,
                "agent_id": entry.agent_id,
                "action": entry.action,
                "cost": entry.cost,
                "value": entry.value,
                "task_id": entry.task_id,
                "details": entry.details,
            }) + "\n")

    def total_cost(self, agent_id: str | None = None) -> float:
        entries = [e for e in self._entries if agent_id is None or e.agent_id == agent_id]
        return sum(e.cost for e in entries)

    def total_value(self, agent_id: str | None = None) -> float:
        entries = [e for e in self._entries if agent_id is None or e.agent_id == agent_id]
        return sum(e.value for e in entries)

    def roi(self, agent_id: str | None = None) -> float:
        cost = self.total_cost(agent_id)
        value = self.total_value(agent_id)
        return (value - cost) / cost if cost > 0 else 0.0

    def summary(self) -> dict[str, Any]:
        agents = set(e.agent_id for e in self._entries)
        return {
            "total_entries": len(self._entries),
            "total_cost": self.total_cost(),
            "total_value": self.total_value(),
            "roi": self.roi(),
            "agents": {
                agent: {
                    "cost": self.total_cost(agent),
                    "value": self.total_value(agent),
                    "roi": self.roi(agent),
                }
                for agent in agents
            },
        }
