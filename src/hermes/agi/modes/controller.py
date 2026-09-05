"""
Hermes AGI/ASI Harness — Adaptive Spatiotemporal Runtime Modes.

Inspired by DeepSeek Harness (dsh):
Dynamically shifts the agent's operating mode, mounting appropriate plugins,
scaling compute budgets, and configuring isolation based on task complexity.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("hermes.modes.controller")


class RuntimeMode(str, Enum):
    """Spatiotemporal execution modes for the harness."""
    REACTIVE = "reactive"            # Low-latency, direct tool execution
    DEEP_REASON = "deep_reason"      # MCTS Tree-of-Thoughts + Adversarial Debate Mesh
    ENDURANCE_CODE = "endurance_code"# gnhf branch isolation + in-harness compiler repair
    SELF_EVOLVE = "self_evolve"      # Closed-Loop Darwinian AVO Self-Evolution


@dataclass
class ModeConfig:
    """Active environmental configuration determined by the runtime mode."""
    mode: RuntimeMode
    max_compute_budget_steps: int
    use_branch_isolation: bool
    enable_mcts: bool
    enable_adversarial_debate: bool
    enable_in_harness_repair: bool
    enable_anti_goodhart: bool
    tool_whitelist: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "max_compute_budget_steps": self.max_compute_budget_steps,
            "use_branch_isolation": self.use_branch_isolation,
            "enable_mcts": self.enable_mcts,
            "enable_adversarial_debate": self.enable_adversarial_debate,
            "enable_in_harness_repair": self.enable_in_harness_repair,
            "enable_anti_goodhart": self.enable_anti_goodhart,
            "tool_whitelist": self.tool_whitelist,
        }


class ModeController:
    """
    Classifies incoming objectives and dynamically configures the harness
    operating mode to maximize throughput, compute efficiency, and safety.
    """

    def __init__(self, default_mode: RuntimeMode = RuntimeMode.REACTIVE):
        self.default_mode = default_mode

    def classify_task(self, task: str) -> RuntimeMode:
        """Analyze intent and classify into the optimal runtime mode."""
        t = task.lower().strip()

        # 1. Check for Self-Evolution
        if any(kw in t for kw in ("evolve", "self-improve", "darwinian", "optimize harness", "avo", "bottleneck")):
            return RuntimeMode.SELF_EVOLVE

        # 2. Check for Endurance Coding / Long-Horizon Work
        if any(kw in t for kw in ("refactor", "overnight", "endurance", "implement module", "test coverage", "fix bug", "suite")):
            return RuntimeMode.ENDURANCE_CODE

        # 3. Check for Deep Reasoning / Algorithmic Puzzles
        if any(kw in t for kw in ("prove", "puzzle", "consensus", "arc", "theorem", "deliberate", "architecture", "tradeoff", "hypothes")):
            return RuntimeMode.DEEP_REASON

        return RuntimeMode.REACTIVE

    def configure_mode(self, mode: RuntimeMode) -> ModeConfig:
        """Instantiate the spatiotemporal configuration for the chosen mode."""
        if mode == RuntimeMode.DEEP_REASON:
            return ModeConfig(
                mode=mode,
                max_compute_budget_steps=50,
                use_branch_isolation=False,
                enable_mcts=True,
                enable_adversarial_debate=True,
                enable_in_harness_repair=False,
                enable_anti_goodhart=True,
                tool_whitelist=["thinking_engine", "research_agent", "debate_mesh", "verification_engine"],
            )
        elif mode == RuntimeMode.ENDURANCE_CODE:
            return ModeConfig(
                mode=mode,
                max_compute_budget_steps=100,
                use_branch_isolation=True,
                enable_mcts=False,
                enable_adversarial_debate=True,
                enable_in_harness_repair=True,
                enable_anti_goodhart=True,
                tool_whitelist=["git_tool", "filesystem_tool", "python_tool", "shell_tool", "coding_loop"],
            )
        elif mode == RuntimeMode.SELF_EVOLVE:
            return ModeConfig(
                mode=mode,
                max_compute_budget_steps=200,
                use_branch_isolation=True,
                enable_mcts=True,
                enable_adversarial_debate=True,
                enable_in_harness_repair=True,
                enable_anti_goodhart=True,
                tool_whitelist=["avo_engine", "benchmarks", "git_tool", "supervisor", "knowledge_base"],
            )
        else:  # REACTIVE
            return ModeConfig(
                mode=mode,
                max_compute_budget_steps=10,
                use_branch_isolation=False,
                enable_mcts=False,
                enable_adversarial_debate=False,
                enable_in_harness_repair=False,
                enable_anti_goodhart=False,
                tool_whitelist=["filesystem_tool", "shell_tool", "python_tool"],
            )
