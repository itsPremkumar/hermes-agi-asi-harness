"""
jit_harness.py — Just-In-Time (JIT) Harness Configuration Generator

Dynamically synthesizes task-specific harness parameters for optimal execution.
Analyzes task descriptions and generates optimal execution profiles.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class TaskProfile:
    """Optimal execution profile for a task."""
    domain: str
    complexity_score: float  # 0.0 to 1.0
    recommended_temperature: float
    max_steps: int
    required_tools: list[str] = field(default_factory=list)
    verification_mode: str = "standard"
    estimated_duration_seconds: int = 30


class JITHarnessGenerator:
    """
    JIT Harness Generator — analyzes task descriptions and produces
    optimal execution profiles.
    """

    DOMAIN_PATTERNS = {
        "software_engineering": {
            "keywords": ["code", "refactor", "bug", "python", "test", "build", "implement", "function", "class", "module", "write file", "save file"],
            "temperature": 0.1,
            "steps": 25,
            "complexity": 0.8,
            "tools": ["file_read", "file_write", "python_exec", "shell", "ast_verifier"],
            "verification": "strict_ast",
            "duration": 60,
        },
        "deep_research": {
            "keywords": ["research", "investigate", "compare", "paper", "study", "analyze", "literature"],
            "temperature": 0.3,
            "steps": 20,
            "complexity": 0.7,
            "tools": ["web_search", "browser", "knowledge_graph", "memory_search"],
            "verification": "evidence_graph",
            "duration": 300,
        },
        "formal_proofs": {
            "keywords": ["math", "proof", "theorem", "crypto", "verify", "formal", "invariant", "lemma", "prove", "prove", "demonstrate"],
            "temperature": 0.0,
            "steps": 30,
            "complexity": 0.95,
            "tools": ["formal_verifier", "symbolic_solver", "ast_verifier"],
            "verification": "formal_invariants",
            "duration": 120,
        },
        "data_analysis": {
            "keywords": ["analyze", "data", "chart", "graph", "plot", "statistics", "visualize"],
            "temperature": 0.2,
            "steps": 15,
            "complexity": 0.6,
            "tools": ["python_exec", "file_read", "file_write", "shell"],
            "verification": "data_integrity",
            "duration": 90,
        },
        "creative": {
            "keywords": ["create story", "compose song", "design poster", "draw", "generate art"],
            "temperature": 0.7,
            "steps": 15,
            "complexity": 0.55,
            "tools": ["file_write", "memory_search"],
            "verification": "creative_review",
            "duration": 60,
        },
        "optimization": {
            "keywords": ["optimize", "improve", "minimize", "maximize", "efficiency", "fastest"],
            "temperature": 0.4,
            "steps": 20,
            "complexity": 0.75,
            "tools": ["python_exec", "evolution_engine", "shell"],
            "verification": "benchmark",
            "duration": 120,
        },
        "general": {
            "keywords": [],
            "temperature": 0.2,
            "steps": 15,
            "complexity": 0.5,
            "tools": ["file_read", "file_write", "python_exec"],
            "verification": "standard",
            "duration": 60,
        },
    }

    def analyze_task(self, task_description: str) -> TaskProfile:
        """
        Analyzes a task description and generates an optimal execution profile.
        """
        t_low = task_description.lower()

        best_domain = "general"
        best_score = 0.0

        for domain, config in self.DOMAIN_PATTERNS.items():
            if domain == "general":
                continue
            score = sum(1 for w in config["keywords"] if w in t_low) / len(config["keywords"])
            if score > best_score:
                best_score = score
                best_domain = domain

        domain_config = self.DOMAIN_PATTERNS[best_domain]
        complexity = domain_config["complexity"]

        # Adjust complexity based on task length and detail
        if len(task_description) > 200:
            complexity = min(1.0, complexity + 0.1)
        if "please" in t_low or "could you" in t_low:
            complexity = max(0.3, complexity - 0.05)

        return TaskProfile(
            domain=best_domain,
            complexity_score=round(complexity, 2),
            recommended_temperature=domain_config["temperature"],
            max_steps=domain_config["steps"],
            required_tools=domain_config["tools"],
            verification_mode=domain_config["verification"],
            estimated_duration_seconds=domain_config["duration"],
        )

    def get_all_domains(self) -> list[str]:
        """Returns all available domain names."""
        return list(self.DOMAIN_PATTERNS.keys())


class JITHarnessPlugin:
    """Plugin wrapper for JITHarnessGenerator."""

    def __init__(self, kernel=None):
        self.state = "started"
        self.kernel = kernel
        self.generator = JITHarnessGenerator()
        self.manifest = type('Manifest', (), {'name': 'jit_harness', 'version': '1.0.0'})()

    async def load(self):
        return True

    async def start(self):
        return True

    async def stop(self):
        return True

    async def health(self):
        return {
            "status": "healthy",
            "plugin": "jit_harness",
            "version": "1.0.0",
            "state": self.state,
            "healthy": True,
            "domains": len(self.generator.get_all_domains()),
        }

    def get_capabilities(self):
        return ["task_profiling", "harness_synthesis", "domain_detection"]

    def analyze_task(self, task_description: str) -> TaskProfile:
        return self.generator.analyze_task(task_description)


async def create(kernel=None) -> JITHarnessPlugin:
    """Factory function for kernel integration."""
    plugin = JITHarnessPlugin(kernel)
    await plugin.load()
    await plugin.start()
    return plugin
