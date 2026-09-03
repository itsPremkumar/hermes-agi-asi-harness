"""
Hermes AGI/ASI Harness — Autonomous Engines Package.

This package contains the continuous, supervisor, ultimate, and executive control plane
engines that orchestrate 24/7 autonomous operations:
- harness_control_plane: Multi-layer safety and task routing executive control plane
- hermes_ultimate: Integrated non-stop production agent loop
- hermes_engine: Execution engine and agent loop
- hermes_supervisor: System health and performance supervision
- continuous_dev: Automated canary deployments, A/B testing, and daily improvement
- master: Master process runner and service coordinator
- capability_registry: Discovery and registry for tools/capabilities
- safety_plugin: Real-time policy and guardrail enforcement
"""

from .harness_control_plane import (
    ExecutiveControlPlane,
    HarnessState,
    SafetyLevel,
    TaskRequest,
    SafetyGuardrail,
    HermesBridge,
)
from .continuous_dev import (
    DailyImprovementCron,
    CanaryDeploymentManager,
    ABTestingFramework,
    RollbackManager,
    ProgressDashboard,
)

__all__ = [
    "ExecutiveControlPlane",
    "HarnessState",
    "SafetyLevel",
    "TaskRequest",
    "SafetyGuardrail",
    "HermesBridge",
    "DailyImprovementCron",
    "CanaryDeploymentManager",
    "ABTestingFramework",
    "RollbackManager",
    "ProgressDashboard",
]
