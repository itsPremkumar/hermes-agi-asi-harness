"""
Hermes AGI/ASI Harness — Active Watchdog & Continuous Supervisor Monitor.

Supervises the Hermes Agent during execution:
- Tracks heartbeats & liveness
- Detects action stalls and repetitive tool-calling loops
- Monitors invariant safety bounds
- Generates active steering interjections to redirect Hermes when off-track
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes.watchdog")


@dataclass
class AgentTelemetryEvent:
    """A single logged telemetry event from the Hermes execution loop."""
    event_id: str
    timestamp: float
    action_type: str  # tool_call, heartbeat, thought, error, steering
    tool_name: str = ""
    args_summary: str = ""
    result_summary: str = ""
    duration_ms: float = 0.0


class HermesWatchdogMonitor:
    """
    Active Watchdog & Supervisor Monitor for the Hermes AI Agent.
    
    Provides continuous telemetry tracking, stall/loop detection, and active
    steering interjections to maintain mission invariants.
    """

    def __init__(
        self,
        mission_id: str,
        heartbeat_timeout_seconds: float = 60.0,
        max_loop_threshold: int = 3,
    ):
        self.mission_id = mission_id
        self.heartbeat_timeout = heartbeat_timeout_seconds
        self.max_loop_threshold = max_loop_threshold
        self.events: list[AgentTelemetryEvent] = []
        self.last_heartbeat = time.time()
        self.steering_history: list[str] = []
        self.action_signature_history: list[str] = []
        self.stalls_detected = 0

    def record_heartbeat(self) -> None:
        """Record a liveness heartbeat from the executing agent."""
        self.last_heartbeat = time.time()
        self.events.append(
            AgentTelemetryEvent(
                event_id=f"hb-{len(self.events)}",
                timestamp=self.last_heartbeat,
                action_type="heartbeat",
            )
        )

    def record_action(self, tool_name: str, args: Any, result: Any, duration_ms: float = 0.0) -> None:
        """Record an executed tool action and inspect for loops."""
        self.last_heartbeat = time.time()
        args_str = str(args)[:100]
        res_str = str(result)[:100]
        sig = f"{tool_name}:{args_str}"
        self.action_signature_history.append(sig)

        event = AgentTelemetryEvent(
            event_id=f"act-{len(self.events)}",
            timestamp=self.last_heartbeat,
            action_type="tool_call",
            tool_name=tool_name,
            args_summary=args_str,
            result_summary=res_str,
            duration_ms=duration_ms,
        )
        self.events.append(event)

    def detect_stall_or_loop(self) -> dict[str, Any]:
        """
        Inspect execution trajectory for loops, stalls, or deadlocks.
        """
        now = time.time()
        # 1. Heartbeat timeout check
        if (now - self.last_heartbeat) > self.heartbeat_timeout:
            return {
                "stalled": True,
                "reason": "heartbeat_timeout",
                "message": f"Agent silent for {now - self.last_heartbeat:.1f}s (> {self.heartbeat_timeout}s)",
            }

        # 2. Loop detection: check if last N actions are identical
        if len(self.action_signature_history) >= self.max_loop_threshold:
            recent = self.action_signature_history[-self.max_loop_threshold:]
            if len(set(recent)) == 1:
                self.stalls_detected += 1
                return {
                    "stalled": True,
                    "reason": "repetitive_loop",
                    "action_signature": recent[0],
                    "message": f"Detected repetitive loop: '{recent[0]}' executed {self.max_loop_threshold} times consecutively",
                }

        return {"stalled": False, "reason": "normal", "message": "Agent execution progressing within bounds"}

    def generate_steering_interjection(self, stall_info: dict[str, Any]) -> str:
        """
        Generate an active supervisor steering prompt to guide Hermes back on track.
        """
        reason = stall_info.get("reason", "unknown")
        if reason == "repetitive_loop":
            action = stall_info.get("action_signature", "action")
            interjection = (
                f"[SUPERVISOR INTERJECTION] WARNING: You are trapped in a repetitive execution loop calling '{action}'. "
                f"STOP repeating this exact call. Alter your strategy, verify prerequisites, or try an alternative approach."
            )
        elif reason == "heartbeat_timeout":
            interjection = (
                "[SUPERVISOR INTERJECTION] NOTICE: No progress signal received within the heartbeat window. "
                "Emit a status update or yield partial progress immediately."
            )
        else:
            interjection = (
                "[SUPERVISOR INTERJECTION] ATTENTION: Execution divergence detected. "
                "Align with the active Goal Contract acceptance criteria."
            )

        self.steering_history.append(interjection)
        self.events.append(
            AgentTelemetryEvent(
                event_id=f"steer-{len(self.events)}",
                timestamp=time.time(),
                action_type="steering",
                result_summary=interjection,
            )
        )
        return interjection

    def get_telemetry_summary(self) -> dict[str, Any]:
        """Return a summary of all monitoring telemetry."""
        return {
            "mission_id": self.mission_id,
            "total_events": len(self.events),
            "stalls_detected": self.stalls_detected,
            "steering_interjections": len(self.steering_history),
            "last_heartbeat_age": time.time() - self.last_heartbeat,
            "history": [
                {
                    "type": e.action_type,
                    "tool": e.tool_name,
                    "args": e.args_summary,
                    "result": e.result_summary,
                    "timestamp": e.timestamp,
                }
                for e in self.events[-10:]  # last 10 events
            ],
        }
