"""
Goal Contract Plugin — Formal Mission Definition with Success Criteria & Approval Gates

Every mission becomes a Goal Contract: desired_state, success_criteria,
failure_conditions, approval requirements, constraints.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class ApprovalLevel(str, Enum):
    AUTONOMOUS = "autonomous"
    LOGGED = "autonomous_and_logged"
    PREPARE = "prepare_for_approval"
    REQUIRED = "human_approval_required"


@dataclass
class GoalContract:
    id: str
    objective: str
    desired_state: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    failure_conditions: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    budget: Dict[str, Any] = field(default_factory=dict)
    approval: Dict[str, ApprovalLevel] = field(default_factory=dict)
    risk_level: str = "low"
    deadline: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "objective": self.objective,
            "desired_state": self.desired_state,
            "success_criteria": self.success_criteria,
            "failure_conditions": self.failure_conditions,
            "constraints": self.constraints,
            "budget": self.budget,
            "approval": {k: v.value for k, v in self.approval.items()},
            "risk_level": self.risk_level,
            "deadline": self.deadline,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GoalContract":
        d = dict(d)
        d["approval"] = {k: ApprovalLevel(v) for k, v in d.get("approval", {}).items()}
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class GoalCompiler:
    """Compiles a raw objective into a GoalContract with all fields."""

    def __init__(self):
        self._goal_counter = 0

    def compile(self, objective: str, **overrides) -> GoalContract:
        """Compile a raw objective into a GoalContract."""
        self._goal_counter += 1
        goal_id = f"GOAL-{self._goal_counter:04d}"

        # Infer risk level from objective keywords
        risk = self._infer_risk(objective)

        # Infer desired state from objective
        desired = overrides.get("desired_state", self._infer_desired_state(objective))

        # Infer success criteria
        criteria = overrides.get("success_criteria", self._infer_criteria(objective))

        # Infer failure conditions
        failures = overrides.get("failure_conditions", ["unsafe_action", "missing_dependency", "invalid_result"])

        contract = GoalContract(
            id=goal_id,
            objective=objective,
            desired_state=desired,
            success_criteria=criteria,
            failure_conditions=failures,
            constraints=overrides.get("constraints", {}),
            budget=overrides.get("budget", {"monetary_limit": 0, "token_limit": 100000}),
            approval=overrides.get("approval", self._infer_approvals(risk)),
            risk_level=risk,
            deadline=overrides.get("deadline"),
            metadata=overrides.get("metadata", {}),
        )
        return contract

    def _infer_risk(self, objective: str) -> str:
        obj = objective.lower()
        if any(w in obj for w in ["delete", "remove", "drop", "destroy", "spend", "money", "financial", "production", "deploy", "publish"]):
            return "critical"
        elif any(w in obj for w in ["modify", "change", "update", "send", "email", "message", "post", "api", "remote"]):
            return "high"
        elif any(w in obj for w in ["write", "create", "build", "implement", "test", "run"]):
            return "medium"
        return "low"

    def _infer_desired_state(self, objective: str) -> List[str]:
        obj = objective.lower()
        if "write" in obj or "file" in obj:
            return ["file exists with correct content"]
        if "code" in obj or "implement" in obj:
            return ["code is implemented", "code compiles/runs"]
        if "research" in obj:
            return ["research report exists with sources"]
        if "deploy" in obj:
            return ["application is deployed"]
        return ["objective is satisfied"]

    def _infer_criteria(self, objective: str) -> List[str]:
        return ["functional", "tested", "verified"]

    def _infer_approvals(self, risk: str) -> Dict[str, ApprovalLevel]:
        if risk == "critical":
            return {
                "financial_transaction": ApprovalLevel.REQUIRED,
                "destructive_operation": ApprovalLevel.REQUIRED,
                "external_publication": ApprovalLevel.REQUIRED,
            }
        elif risk == "high":
            return {
                "financial_transaction": ApprovalLevel.REQUIRED,
                "destructive_operation": ApprovalLevel.PREPARE,
                "external_publication": ApprovalLevel.PREPARE,
            }
        elif risk == "medium":
            return {
                "financial_transaction": ApprovalLevel.REQUIRED,
                "destructive_operation": ApprovalLevel.LOGGED,
                "external_publication": ApprovalLevel.LOGGED,
            }
        return {
            "financial_transaction": ApprovalLevel.LOGGED,
            "destructive_operation": ApprovalLevel.LOGGED,
            "external_publication": ApprovalLevel.AUTONOMOUS,
        }


class GoalContractPlugin:
    def __init__(self):
        self.compiler = GoalCompiler()
        self._contracts: Dict[str, GoalContract] = {}

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {"status": "healthy", "contracts_created": len(self._contracts)}

    def create_contract(self, objective: str, **overrides) -> GoalContract:
        contract = self.compiler.compile(objective, **overrides)
        self._contracts[contract.id] = contract
        return contract

    def get_contract(self, goal_id: str) -> Optional[GoalContract]:
        return self._contracts.get(goal_id)

    @property
    def contract_count(self) -> int:
        return len(self._contracts)


async def create(kernel=None):
    return GoalContractPlugin()
