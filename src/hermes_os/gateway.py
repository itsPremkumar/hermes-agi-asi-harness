"""
HERMES INTELLIGENCE OS — OPENCLAW 2.0 GATEWAY & NODE ABSTRACTION
===============================================================
Inspired by OpenClaw 2.0 and Agent Control Protocol (ACP) architecture:
- Heartbeat vs Task loop separation (lightweight attention polling vs heavy execution).
- Distributed Device Node Registry (Desktop, Cloud VM, Server, Edge).
- External Harness Interoperability Bridge (Claude Code, OpenHands, Codex, Prime Agent).
"""

from __future__ import annotations

import enum
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("hermes.os.gateway")


class NodeType(str, enum.Enum):
    """Device node deployment environment."""
    DESKTOP = "desktop"
    CLOUD_VM = "cloud_vm"
    SERVER = "server"
    EDGE = "edge"


class NodeStatus(str, enum.Enum):
    """Operational status of a registered device node."""
    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"
    DRAINING = "draining"


@dataclass
class DeviceNode:
    """A compute device node capable of hosting agent tool or subagent execution."""
    node_id: str
    node_type: NodeType
    platform: str                    # e.g., "windows", "linux", "darwin"
    capabilities: List[str]          # e.g., ["python", "bash", "browser", "gpu"]
    status: NodeStatus = NodeStatus.ONLINE
    cpu_cores: int = 8
    memory_gb: float = 16.0
    has_gpu: bool = False
    last_heartbeat: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_alive(self, timeout_seconds: float = 60.0) -> bool:
        return (time.time() - self.last_heartbeat) < timeout_seconds and self.status != NodeStatus.OFFLINE

    def matches_capabilities(self, required_caps: List[str]) -> bool:
        return all(cap in self.capabilities for cap in required_caps)


class NodeRegistry:
    """Manages registered compute device nodes across local and remote clusters."""

    def __init__(self):
        self._nodes: Dict[str, DeviceNode] = {}
        # Register the default local execution host
        self.register_node(DeviceNode(
            node_id="node-local-host",
            node_type=NodeType.DESKTOP,
            platform="windows",
            capabilities=["python", "bash", "browser", "filesystem", "repl"],
            status=NodeStatus.ONLINE,
            cpu_cores=16,
            memory_gb=32.0,
            has_gpu=True,
        ))

    def register_node(self, node: DeviceNode) -> None:
        self._nodes[node.node_id] = node
        logger.info(f"Registered device node {node.node_id} ({node.node_type.value}, {node.platform})")

    def unregister_node(self, node_id: str) -> bool:
        if node_id in self._nodes:
            del self._nodes[node_id]
            logger.info(f"Unregistered device node {node_id}")
            return True
        return False

    def update_heartbeat(self, node_id: str) -> bool:
        if node_id in self._nodes:
            self._nodes[node_id].last_heartbeat = time.time()
            if self._nodes[node_id].status == NodeStatus.OFFLINE:
                self._nodes[node_id].status = NodeStatus.ONLINE
            return True
        return False

    def find_best_node(
        self,
        required_capabilities: List[str],
        min_memory_gb: float = 0.0,
        prefer_gpu: bool = False,
    ) -> Optional[DeviceNode]:
        """Find the most capable and idle node matching requirements."""
        candidates = [
            n for n in self._nodes.values()
            if n.is_alive()
            and n.status != NodeStatus.BUSY
            and n.matches_capabilities(required_capabilities)
            and n.memory_gb >= min_memory_gb
        ]
        if not candidates:
            # Fallback to busy if alive and matching
            candidates = [
                n for n in self._nodes.values()
                if n.is_alive()
                and n.matches_capabilities(required_capabilities)
                and n.memory_gb >= min_memory_gb
            ]
        if not candidates:
            return None

        # Sort: prefer GPU if requested, then highest memory
        candidates.sort(
            key=lambda n: (1 if prefer_gpu and n.has_gpu else 0, n.memory_gb, n.cpu_cores),
            reverse=True,
        )
        return candidates[0]

    def list_nodes(self) -> List[DeviceNode]:
        return list(self._nodes.values())


# =====================================================================
# Heartbeat vs Task Loop Separation (OpenClaw Architecture)
# =====================================================================

@dataclass
class AttentionPollResult:
    """Outcome of an idle heartbeat attention check."""
    needs_attention: bool
    alerts: List[str] = field(default_factory=list)
    pending_approvals: List[str] = field(default_factory=list)
    active_tasks_count: int = 0
    health_ok: bool = True
    timestamp: float = field(default_factory=time.time)


class HeartbeatMonitor:
    """
    Lightweight, fast non-blocking heartbeat loop.
    Evaluates whether the system requires attention without waking
    the full heavy cognitive or LLM reasoning pipeline.
    """

    def __init__(self):
        self._attention_triggers: List[Callable[[], Optional[str]]] = []
        self._pending_approvals: List[str] = []

    def register_trigger(self, check_fn: Callable[[], Optional[str]]) -> None:
        """Register a callback that returns an alert string if attention is needed."""
        self._attention_triggers.append(check_fn)

    def submit_pending_approval(self, approval_id: str) -> None:
        self._pending_approvals.append(approval_id)

    def resolve_pending_approval(self, approval_id: str) -> bool:
        if approval_id in self._pending_approvals:
            self._pending_approvals.remove(approval_id)
            return True
        return False

    def poll_attention(self, active_tasks_count: int = 0) -> AttentionPollResult:
        """Poll attention quickly (sub-millisecond overhead)."""
        alerts: List[str] = []
        for check in self._attention_triggers:
            try:
                alert = check()
                if alert:
                    alerts.append(alert)
            except Exception as e:
                alerts.append(f"Trigger check error: {e}")

        needs_attention = (
            len(alerts) > 0 or
            len(self._pending_approvals) > 0
        )

        return AttentionPollResult(
            needs_attention=needs_attention,
            alerts=alerts,
            pending_approvals=list(self._pending_approvals),
            active_tasks_count=active_tasks_count,
            health_ok=True,
        )


# =====================================================================
# Agent Control Protocol (ACP) — External Harness Bridge
# =====================================================================

class ExternalHarnessType(str, enum.Enum):
    """External autonomous agent harness environments."""
    CLAUDE_CODE = "claude_code"
    OPENHANDS = "openhands"
    CODEX = "codex"
    PRIME_AGENT = "prime_agent"
    AVO = "avo"


@dataclass
class HarnessSession:
    """State of an external managed agent harness session."""
    session_id: str
    harness_type: ExternalHarnessType
    status: str                        # "init", "running", "paused", "completed", "failed"
    assigned_node_id: str
    objective: str
    tokens_consumed: int = 0
    created_at: float = field(default_factory=time.time)
    telemetry_logs: List[str] = field(default_factory=list)
    result_data: Dict[str, Any] = field(default_factory=dict)


class ExternalHarnessBridge:
    """
    Bridge enabling Hermes OS to launch, steer, supervise, and assimilate
    results from third-party autonomous harnesses (Claude Code, OpenHands, Codex, etc.).
    """

    def __init__(self, node_registry: NodeRegistry):
        self.node_registry = node_registry
        self._sessions: Dict[str, HarnessSession] = {}

    def launch_harness(
        self,
        harness_type: ExternalHarnessType,
        objective: str,
        node_id: Optional[str] = None,
    ) -> HarnessSession:
        """Launch an external agent harness session on an available compute node."""
        if not node_id:
            best_node = self.node_registry.find_best_node(required_capabilities=["python"])
            node_id = best_node.node_id if best_node else "node-local-host"

        session_id = f"acp-{harness_type.value}-{uuid.uuid4().hex[:8]}"
        session = HarnessSession(
            session_id=session_id,
            harness_type=harness_type,
            status="running",
            assigned_node_id=node_id,
            objective=objective,
        )
        session.telemetry_logs.append(f"Session initialized on {node_id} for {objective}")
        self._sessions[session_id] = session
        logger.info(f"Launched external harness {harness_type.value} on {node_id} (session={session_id})")
        return session

    def steer_harness(self, session_id: str, steering_command: str) -> bool:
        """Inject mid-turn steering instruction into a running harness."""
        if session_id not in self._sessions:
            return False
        session = self._sessions[session_id]
        if session.status != "running":
            return False
        session.telemetry_logs.append(f"Steering injected: {steering_command}")
        return True

    def complete_harness(self, session_id: str, result: Dict[str, Any], tokens: int = 1200) -> bool:
        """Mark harness session as completed and ingest results."""
        if session_id not in self._sessions:
            return False
        session = self._sessions[session_id]
        session.status = "completed"
        session.tokens_consumed += tokens
        session.result_data = result
        session.telemetry_logs.append("Session completed successfully")
        return True

    def terminate_harness(self, session_id: str, reason: str = "") -> bool:
        """Halt an external harness session."""
        if session_id not in self._sessions:
            return False
        session = self._sessions[session_id]
        session.status = "terminated"
        session.telemetry_logs.append(f"Terminated: {reason}")
        return True

    def get_session(self, session_id: str) -> Optional[HarnessSession]:
        return self._sessions.get(session_id)

    def list_sessions(self) -> List[HarnessSession]:
        return list(self._sessions.values())


# =====================================================================
# Central OpenClaw Gateway
# =====================================================================

class OpenClawGateway:
    """
    Central Gateway coordinating Node Registries, Heartbeat polling,
    and external harness orchestration.
    """

    def __init__(self):
        self.nodes = NodeRegistry()
        self.heartbeat = HeartbeatMonitor()
        self.external_harness = ExternalHarnessBridge(node_registry=self.nodes)

    def check_attention(self, active_tasks: int = 0) -> AttentionPollResult:
        """Fast non-blocking heartbeat poll."""
        return self.heartbeat.poll_attention(active_tasks_count=active_tasks)
