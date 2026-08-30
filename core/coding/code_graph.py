"""
Code Graph — Build import/call/inheritance dependency graphs.

Graph types: imports, calls, inherits, implements, reads, writes, publishes,
subscribes, configures, tests, builds, deploys
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class NodeType(str, Enum):
    FILE = "file"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    VARIABLE = "variable"
    SERVICE = "service"
    DATABASE = "database"
    API_ENDPOINT = "api_endpoint"
    TEST = "test"


class RelationType(str, Enum):
    IMPORTS = "imports"
    CALLS = "calls"
    INHERITS = "inherits"
    IMPLEMENTS = "implements"
    READS = "reads"
    WRITES = "writes"
    PUBLISHES = "publishes"
    SUBSCRIBES = "subscribes"
    CONFIGURES = "configures"
    TESTS = "tests"
    BUILDS = "builds"
    DEPLOYS = "deploys"
    DEPENDS_ON = "depends_on"


@dataclass
class GraphNode:
    id: str
    name: str
    node_type: NodeType
    file_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    id: str
    source_id: str
    target_id: str
    relation: RelationType
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BlastRadius:
    """Result of blast radius analysis."""
    changed_node: str
    affected_nodes: List[str]
    affected_files: List[str]
    affected_services: List[str]
    affected_tests: List[str]
    risk_score: float


class CodeGraph:
    """Code dependency graph for impact analysis."""
    
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
    
    def add_node(self, name: str, node_type: NodeType,
                 file_path: str, metadata: Dict[str, Any] = None) -> GraphNode:
        node = GraphNode(
            id=str(uuid.uuid4()),
            name=name,
            node_type=node_type,
            file_path=file_path,
            metadata=metadata or {},
        )
        self.nodes[node.id] = node
        return node
    
    def add_edge(self, source_id: str, target_id: str,
                 relation: RelationType, metadata: Dict[str, Any] = None) -> GraphEdge:
        edge = GraphEdge(
            id=str(uuid.uuid4()),
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            metadata=metadata or {},
        )
        self.edges.append(edge)
        return edge
    
    def get_dependents(self, node_id: str) -> List[GraphNode]:
        """Get all nodes that depend on this node."""
        dependent_ids = {
            e.source_id for e in self.edges if e.target_id == node_id
        }
        return [self.nodes[nid] for nid in dependent_ids if nid in self.nodes]
    
    def get_dependencies(self, node_id: str) -> List[GraphNode]:
        """Get all nodes this node depends on."""
        dependency_ids = {
            e.target_id for e in self.edges if e.source_id == node_id
        }
        return [self.nodes[nid] for nid in dependency_ids if nid in self.nodes]
    
    def compute_blast_radius(self, changed_node_id: str) -> BlastRadius:
        """Compute the blast radius of changing a node."""
        visited = set()
        queue = [changed_node_id]
        affected_files = set()
        affected_services = set()
        affected_tests = set()
        
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            
            node = self.nodes.get(current)
            if not node:
                continue
            
            if node.node_type == NodeType.FILE:
                affected_files.add(node.file_path)
            elif node.node_type == NodeType.SERVICE:
                affected_services.add(node.name)
            elif node.node_type == NodeType.TEST:
                affected_tests.add(node.name)
            
            # Follow all outgoing edges
            for edge in self.edges:
                if edge.source_id == current and edge.target_id not in visited:
                    queue.append(edge.target_id)
        
        # Risk score based on number of affected nodes
        risk_score = min(1.0, len(visited) / max(len(self.nodes), 1))
        
        return BlastRadius(
            changed_node=changed_node_id,
            affected_nodes=list(visited - {changed_node_id}),
            affected_files=list(affected_files),
            affected_services=list(affected_services),
            affected_tests=list(affected_tests),
            risk_score=risk_score,
        )
    
    def find_path(self, source_id: str, target_id: str) -> List[GraphNode]:
        """Find path between two nodes using BFS."""
        if source_id == target_id:
            return [self.nodes[source_id]]
        
        visited = {source_id}
        queue = [(source_id, [source_id])]
        
        while queue:
            current, path = queue.pop(0)
            for edge in self.edges:
                if edge.source_id == current and edge.target_id not in visited:
                    new_path = path + [edge.target_id]
                    if edge.target_id == target_id:
                        return [self.nodes[nid] for nid in new_path]
                    visited.add(edge.target_id)
                    queue.append((edge.target_id, new_path))
        
        return []
    
    def get_orphaned_nodes(self) -> List[GraphNode]:
        """Find nodes with no connections."""
        connected_ids = set()
        for edge in self.edges:
            connected_ids.add(edge.source_id)
            connected_ids.add(edge.target_id)
        
        return [node for node_id, node in self.nodes.items() if node_id not in connected_ids]
    
    def get_state(self) -> Dict[str, Any]:
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "files": sum(1 for n in self.nodes.values() if n.node_type == NodeType.FILE),
            "classes": sum(1 for n in self.nodes.values() if n.node_type == NodeType.CLASS),
            "functions": sum(1 for n in self.nodes.values() if n.node_type == NodeType.FUNCTION),
            "services": sum(1 for n in self.nodes.values() if n.node_type == NodeType.SERVICE),
        }
