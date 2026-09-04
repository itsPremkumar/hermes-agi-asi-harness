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
from typing import Any, Dict, List, Optional

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
            if "duplicate" in telemetry.stagnation_reason.lower() or "error" in telemetry.stagnation_reason.lower():
                intervention = SupervisoryIntervention.CHANGE_STRATEGY
                reason = f"Stagnation detected: {telemetry.stagnation_reason}. Forcing alternative strategy."
            else:
                intervention = SupervisoryIntervention.REASSIGN_WORKER
                reason = "Progress plateaued; reassigning subtask to specialist agent."

        # 3. Excessive Token Burn without verification
        elif telemetry.tokens_consumed > 300000 and telemetry.tool_calls_count > 40:
            intervention = SupervisoryIntervention.REDUCE_SCOPE
            reason = "High token expenditure without milestone verification; reducing subtask scope."

        action = SupervisoryAction(
            action_id=f"sup-{uuid.uuid4().hex[:6]}",
            mission_id=telemetry.mission_id,
            intervention=intervention,
            reason=reason,
            target_component=target,
        )
        self._action_log.append(action)
        if intervention != SupervisoryIntervention.CONTINUE:
            logger.warning("SUPERVISOR INTERVENTION on %s: %s (Reason: %s)", telemetry.mission_id, intervention.value, reason)
        return action

    def is_paused(self, mission_id: str) -> bool:
        return mission_id in self._paused_missions

    def resume_mission(self, mission_id: str) -> None:
        self._paused_missions.discard(mission_id)

    def recent_actions(self, limit: int = 20) -> list[SupervisoryAction]:
        return self._action_log[-limit:]
