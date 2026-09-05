"""
HERMES INTELLIGENCE OS — UNIVERSAL RUNTIME ADAPTER SPI (v9)
===========================================================
Service Provider Interface (SPI) decoupling the sovereign Hermes Executive
from concrete execution frameworks:
- RuntimeAdapter: Abstract interface implemented by all execution substrates.
- ExecutionResult: Standardized execution telemetry returned to the kernel.
- Guarantees Hermes is completely runtime-agnostic and model-agnostic.
"""

from __future__ import annotations

import abc
import enum
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .cognitive_compiler import ExecutionPlanIR

logger = logging.getLogger("hermes.os.runtime_spi")


class ExecutionStatus(str, enum.Enum):
    """Lifecycle status of a runtime execution."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    INTERRUPTED = "interrupted"


@dataclass
class ExecutionResult:
    """Standardized result returned by any concrete RuntimeAdapter."""
    mission_id: str
    runtime_id: str
    status: ExecutionStatus
    completed_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[str] = field(default_factory=list)
    checkpoints_created: List[str] = field(default_factory=list)
    tokens_consumed: int = 0
    elapsed_seconds: float = 0.0
    proof: Dict[str, Any] = field(default_factory=dict)
    artifacts_produced: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.status == ExecutionStatus.COMPLETED

    @property
    def success(self) -> bool:
        return self.is_success

    @property
    def runtime_used(self) -> str:
        return self.runtime_id

    @property
    def duration_s(self) -> float:
        return self.elapsed_seconds

    @property
    def proof_hash(self) -> str:
        return self.proof.get("proof_hash", "")

    @property
    def waves_completed(self) -> List[int]:
        return self.metadata.get("waves_completed", [1])

    @property
    def step_outputs(self) -> Dict[str, Any]:
        return self.metadata.get("step_outputs", {})

    @property
    def worker_sandboxes(self) -> List[str]:
        return self.metadata.get("worker_sandboxes", [])

    @property
    def error(self) -> Optional[str]:
        return self.metadata.get("error")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "runtime_id": self.runtime_id,
            "status": self.status.value,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "checkpoints": self.checkpoints_created,
            "tokens_consumed": self.tokens_consumed,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "proof": self.proof,
            "artifacts": self.artifacts_produced,
            "metadata": self.metadata,
        }


class RuntimeAdapter(abc.ABC):
    """Universal Service Provider Interface for Hermes execution substrates."""

    @property
    @abc.abstractmethod
    def runtime_id(self) -> str:
        """Unique identifier (e.g. 'langgraph', 'deep_agents', 'composite_dual')."""
        ...

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """Human-readable description of the runtime substrate."""
        ...

    @abc.abstractmethod
    async def compile_execution_substrate(self, plan: ExecutionPlanIR) -> Any:
        """Transforms ExecutionPlanIR into the runtime's native format (e.g. StateGraph)."""
        ...

    @abc.abstractmethod
    async def execute_plan(self, plan: ExecutionPlanIR) -> ExecutionResult:
        """Executes the plan to completion and returns standardized result dictionary."""
        ...

    @abc.abstractmethod
    async def pause(self, mission_id: str, reason: str = "") -> bool:
        """Interrupts execution out-of-band."""
        ...

    @abc.abstractmethod
    async def resume(self, mission_id: str, checkpoint_id: Optional[str] = None) -> ExecutionResult:
        """Resumes execution from a saved checkpoint."""
        ...
