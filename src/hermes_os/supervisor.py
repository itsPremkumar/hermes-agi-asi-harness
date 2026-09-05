"""
HERMES INTELLIGENCE OS — PLANE 18A: THE EXTERNAL SUPERVISOR LAYER
=================================================================
AVO-inspired out-of-band supervisory intelligence:
- Operates purely on execution telemetry (not a worker agent, does not edit files)
- Monitors progress rate, resource burn, stagnation signals, and safety anomalies
- Issues steering interventions:
  PAUSE • RESUME • REASSIGN • CHANGE_MODEL • CHANGE_STRATEGY • REDUCE_SCOPE • RESTORE_CHECKPOINT • ROLLBACK • ESCALATE
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("hermes.os.supervisor")


class SupervisoryIntervention(str, Enum):
    CONTINUE = "continue"
    PAUSE = "pause"
    RESUME = "resume"
    REASSIGN_WORKER = "reassign_worker"
    CHANGE_MODEL = "change_model"
    CHANGE_STRATEGY = "change_strategy"
    REDUCE_SCOPE = "reduce_scope"
    RESTORE_CHECKPOINT = "restore_checkpoint"
    ROLLBACK = "rollback"
    TERMINATE = "terminate"
    ESCALATE_TO_HUMAN = "escalate_to_human"


@dataclass
class SupervisorTelemetry:
    mission_id: str
    active_agent_id: str
    elapsed_seconds: float
    tokens_consumed: int
    tool_calls_count: int
    stagnation_detected: bool
    stagnation_reason: str = ""
    anomaly_detected: bool = False
    anomaly_reason: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class SupervisoryAction:
    action_id: str
    mission_id: str
    intervention: SupervisoryIntervention
    reason: str
    target_component: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class SupervisorDirective:
    """AGX-style LLM re-plan output: what to do when waves stall."""

    directive: str = "CONTINUE"
    strategy: str = ""
    subgoals: list[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "directive": self.directive,
            "strategy": self.strategy,
            "subgoals": self.subgoals,
            "reason": self.reason,
        }


class ExternalSupervisor:
    """
    Independent supervisory controller running out-of-band from primary workers.
    Ensures long-horizon execution never derails into runaway loops or stagnation.
    """

    def __init__(self):
        self._telemetry_history: list[SupervisorTelemetry] = []
        self._action_log: list[SupervisoryAction] = []
        self._paused_missions: set[str] = set()

    def ingest_telemetry(self, telemetry: SupervisorTelemetry) -> SupervisoryAction:
        """Evaluate real-time worker telemetry and decide on intervention."""
        self._telemetry_history.append(telemetry)
        intervention = SupervisoryIntervention.CONTINUE
        reason = "Execution progressing nominally"
        target = telemetry.active_agent_id

        # 1. Critical Anomaly or Misalignment
        if telemetry.anomaly_detected:
            intervention = SupervisoryIntervention.PAUSE
            reason = f"Safety anomaly detected: {telemetry.anomaly_reason}"
            self._paused_missions.add(telemetry.mission_id)

        # 2. Critical Stagnation Loop
        elif telemetry.stagnation_detected:
            if (
                "duplicate" in telemetry.stagnation_reason.lower()
                or "error" in telemetry.stagnation_reason.lower()
            ):
                intervention = SupervisoryIntervention.CHANGE_STRATEGY
                reason = f"Stagnation detected: {telemetry.stagnation_reason}. Forcing alternative strategy."
            else:
                intervention = SupervisoryIntervention.REASSIGN_WORKER
                reason = "Progress plateaued; reassigning subtask to specialist agent."

        # 3. Excessive Token Burn without verification
        elif telemetry.tokens_consumed > 300000 and telemetry.tool_calls_count > 40:
            intervention = SupervisoryIntervention.REDUCE_SCOPE
            reason = (
                "High token expenditure without milestone verification; reducing subtask scope."
            )

        action = SupervisoryAction(
            action_id=f"sup-{uuid.uuid4().hex[:6]}",
            mission_id=telemetry.mission_id,
            intervention=intervention,
            reason=reason,
            target_component=target,
        )
        self._action_log.append(action)
        if intervention != SupervisoryIntervention.CONTINUE:
            logger.warning(
                "SUPERVISOR INTERVENTION on %s: %s (Reason: %s)",
                telemetry.mission_id,
                intervention.value,
                reason,
            )
        return action

    def is_paused(self, mission_id: str) -> bool:
        return mission_id in self._paused_missions

    def resume_mission(self, mission_id: str) -> None:
        self._paused_missions.discard(mission_id)

    def recent_actions(self, limit: int = 20) -> list[SupervisoryAction]:
        return self._action_log[-limit:]

    # ------------------------------------------------------------------
    # Closed-loop actuation: turn an intervention into runtime/daemon calls
    # ------------------------------------------------------------------
    async def actuate(
        self, action: SupervisoryAction, runtime: Any = None, daemon: Any = None
    ) -> dict[str, Any]:
        """Execute the intervention against live runtime + daemon. Returns actuation report."""
        iv = action.intervention
        try:
            if iv == SupervisoryIntervention.PAUSE and runtime is not None:
                await runtime.pause(action.mission_id, action.reason)
            elif iv == SupervisoryIntervention.RESUME and runtime is not None:
                await runtime.resume(action.mission_id)
                self.resume_mission(action.mission_id)
            elif iv == SupervisoryIntervention.RESTORE_CHECKPOINT and daemon is not None:
                snap = daemon.load_checkpoint(action.mission_id)
                return {"actuated": True, "intervention": iv.value, "checkpoint": bool(snap)}
            elif iv == SupervisoryIntervention.TERMINATE and runtime is not None:
                await runtime.pause(action.mission_id, "terminated by supervisor")
                self._paused_missions.add(action.mission_id)
            return {"actuated": True, "intervention": iv.value}
        except Exception as e:
            logger.error("Supervisor actuation failed: %s", e)
            return {"actuated": False, "error": str(e), "intervention": iv.value}

    def build_telemetry(
        self,
        mission_id: str,
        active_agent_id: str = "primary_worker",
        elapsed_seconds: float = 0.0,
        tokens_consumed: int = 0,
        tool_calls_count: int = 0,
        stagnation: Any = None,
        anomaly: str = "",
        has_signal: Optional[bool] = None,
    ) -> SupervisorTelemetry:
        """Build real telemetry from stagnation detector + counters (replaces hardcoded values).

        has_signal must come from the DETECTOR (AVOStagnationDetector.has_signal),
        not the telemetry snapshot — pass it explicitly. With zero recorded steps,
        wall-clock alone is not stagnation evidence.
        """
        stag_detected = False
        stag_reason = ""
        if stagnation is not None:
            lvl = getattr(stagnation, "level", "")
            level = str(getattr(lvl, "value", lvl) or "")
            rec = str(getattr(stagnation, "recommended_intervention", "") or "")
            # Only real traps count: PLATEAU / CRITICAL_LOOP. NOMINAL and
            # SLOW_PROGRESS ("continue_with_monitoring") must stay CONTINUE.
            signal = (
                bool(getattr(stagnation, "has_signal", True))
                if has_signal is None
                else bool(has_signal)
            )
            stag_detected = level.lower() in ("plateau", "critical_loop") and signal
            stag_reason = rec or level
            if level.lower() in ("plateau", "critical_loop") and not signal:
                stag_reason = f"{rec or level} (no recorded steps; treated nominal)"
        return SupervisorTelemetry(
            mission_id=mission_id,
            active_agent_id=active_agent_id,
            elapsed_seconds=elapsed_seconds,
            tokens_consumed=tokens_consumed,
            tool_calls_count=tool_calls_count,
            stagnation_detected=stag_detected,
            stagnation_reason=stag_reason,
            anomaly_detected=bool(anomaly),
            anomaly_reason=anomaly,
        )

    def llm_redirect(
        self, trajectory_summary: str, memory_bullets: str = "", llm_client: Any = None
    ) -> SupervisorDirective:
        """AGX-style stagnation→LLM re-plan. Falls back to rule-based directive offline."""
        if llm_client is None:
            low = trajectory_summary.lower()
            if "duplicate" in low or "error" in low or "fail" in low:
                return SupervisorDirective(
                    directive="CHANGE_STRATEGY",
                    strategy="epsilon_greedy",
                    subgoals=["isolate failing subtask", "retry with reduced scope"],
                    reason="Rule fallback: failure loop detected",
                )
            if "stagnat" in low or "plateau" in low:
                return SupervisorDirective(
                    directive="REDECOMPOSE",
                    strategy="lead_specialists",
                    subgoals=["split stalled wave", "verify each shard independently"],
                    reason="Rule fallback: plateau detected",
                )
            return SupervisorDirective(directive="CONTINUE", reason="Nominal")
        try:
            prompt = (
                f"Trajectory:\n{trajectory_summary}\nMemory:\n{memory_bullets}\n"
                "Return DIRECTIVE / STRATEGY / SUBGOALS lines."
            )
            out = llm_client.generate(prompt) if hasattr(llm_client, "generate") else ""
            text = getattr(out, "content", str(out))
            directive, strategy, subgoals = "CONTINUE", "", []
            for line in str(text).splitlines():
                u = line.strip().upper()
                if u.startswith("DIRECTIVE"):
                    directive = line.split(":", 1)[-1].strip().upper() or directive
                elif u.startswith("STRATEGY"):
                    strategy = line.split(":", 1)[-1].strip()
                elif u.startswith("SUBGOAL"):
                    subgoals.append(line.split(":", 1)[-1].strip())
            return SupervisorDirective(
                directive=directive, strategy=strategy, subgoals=subgoals, reason="LLM redirect"
            )
        except Exception as e:
            return SupervisorDirective(directive="CONTINUE", reason=f"LLM redirect failed: {e}")
