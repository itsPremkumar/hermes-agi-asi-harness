"""
Hermes AGI/ASI Harness — Core Source Package.
=============================================

This directory houses the unified, modular, production-grade harness runtime:

Kernel & Core Runtime:
- hermes_agi: Primary public Harness API, CLI, real plugins, planning, and workflow engine
- core: Foundational runtime kernel (HermesKernel), supervisor, memory, cognition, mission compiler
- harnix: LangGraph state machine runtime and execution nodes
- harness: Harness engine, plugin lifecycle, telemetry, registry

Autonomous Engines & Operations:
- engines: Autonomous execution engines (control plane, ultimate, supervisor, continuous dev)
- hermes_asi_master: 24/7 Watchdog, scheduler, and cron runtime

Agent Swarm & Capabilities:
- agents: 26 specialized bot profiles & swarm implementations (coder, researcher, verifier, executive)
- plugins: 130+ capability plugin ecosystem (tool plane, cognitive, safety, integration)
- tools: Tool registries and execution plane

Domain-Specific Modules:
- arc_agi_3: ARC-AGI solver engine
- daily_improvement: Continuous improvement cycle & scheduler
- deep_research: Deep research synthesis and reporting
- diagnostics: Runtime inspection & diagnostics
- mesh: Consensus engine and message router
- operations: Watchdog, scheduler, checkpointing, economic ledger
- research: Research synthesis
- safety: Risk assessor, policy enforcer, threat modeler
- security: Security validator & audit
- training: Model self-training pipeline
- verification: Formal verification & proofs
"""

__version__ = "2.0.0"

# Primary Entry Points
try:
    from .agents import DEFAULT_ROLES, Agent, Role
    from .core.runtime.kernel import HermesKernel, KernelConfig
    from .engines import DailyImprovementCron, ExecutiveControlPlane
    from .hermes_agi import Config, Harness, load_config
except ImportError:
    pass
