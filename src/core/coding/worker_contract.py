"""Worker Contract — Bounded context for each agent."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkerContract:
    id: str
    mission_id: str
    task_id: str
    objective: str
    repository_snapshot: str
    relevant_files: list[str]
    constraints: list[str]
    acceptance_tests: list[str]
    allowed_tools: list[str]
    risk_level: str
    output_artifacts: list[str]
    escalation_rules: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

class ContractManager:
    def __init__(self):
        self.contracts: dict[str, WorkerContract] = {}
    
    def create_contract(self, mission_id: str, task_id: str, objective: str,
                        repository_snapshot: str, relevant_files: list[str],
                        constraints: list[str], acceptance_tests: list[str],
                        allowed_tools: list[str], risk_level: str = "medium",
                        output_artifacts: list[str] | None = None,
                        escalation_rules: list[str] | None = None, **kwargs) -> WorkerContract:
        contract = WorkerContract(
            id=str(uuid.uuid4()), mission_id=mission_id, task_id=task_id,
            objective=objective, repository_snapshot=repository_snapshot,
            relevant_files=relevant_files, constraints=constraints,
            acceptance_tests=acceptance_tests, allowed_tools=allowed_tools,
            risk_level=risk_level,
            output_artifacts=output_artifacts or [],
            escalation_rules=escalation_rules or [],
            metadata=kwargs,
        )
        self.contracts[contract.id] = contract
        return contract
    
    def get_state(self) -> dict[str, Any]:
        return {"contracts": len(self.contracts)}
