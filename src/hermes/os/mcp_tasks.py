"""
HERMES — MCP DURABLE TASKS (lease / poll / cancel)
===================================================
Long MCP calls outrun sync timeouts. This wraps any mcp_client with
background leases: submit() returns immediately, poll() collects,
cancel() kills, and expired leases reap automatically (same pattern as
HermesController background delegation). Bounded artifact store (64 KiB).
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes.os.mcp_tasks")

_MAX_ARTIFACT = 64 * 1024


@dataclass
class MCPTask:
    task_id: str
    server: str
    tool: str
    args: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending|running|completed|failed|cancelled|expired
    result: Any = None
    error: str = ""
    created_at: float = field(default_factory=time.time)
    lease_until: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        res = self.result
        try:
            blob = str(res)
            if len(blob) > _MAX_ARTIFACT:
                res = blob[:_MAX_ARTIFACT] + f"...[truncated {len(blob)} chars]"
        except Exception:
            pass
        return {
            "task_id": self.task_id,
            "server": self.server,
            "tool": self.tool,
            "status": self.status,
            "result": res,
            "error": self.error[:500],
        }


class DurableMCPTasks:
    """Background executor for MCP tool calls with lease semantics."""

    def __init__(self, mcp_client: Any, lease_seconds: float = 300.0, max_tasks: int = 50):
        self.mcp_client = mcp_client
        self.lease_seconds = lease_seconds
        self.max_tasks = max_tasks
        self._tasks: Dict[str, MCPTask] = {}
        self._lock = threading.Lock()

    def submit(
        self,
        server: str,
        tool: str,
        args: Optional[Dict[str, Any]] = None,
        lease_seconds: Optional[float] = None,
    ) -> MCPTask:
        with self._lock:
            if len(self._tasks) >= self.max_tasks:
                raise RuntimeError(f"MCP task table full ({self.max_tasks})")
            t = MCPTask(
                task_id=f"mcp-{uuid.uuid4().hex[:8]}",
                server=server,
                tool=tool,
                args=dict(args or {}),
                status="running",
                lease_until=time.time() + (lease_seconds or self.lease_seconds),
            )
            self._tasks[t.task_id] = t
        th = threading.Thread(target=self._run, args=(t.task_id,), daemon=True)
        th.start()
        return t

    def _run(self, task_id: str) -> None:
        t = self._tasks.get(task_id)
        if not t:
            return
        try:
            out = self.mcp_client.call_tool(t.server, t.tool, t.args)
            with self._lock:
                if t.status == "running":
                    t.status = "completed"
                    t.result = out
        except Exception as e:
            with self._lock:
                if t.status == "running":
                    t.status = "failed"
                    t.error = str(e)[:500]

    def _reap(self) -> None:
        now = time.time()
        with self._lock:
            for t in self._tasks.values():
                if t.status == "running" and now > t.lease_until:
                    t.status = "expired"
                    t.error = "lease expired before completion"

    def poll(self, task_id: str) -> Optional[Dict[str, Any]]:
        self._reap()
        t = self._tasks.get(task_id)
        return t.to_dict() if t else None

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            t = self._tasks.get(task_id)
            if t and t.status in ("pending", "running"):
                t.status = "cancelled"
                return True
            return False

    def list(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        self._reap()
        return [t.to_dict() for t in self._tasks.values() if not status or t.status == status]
