
"""
Unified Brain Interface — every LLM call routes through ONE interface.

Extracted & enhanced from agx-harness-main:
- brain.py: HermesBrain, DeepAgentsPlanner, EchoBrain, PlannerBrain protocol

The brain never touches state directly; it only returns text.
The kernel decides what to do with the text.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import subprocess
import threading
from typing import Dict, List, Optional, Protocol
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class BrainError(RuntimeError):
    pass


@dataclass
class ModelResponse:
    content: str
    model: str
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    cached: bool = False


class PlannerBrain(Protocol):
    """Protocol for brain implementations."""
    def hypothesize(self, goal: str, context_bullets: List[str], **kw) -> str: ...
    def implement(self, hypothesis: str, goal: str, **kw) -> str: ...
    def plan(self, goal: str, criterion: str) -> dict: ...
    def research(self, goal: str, strategy: str, **kw) -> str: ...
    def critique(self, goal: str, hypothesis: str, **kw) -> str: ...
    def supervise(self, goal: str, criterion: str, trajectory: str, memory: str) -> str: ...


def _build_hermes_cmd(prompt: str, model: Optional[str] = None, toolset: Optional[str] = None) -> List[str]:
    """Assemble the Hermes CLI invocation."""
    cmd = ["hermes", "-z", prompt, "--accept-hooks"]
    if model:
        cmd += ["-m", model]
    if toolset:
        cmd += ["-t", toolset]
    return cmd


_ERROR_RE = re.compile(
    r"(?i)(^|\b)(http\s*40\d|unauthorized|not supported|api[ _-]?key|"
    r"model .* not|rate[ _-]?limit|forbidden)(\b|$)")


def _hermes(prompt: str, timeout: int = 600, model: Optional[str] = None, toolset: Optional[str] = None) -> str:
    """One shot through the Hermes CLI."""
    last_err: Optional[str] = None
    for _ in range(2):
        try:
            r = subprocess.run(_build_hermes_cmd(prompt, model, toolset),
                               capture_output=True, text=True, timeout=timeout)
            out = (r.stdout or "").strip()
            if r.returncode == 0 and out and not _ERROR_RE.search(out):
                return out
            last_err = "rc=%d err=%s" % (r.returncode, (r.stderr or out or "")[:200])
        except FileNotFoundError:
            raise BrainError("hermes CLI not on PATH")
        except subprocess.TimeoutExpired:
            last_err = "timeout after %ss" % timeout
    raise BrainError("hermes brain failed twice: %s" % last_err)


class HermesBrain:
    """Default brain: zero-key, free-model routing via Hermes CLI."""
    
    def __init__(self, max_hypothesis_chars: int = 400, model: Optional[str] = None,
                 research_toolset: Optional[str] = "web"):
        self.max_hypothesis_chars = max_hypothesis_chars
        self.model = model or os.environ.get("AGX_HERMES_MODEL")
        self.research_toolset = research_toolset
    
    def _ask(self, role: str, toolset: Optional[str] = None, **kw) -> str:
        prompt = self._build_prompt(role, **kw)
        return _hermes(prompt, model=self.model, toolset=toolset)
    
    def _build_prompt(self, role: str, **kw) -> str:
        """Build a prompt from role and context."""
        prompts = {
            "implementer": "Goal: {goal}\nCriterion: {criterion}\nContext: {context}\nResearch: {research}\nProvide a concrete implementation plan.",
            "coder": "Goal: {goal}\nHypothesis: {hypothesis}\nResearch: {research}\nWrite the implementation code.",
            "planner": "Goal: {goal}\nCriterion: {criterion}\nDecompose into sub-goals JSON.",
            "researcher": "Goal: {goal}\nStrategy: {strategy}\nPrior: {prior}\nGather key facts.",
            "critic": "Goal: {goal}\nHypothesis: {hypothesis}\nIdentify edge cases and vulnerabilities.",
            "supervisor": "Goal: {goal}\nTrajectory: {trajectory}\nMemory: {memory}\nProvide DIRECTIVE, STRATEGY, SUBGOALS.",
        }
        template = prompts.get(role, "Task: {goal}")
        try:
            return template.format(**kw)
        except (KeyError, IndexError):
            return template
    
    def hypothesize(self, goal: str, context_bullets: List[str] = None, **kw) -> str:
        ctx = "\n".join("- " + b for b in (context_bullets or [])[:12]) or "- (fresh start)"
        out = self._ask("implementer", goal=goal, criterion=kw.get("criterion", "(none)"),
                        context=ctx, research=kw.get("research", "(none)"))
        return out.splitlines()[0][:self.max_hypothesis_chars].strip()
    
    def implement(self, hypothesis: str, goal: str, **kw) -> str:
        return self._ask("coder", goal=goal, hypothesis=hypothesis,
                         research=kw.get("research", "(none)")).strip()
    
    def plan(self, goal: str, criterion: str) -> dict:
        out = self._ask("planner", goal=goal, criterion=criterion)
        start = out.find("{")
        end = out.rfind("}")
        if start < 0 or end <= start:
            return {"goal": goal, "sub_goals": []}
        try:
            obj = json.loads(out[start:end + 1])
            return obj if isinstance(obj, dict) else {"goal": goal, "sub_goals": []}
        except json.JSONDecodeError:
            return {"goal": goal, "sub_goals": []}
    
    def research(self, goal: str, strategy: str, prior: str = "", toolset: Optional[str] = None) -> str:
        return self._ask("researcher", toolset=toolset or self.research_toolset,
                         goal=goal, strategy=strategy, prior=prior or "(none)")
    
    def critique(self, goal: str, hypothesis: str, **kw) -> str:
        return self._ask("critic", goal=goal, hypothesis=hypothesis,
                         research=kw.get("research", "(none)"))
    
    def supervise(self, goal: str, criterion: str, trajectory: str, memory: str) -> str:
        return self._ask("supervisor", goal=goal, criterion=criterion,
                         trajectory=trajectory or "(none)", memory=memory or "(none)")


class EchoBrain:
    """Deterministic test brain — NEVER ships to production runs."""
    
    def __init__(self, hypotheses: List[str]):
        if os.environ.get("AGX_ALLOW_ECHO_BRAIN") != "1":
            raise BrainError("EchoBrain refused: set AGX_ALLOW_ECHO_BRAIN=1 (tests only)")
        self.hypotheses = hypotheses
        self._i = 0
        self._lock = threading.Lock()
    
    def hypothesize(self, goal: str, context_bullets: List[str] = None, **kw) -> str:
        with self._lock:
            h = self.hypotheses[self._i % len(self.hypotheses)]
            self._i += 1
        return h
    
    def plan(self, goal: str, criterion: str) -> dict:
        return {"goal": goal, "sub_goals": [{"id": "s1", "desc": "analyze"}, {"id": "s2", "desc": "implement"}]}
    
    def research(self, goal: str, strategy: str, **kw) -> str:
        return "KEY FACTS:\n- baseline approach exists\n- improvements available"
    
    def critique(self, goal: str, hypothesis: str, **kw) -> str:
        return "OK"
    
    def implement(self, hypothesis: str, goal: str, **kw) -> str:
        return ""
    
    def supervise(self, goal: str, criterion: str, trajectory: str, memory: str) -> str:
        return "DIRECTIVE: continue\nSTRATEGY: keep\nSUBGOALS: keep"
