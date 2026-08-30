"""
Requirement Traceability Graph — Requirement → Design → Implementation → Test → Evidence
"""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

class TraceNodeType(str, Enum):
    REQUIREMENT = "requirement"
    DESIGN_DECISION = "design_decision"
    IMPLEMENTATION = "implementation"
    TEST = "test"
    EVIDENCE = "evidence"

class TraceStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VERIFIED = "verified"
    FAILED = "failed"

@dataclass
class TraceNode:
    id: str
    node_type: TraceNodeType
    description: str
    status: TraceStatus = TraceStatus.PENDING
    references: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TraceEdge:
    source_id: str
    target_id: str
    relationship: str

class RequirementTraceGraph:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.nodes: Dict[str, TraceNode] = {}
        self.edges: List[TraceEdge] = []
    
    def add_node(self, node_type: TraceNodeType, description: str,
                 status: TraceStatus = TraceStatus.PENDING,
                 metadata: Dict[str, Any] = None) -> TraceNode:
        node = TraceNode(id=str(uuid.uuid4()), node_type=node_type,
                        description=description, status=status,
                        metadata=metadata or {})
        self.nodes[node.id] = node
        return node
    
    def add_edge(self, source_id: str, target_id: str, relationship: str):
        self.edges.append(TraceEdge(source_id=source_id, target_id=target_id,
                                    relationship=relationship))
    
    def get_unverified(self) -> List[TraceNode]:
        return [n for n in self.nodes.values() if n.status != TraceStatus.VERIFIED]
    
    def get_coverage(self) -> Dict[str, Any]:
        total = len(self.nodes)
        verified = sum(1 for n in self.nodes.values() if n.status == TraceStatus.VERIFIED)
        return {"total": total, "verified": verified,
                "coverage": verified / max(total, 1)}
    
    def get_state(self) -> Dict[str, Any]:
        return {"nodes": len(self.nodes), "edges": len(self.edges),
                "coverage": self.get_coverage()}
