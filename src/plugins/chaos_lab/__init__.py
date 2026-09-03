"""ChaosLab — chaos engineering and fault injection."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExperimentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FaultType(str, Enum):
    LATENCY = "latency"
    ERROR = "error"
    TIMEOUT = "timeout"
    CORRUPTION = "corruption"


@dataclass
class Experiment:
    id: str
    name: str
    fault_type: FaultType
    target: str
    status: ExperimentStatus = ExperimentStatus.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)


class ChaosLab:
    """Run chaos experiments."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._experiments: dict[str, Experiment] = {}

    def create(self, name: str, fault_type: FaultType, target: str) -> Experiment:
        exp = Experiment(id=str(uuid.uuid4()), name=name, fault_type=fault_type, target=target)
        self._experiments[exp.id] = exp
        return exp

    def start(self, exp_id: str) -> bool:
        if exp_id in self._experiments:
            self._experiments[exp_id].status = ExperimentStatus.RUNNING
            return True
        return False

    def complete(self, exp_id: str) -> bool:
        if exp_id in self._experiments:
            self._experiments[exp_id].status = ExperimentStatus.COMPLETED
            return True
        return False

    def get(self, exp_id: str) -> Experiment | None:
        return self._experiments.get(exp_id)

    def list_all(self) -> list[Experiment]:
        return list(self._experiments.values())

    def count(self) -> int:
        return len(self._experiments)
