"""
Hermes Unified Package
======================
Exposes the main submodules:
- hermes.os: Hermes Intelligence OS (v8 Final Architecture)
- hermes.agi: Hermes AGI/ASI Harness (Unified AI Agent Runtime)
"""

from .os import (
    HermesIntelligenceOS,
    PersonaSystem,
    LocalLLMRuntime,
    VerificationGates,
    GitLineageDAG,
    StagnationSupervisor,
    AVOEvolutionEngine,
)
from .agi import (
    Harness,
    Config,
    load_config,
    AdversarialVerifier,
    AgentTeamCoordinator,
    run_agent_team,
)

__version__ = "2.0.0"

__all__ = [
    # Core
    "HermesIntelligenceOS",
    "Harness",
    "Config",
    "load_config",
    # New: Persona System (Mercury Agent)
    "PersonaSystem",
    # New: Local LLM Runtime (Atomic Agent)
    "LocalLLMRuntime",
    # New: Verification Gates (Fable-5)
    "VerificationGates",
    # New: AVO Lineage + Supervisor (NVIDIA)
    "GitLineageDAG",
    "StagnationSupervisor",
    "AVOEvolutionEngine",
    # New: Adversarial Verification (Fable-5/Apodex)
    "AdversarialVerifier",
    # New: Agent Team Coordinator (Apodex)
    "AgentTeamCoordinator",
    "run_agent_team",
    # Submodules
    "os",
    "agi",
]