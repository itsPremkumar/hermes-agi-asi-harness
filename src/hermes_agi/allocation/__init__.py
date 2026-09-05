"""
Hermes AGI/ASI Harness — Hermes Allocation & Monitoring Package.
"""

from .monitor import AgentTelemetryEvent, HermesWatchdogMonitor
from .packet import HermesMissionPacket
from .quality_gates import (
    DEFAULT_AUTONOMOUS_CONTINUATION_DIRECTIVE,
    AutonomousQualityGatePolicy,
    QualityGateFailure,
    QualityGateVerdict,
)

__all__ = [
    "HermesMissionPacket",
    "HermesWatchdogMonitor",
    "AgentTelemetryEvent",
    "AutonomousQualityGatePolicy",
    "QualityGateVerdict",
    "QualityGateFailure",
    "DEFAULT_AUTONOMOUS_CONTINUATION_DIRECTIVE",
]
