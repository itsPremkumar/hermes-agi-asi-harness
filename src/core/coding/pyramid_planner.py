"""Test Pyramid — Multi-layer test generation."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TestLayer(str, Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    SYSTEM = "system"
    E2E = "e2e"
    CONTRACT = "contract"
    PROPERTY = "property"
    FUZZ = "fuzz"
    PERFORMANCE = "performance"
    SECURITY = "security"
    MIGRATION = "migration"
    RECOVERY = "recovery"

@dataclass
class TestSuite:
    id: str
    layer: TestLayer
    name: str
    tests: list[dict[str, Any]] = field(default_factory=list)
    coverage: float = 0.0

class TestPyramid:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.suites: dict[str, TestSuite] = {}
    
    def create_suite(self, layer: TestLayer, name: str) -> TestSuite:
        suite = TestSuite(id=str(uuid.uuid4()), layer=layer, name=name)
        self.suites[suite.id] = suite
        return suite
    
    def add_test(self, suite_id: str, name: str, test_code: str,
                 expected_result: Any = None) -> dict[str, Any]:
        test = {"name": name, "code": test_code, "expected": expected_result, "status": "pending"}
        if suite_id in self.suites:
            self.suites[suite_id].tests.append(test)
        return test
    
    def get_layers(self) -> list[TestLayer]:
        return list({s.layer for s in self.suites.values()})
    
    def get_total_tests(self) -> int:
        return sum(len(s.tests) for s in self.suites.values())
    
    def get_state(self) -> dict[str, Any]:
        return {"suites": len(self.suites), "total_tests": self.get_total_tests()}
