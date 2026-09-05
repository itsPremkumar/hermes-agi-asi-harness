"""Quality Gates - 7 gates from requirement to production verification."""
from __future__ import annotations

import uuid
from enum import Enum
from typing import Any


class Gate(str, Enum):
    REQUIREMENT = "requirement"
    ARCHITECTURE = "architecture"
    IMPLEMENTATION = "implementation"
    TEST = "test"
    SECURITY = "security"
    DEPLOYMENT = "deployment"
    PRODUCTION = "production"

class QualityGates:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.gates: dict[str, bool] = {g.value: False for g in Gate}
    
    def pass_gate(self, gate: Gate):
        self.gates[gate.value] = True
    
    def all_passed(self) -> bool:
        return all(self.gates.values())
    
    def get_pending(self) -> list[str]:
        return [g for g, passed in self.gates.items() if not passed]
    
    def get_state(self) -> dict[str, Any]:
        return {"passed": sum(1 for v in self.gates.values() if v), "pending": self.get_pending()}
