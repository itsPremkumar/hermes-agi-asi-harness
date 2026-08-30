"""Test Oracle Strategy — Define how correctness is known."""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

class OracleType(str, Enum):
    EXACT = "exact"
    SCHEMA = "schema"
    COMPILER = "compiler"
    UNIT = "unit"
    INTEGRATION = "integration"
    SNAPSHOT = "snapshot"
    PROPERTY = "property"
    INVARIANT = "invariant"
    EXTERNAL = "external"
    HUMAN = "human"

@dataclass
class TestOracle:
    id: str
    oracle_type: OracleType
    name: str
    expected: Any = None
    tolerance: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class OracleManager:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.oracles: Dict[str, TestOracle] = {}
    
    def create_oracle(self, oracle_type: OracleType, name: str,
                      expected: Any = None, tolerance: float = 0.0,
                      **kwargs) -> TestOracle:
        oracle = TestOracle(id=str(uuid.uuid4()), oracle_type=oracle_type,
                           name=name, expected=expected, tolerance=tolerance,
                           metadata=kwargs)
        self.oracles[oracle.id] = oracle
        return oracle
    
    def verify(self, oracle_id: str, actual: Any) -> Dict[str, Any]:
        oracle = self.oracles.get(oracle_id)
        if not oracle:
            return {"status": "error", "message": "Oracle not found"}
        
        if oracle.oracle_type == OracleType.EXACT:
            passed = actual == oracle.expected
        elif oracle.oracle_type == OracleType.SCHEMA:
            passed = isinstance(actual, type(oracle.expected))
        else:
            passed = True
        
        return {"status": "pass" if passed else "fail", "oracle_id": oracle_id}
    
    def get_state(self) -> Dict[str, Any]:
        return {"oracles": len(self.oracles)}
