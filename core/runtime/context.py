#!/usr/bin/env python3
"""
Agent Context — unifies the working plugins into one coherent surface.

Wires together:
- state_manager       (session / task state)
- memory_curator      (long-term semantic memory)
- permission_system   (action gating, R0-R6)
- audit_logger        (every action logged + tamper-evident)
- streaming_output    (live output to subscribers)

The agent ONLY ever reaches plugins through this context or the kernel.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.runtime.agent_kernel import AgentKernel
from core.runtime.event_bus import EventBus


class AgentContext:
    """Single entry point for agent <-> plugin interaction."""

    def __init__(self, kernel: AgentKernel, event_bus: EventBus = None):
        self.kernel = kernel
        self.bus = event_bus or EventBus()
        self.state = kernel.get("state_manager")
        self.memory = kernel.get("memory_curator")
        self.permissions = kernel.get("permission_system")
        self.audit = kernel.get("audit_logger")
        self.stream = kernel.get("streaming_output")
        self.session_id: Optional[str] = None
        self.task_id: Optional[str] = None

    # ── Session / task lifecycle ────────────────────────────────────────

    def begin_session(self, title: str = "agent-session") -> str:
        if self.state:
            self.session_id = self.state.create_session(title, {"created": datetime.utcnow().isoformat()})
        else:
            self.session_id = f"session_{id(self)}"
        return self.session_id

    def begin_task(self, title: str, description: str = "") -> str:
        if self.state and self.session_id:
            self.task_id = self.state.create_task(title, description, session_id=self.session_id)
        else:
            self.task_id = f"task_{id(self)}"
        return self.task_id

    def set_task_status(self, status: str, result: Any = None):
        if self.state and self.task_id:
            self.state.update_task(self.task_id, status=status, result=json.dumps(result) if result is not None else None)

    # ── Permission gating ───────────────────────────────────────────────

    def check_permission(self, action: str, context: Dict[str, Any] = None) -> tuple[bool, str]:
        if not self.permissions:
            return True, "no permission system loaded"
        return self.permissions.check(action, context or {})

    def require_permission(self, action: str, context: Dict[str, Any] = None):
        """Raise if not permitted."""
        ok, reason = self.check_permission(action, context)
        if not ok:
            raise PermissionError(f"Action '{action}' blocked: {reason}")

    # ── Audit ────────────────────────────────────────────────────────────

    def log_action(self, event_type: str, action: str, target: str,
                   result: str, details: Dict[str, Any] = None):
        if self.audit:
            self.audit.log(event_type, "agent", action, target, result, details or {})
        # Also emit to event bus for subscribers
        self.bus.emit(event_type, {"action": action, "target": target, "result": result, **(details or {})})

    # ── Memory ───────────────────────────────────────────────────────────

    def remember(self, content: str, category: str = "general",
                 importance: float = 0.5, tags: List[str] = None) -> Optional[str]:
        if not self.memory:
            return None
        return self.memory.add_memory(content, category, importance, tags)

    def recall(self, query: str, top_k: int = 3, category: str = None) -> List[Dict[str, Any]]:
        if not self.memory:
            return []
        return self.memory.search(query, top_k=top_k, category=category)

    # ── Streaming ───────────────────────────────────────────────────────

    async def emit(self, content: str, metadata: Dict[str, Any] = None):
        if self.stream:
            await self.stream.emit(content, metadata=metadata or {})

    def subscribe(self):
        if self.stream:
            return self.stream.subscribe()
        return None

    def unsubscribe(self, queue):
        if self.stream:
            self.stream.unsubscribe(queue)

    # ── Direct plugin access (by name) ──────────────────────────────────

    def plugin(self, name: str):
        return self.kernel.get(name)

    def plugins_with_capability(self, capability: str) -> List[str]:
        return self.kernel.get_plugins_by_capability(capability)
