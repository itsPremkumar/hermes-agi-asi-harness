"""Test-First Planning — Requirement → Acceptance Criteria → Test Design → Implementation."""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

class TestFirstPlanner:
    def __init__(self):
        self.id = str(uuid.uuid4())
    
    def plan(self, requirement: str, acceptance_criteria: List[str]) -> Dict[str, Any]:
        """Plan implementation from requirements using test-first approach."""
        tests = []
        for criterion in acceptance_criteria:
            tests.append({
                "criterion": criterion,
                "test_name": f"test_{criterion.lower().replace(' ', '_')}",
                "status": "pending",
            })
        
        return {
            "requirement": requirement,
            "acceptance_criteria": acceptance_criteria,
            "tests": tests,
            "implementation": None,
            "status": "planned",
        }
    
    def get_state(self) -> Dict[str, Any]:
        return {"id": self.id}
