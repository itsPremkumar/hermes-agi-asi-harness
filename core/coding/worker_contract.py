"""Worker Contract — Bounded context for each agent."""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

@dataclass
class WorkerContract:
    id: str
    mission_id: str
    task_id: str
    objective: str
    repository_snapshot: str
    relevant_files: List[str]
    constraints: List[str]
    acceptance_tests: List[str]
    allowed_tools: List[str]
    risk_level: str
    output_artifacts: List[str]
    escalation_rules: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

class ContractManager:
    def __init__(self):
        self.contracts: Dict[str, WorkerContract] = {}
    
    def create_contract(self, mission_id: str, task_id: str, objective: str,
                        repository_snapshot: str, relevant_files: List[str],
                        constraints: List[str], acceptance_tests: List[str],
                        allowed_tools: List[str], risk_level: str = "medium",
                        output_artifacts: List[str] = None,
                        escalation_rules: List[str] = None, **kwargs) -> WorkerContract:
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
    
    def get_state(self) -> Dict[str, Any]:
        return {"contracts": len(self.contracts)}
