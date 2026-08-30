"""Hermes AGI/ASI Harness — Research Integration Layer (t_d62fcc6f)

Integrates 31 documented harness capabilities across 5 domains:
1. Intelligence (formal reasoning, discovery, GUI use, creative synthesis)
2. Infrastructure (scheduling, routing, plugins, self-healing)
3. Safety (guardrails, rate limits, anomaly detection, audit)
4. Integration (Hermes profiles, kanban, cron, MCP, mesh)
5. Operations (monitoring, trace, dashboard, SLOs, failover)

ASI Pathways Supported:
- A: Autonomous agent execution (self-directed goal pursuit)
- B: Human-AI collaborative (human-in-the-loop)
- C: Multi-agent swarm (decentralized coordination)
- D: Formal-verified reasoning (Lean/Z3 proofs)

Owner: @cto. Status: research-integrated, staged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class CapabilityDomain(Enum):
    """5 capability domains for the harness."""
    INTELLIGENCE = "intelligence"
    INFRASTRUCTURE = "infrastructure"
    SAFETY = "safety"
    INTEGRATION = "integration"
    OPERATIONS = "operations"


class ASIPathway(Enum):
    """4 supported ASI pathways."""
    AUTONOMOUS = "autonomous"
    COLLABORATIVE = "collaborative"
    SWARM = "swarm"
    FORMAL = "formal"


@dataclass
class CapabilitySpec:
    """A documented harness capability."""
    capability_id: str
    name: str
    domain: CapabilityDomain
    pathway: ASIPathway
    plugin_name: str
    description: str
    test_coverage_target: float = 0.90  # ≥90% per module
    criticality: str = "standard"  # standard, critical, mission_critical


class CapabilityRegistry:
    """Registry for the 31 documented harness capabilities."""
    
    def __init__(self):
        self._capabilities: dict[str, CapabilitySpec] = {}
        self._register_all_capabilities()
    
    @property
    def capabilities(self) -> dict[str, CapabilitySpec]:
        return dict(self._capabilities)
    
    def get_by_domain(self, domain: CapabilityDomain) -> list[CapabilitySpec]:
        return [c for c in self._capabilities.values() if c.domain == domain]
    
    def get_by_pathway(self, pathway: ASIPathway) -> list[CapabilitySpec]:
        return [c for c in self._capabilities.values() if c.pathway == pathway]
    
    def get_by_plugin(self, plugin_name: str) -> list[CapabilitySpec]:
        return [c for c in self._capabilities.values() if c.plugin_name == plugin_name]
    
    def count(self) -> int:
        return len(self._capabilities)
    
    def _register_all_capabilities(self) -> None:
        """Register all 31 documented capabilities."""
        
        # === INTELLIGENCE domain (8 capabilities) ===
        self._add("CAP-001", "Formal Reasoning Engine", CapabilityDomain.INTELLIGENCE, ASIPathway.FORMAL, "formal-reasoning", "Lean/Z3 proof engine with verifiable certificates")
        self._add("CAP-002", "Scientific Discovery Loop", CapabilityDomain.INTELLIGENCE, ASIPathway.AUTONOMOUS, "scientific-discovery", "Hypothesis generation to evidence synthesis loop")
        self._add("CAP-003", "Computer-Use GUI", CapabilityDomain.INTELLIGENCE, ASIPathway.COLLABORATIVE, "computer-use", "Screen perception, action planning, verification loop")
        self._add("CAP-004", "Creative Synthesis", CapabilityDomain.INTELLIGENCE, ASIPathway.AUTONOMOUS, "creative-synthesis", "Novel content generation with originality scoring")
        self._add("CAP-005", "Pattern Recognition", CapabilityDomain.INTELLIGENCE, ASIPathway.FORMAL, "pattern-recognition", "Statistical and structural pattern detection")
        self._add("CAP-006", "Causal Inference", CapabilityDomain.INTELLIGENCE, ASIPathway.AUTONOMOUS, "causal-inference", "Cause-effect relationship identification")
        self._add("CAP-007", "Meta-Learning", CapabilityDomain.INTELLIGENCE, ASIPathway.AUTONOMOUS, "meta-learning", "Learning-to-learn across tasks and domains")
        self._add("CAP-008", "Analogical Reasoning", CapabilityDomain.INTELLIGENCE, ASIPathway.FORMAL, "analogical-reasoning", "Cross-domain analogy generation and validation")
        
        # === INFRASTRUCTURE domain (7 capabilities) ===
        self._add("CAP-009", "Task Scheduling", CapabilityDomain.INFRASTRUCTURE, ASIPathway.AUTONOMOUS, "scheduler", "Priority-preemptive task scheduling with quotas")
        self._add("CAP-010", "Plugin Lifecycle", CapabilityDomain.INFRASTRUCTURE, ASIPathway.AUTONOMOUS, "plugin-manager", "Hot-load, unload, dependency resolution")
        self._add("CAP-011", "Self-Healing", CapabilityDomain.INFRASTRUCTURE, ASIPathway.AUTONOMOUS, "self-heal", "Automatic recovery from faults (99.9% uptime)")
        self._add("CAP-012", "Claimer Subsystem", CapabilityDomain.INFRASTRUCTURE, ASIPathway.AUTONOMOUS, "claimer", "Task routing with Law 1 exclusion")
        self._add("CAP-013", "Resource Quotas", CapabilityDomain.INFRASTRUCTURE, ASIPathway.AUTONOMOUS, "quota-manager", "CPU, memory, API call quotas per agent")
        self._add("CAP-014", "Load Balancing", CapabilityDomain.INFRASTRUCTURE, ASIPathway.SWARM, "load-balancer", "Distribute tasks across agents by capacity")
        self._add("CAP-015", "Message Routing", CapabilityDomain.INFRASTRUCTURE, ASIPathway.SWARM, "router", "A2AP message routing with discovery")
        
        # === SAFETY domain (6 capabilities) ===
        self._add("CAP-016", "Multi-Layer Guardrails", CapabilityDomain.SAFETY, ASIPathway.COLLABORATIVE, "safety-guard", "Input, execution, output guardrails")
        self._add("CAP-017", "Rate Limiting", CapabilityDomain.SAFETY, ASIPathway.AUTONOMOUS, "rate-limiter", "Per-minute, per-hour, concurrent limits")
        self._add("CAP-018", "Anomaly Detection", CapabilityDomain.SAFETY, ASIPathway.AUTONOMOUS, "anomaly-detector", "Z-score based behavioral anomaly detection")
        self._add("CAP-019", "Audit Trail", CapabilityDomain.SAFETY, ASIPathway.FORMAL, "audit-log", "Append-only immutable audit log")
        self._add("CAP-020", "Human Override", CapabilityDomain.SAFETY, ASIPathway.COLLABORATIVE, "human-override", "Human approval hooks for critical operations")
        self._add("CAP-021", "Capability Enforcement", CapabilityDomain.SAFETY, ASIPathway.AUTONOMOUS, "capability-enforce", "Unforgeable capability tokens per AgentOS model")
        
        # === INTEGRATION domain (5 capabilities) ===
        self._add("CAP-022", "Hermes Profile Lifecycle", CapabilityDomain.INTEGRATION, ASIPathway.AUTONOMOUS, "hermes-profiles", "Profile detection, lifecycle, role management")
        self._add("CAP-023", "Kanban Integration", CapabilityDomain.INTEGRATION, ASIPathway.COLLABORATIVE, "kanban", "Task board integration with kanban state sync")
        self._add("CAP-024", "Cron Scheduling", CapabilityDomain.INTEGRATION, ASIPathway.AUTONOMOUS, "cron", "Recurring task scheduling with cron expressions")
        self._add("CAP-025", "MCP Server Bridge", CapabilityDomain.INTEGRATION, ASIPathway.SWARM, "mcp-bridge", "Model Context Protocol server integration")
        self._add("CAP-026", "Agent Mesh P2P", CapabilityDomain.INTEGRATION, ASIPathway.SWARM, "agent-mesh", "Decentralized P2P coordination via A2AP")
        
        # === OPERATIONS domain (5 capabilities) ===
        self._add("CAP-027", "Observability Tracing", CapabilityDomain.OPERATIONS, ASIPathway.AUTONOMOUS, "tracer", "OpenTelemetry traces for every loop iteration")
        self._add("CAP-028", "SLO Monitoring", CapabilityDomain.OPERATIONS, ASIPathway.AUTONOMOUS, "slo-monitor", "Service level objective tracking and alerting")
        self._add("CAP-029", "Dashboard Rendering", CapabilityDomain.OPERATIONS, ASIPathway.COLLABORATIVE, "dashboard", "Single pane of glass for all agents and plugins")
        self._add("CAP-030", "Failover & Recovery", CapabilityDomain.OPERATIONS, ASIPathway.AUTONOMOUS, "failover", "Primary-backup failover with 60s takeover")
        self._add("CAP-031", "Test Coverage Enforcement", CapabilityDomain.OPERATIONS, ASIPathway.AUTONOMOUS, "coverage", "≥90% test coverage enforced per module")
    
    def _add(self, cid: str, name: str, domain: CapabilityDomain, 
             pathway: ASIPathway, plugin: str, desc: str) -> None:
        self._capabilities[cid] = CapabilitySpec(
            capability_id=cid,
            name=name,
            domain=domain,
            pathway=pathway,
            plugin_name=plugin,
            description=desc,
        )
