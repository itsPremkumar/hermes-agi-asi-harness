"""
Environment Discovery — When Hermes encounters a new application.

NEW ENVIRONMENT → DISCOVER INTERFACES → DISCOVER CAPABILITIES →
DISCOVER STATE → DISCOVER PERMISSIONS → DISCOVER RISKS →
BUILD ENVIRONMENT MODEL → REGISTER
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DiscoveryStage(str, Enum):
    INIT = "init"
    INTERFACE_DISCOVERY = "interface_discovery"
    CAPABILITY_DISCOVERY = "capability_discovery"
    STATE_DISCOVERY = "state_discovery"
    PERMISSION_DISCOVERY = "permission_discovery"
    RISK_DISCOVERY = "risk_discovery"
    MODEL_BUILDING = "model_building"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DiscoveredInterface:
    name: str
    type: str  # api, gui, cli, file, network
    endpoint: Optional[str] = None
    protocol: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveredCapability:
    name: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)


@dataclass
class DiscoveredRisk:
    type: str
    severity: float
    description: str
    mitigation: str = ""


@dataclass
class DiscoveryResult:
    id: str
    environment_name: str
    stage: DiscoveryStage
    interfaces: List[DiscoveredInterface]
    capabilities: List[DiscoveredCapability]
    state: Dict[str, Any]
    permissions: Dict[str, List[str]]
    risks: List[DiscoveredRisk]
    model: Optional[Dict[str, Any]] = None
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    error: Optional[str] = None


class EnvironmentDiscovery:
    """
    Discover and model new environments.
    
    When Hermes encounters a new application:
    1. Discover interfaces (API, GUI, CLI, file, network)
    2. Discover capabilities (what actions are possible)
    3. Discover state (current state of the environment)
    4. Discover permissions (what is allowed)
    5. Discover risks (what could go wrong)
    6. Build environment model
    7. Register
    """

    def __init__(self):
        self.results: Dict[str, DiscoveryResult] = {}
        self._discovery_count = 0

    def start_discovery(self, environment_name: str) -> DiscoveryResult:
        result = DiscoveryResult(
            id=str(uuid.uuid4()),
            environment_name=environment_name,
            stage=DiscoveryStage.INIT,
            interfaces=[],
            capabilities=[],
            state={},
            permissions={},
            risks=[],
        )
        self.results[result.id] = result
        self._discovery_count += 1
        return result

    def discover_interfaces(self, discovery_id: str,
                            interfaces: List[DiscoveredInterface]) -> DiscoveryResult:
        result = self.results.get(discovery_id)
        if not result:
            raise ValueError(f"Discovery {discovery_id} not found")
        
        result.interfaces = interfaces
        result.stage = DiscoveryStage.INTERFACE_DISCOVERY
        return result

    def discover_capabilities(self, discovery_id: str,
                              capabilities: List[DiscoveredCapability]) -> DiscoveryResult:
        result = self.results.get(discovery_id)
        if not result:
            raise ValueError(f"Discovery {discovery_id} not found")
        
        result.capabilities = capabilities
        result.stage = DiscoveryStage.CAPABILITY_DISCOVERY
        return result

    def discover_state(self, discovery_id: str, state: Dict[str, Any]) -> DiscoveryResult:
        result = self.results.get(discovery_id)
        if not result:
            raise ValueError(f"Discovery {discovery_id} not found")
        
        result.state = state
        result.stage = DiscoveryStage.STATE_DISCOVERY
        return result

    def discover_permissions(self, discovery_id: str,
                             permissions: Dict[str, List[str]]) -> DiscoveryResult:
        result = self.results.get(discovery_id)
        if not result:
            raise ValueError(f"Discovery {discovery_id} not found")
        
        result.permissions = permissions
        result.stage = DiscoveryStage.PERMISSION_DISCOVERY
        return result

    def discover_risks(self, discovery_id: str,
                       risks: List[DiscoveredRisk]) -> DiscoveryResult:
        result = self.results.get(discovery_id)
        if not result:
            raise ValueError(f"Discovery {discovery_id} not found")
        
        result.risks = risks
        result.stage = DiscoveryStage.RISK_DISCOVERY
        return result

    def build_model(self, discovery_id: str) -> DiscoveryResult:
        result = self.results.get(discovery_id)
        if not result:
            raise ValueError(f"Discovery {discovery_id} not found")
        
        result.model = {
            "environment_name": result.environment_name,
            "interfaces": [{"name": i.name, "type": i.type} for i in result.interfaces],
            "capabilities": [{"name": c.name, "action": c.action} for c in result.capabilities],
            "state": result.state,
            "permissions": result.permissions,
            "risks": [{"type": r.type, "severity": r.severity} for r in result.risks],
        }
        result.stage = DiscoveryStage.COMPLETED
        result.completed_at = time.time()
        return result

    def get_result(self, discovery_id: str) -> Optional[DiscoveryResult]:
        return self.results.get(discovery_id)

    def get_all_results(self) -> List[DiscoveryResult]:
        return list(self.results.values())

    def get_state(self) -> Dict[str, Any]:
        return {
            "total_discoveries": self._discovery_count,
            "completed": sum(1 for r in self.results.values() if r.stage == DiscoveryStage.COMPLETED),
            "in_progress": sum(1 for r in self.results.values() if r.stage != DiscoveryStage.COMPLETED),
        }
