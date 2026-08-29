#!/usr/bin/env python3
"""
Debate Engine Plugin — Multi-perspective reasoning and debate
=============================================================
Features:
- Create debate rounds between perspectives
- Multiple reasoning agents with different stances
- Consensus building
- Argument scoring
- Synthesis of conclusions
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("hermes_debate_engine")

try:
    from core.runtime.plugin_base import PluginBase, PluginManifest, PluginPermissions, PluginState
    HAS_CORE = True
except ImportError:
    from enum import Enum as _Enum
    
    class PluginState(str, _Enum):
        REGISTERED = "registered"
        LOADED = "loaded"
        RUNNING = "running"
        PAUSED = "paused"
        ERROR = "error"
        UNLOADED = "unloaded"
    
    @dataclass
    class PluginPermissions:
        filesystem_read: str = "project"
        filesystem_write: str = "project"
        network_domains: List[str] = field(default_factory=list)
        shell_commands: List[str] = field(default_factory=list)
        secrets_access: str = "none"
        max_memory_mb: 512
        max_cpu_percent: 20
    
    @dataclass
    class PluginManifest:
        name: str = ""
        version: str = "1.0.0"
        description: str = ""
        license: str = "MIT"
        source: str = "internal"
        capabilities: List[str] = field(default_factory=list)
        cost: str = "free"
        permissions: PluginPermissions = field(default_factory=PluginPermissions)
        dependencies: List[str] = field(default_factory=list)
        path: Optional[Path] = None
    
    class PluginBase:
        manifest: PluginManifest
        
        def __init__(self, manifest: PluginManifest = None, kernel: Any = None):
            self.manifest = manifest or PluginManifest()
            self.kernel = kernel
            self.state = PluginState.REGISTERED
        
        async def load(self) -> bool:
            self.state = PluginState.LOADED
            return True
        
        async def start(self) -> bool:
            self.state = PluginState.RUNNING
            return True
        
        async def stop(self) -> bool:
            self.state = PluginState.UNLOADED
            return True
    
    HAS_CORE = False


class Perspective(str, Enum):
    """Debate perspectives."""
    PRO = "pro"
    CON = "con"
    NEUTRAL = "neutral"
    CRITICAL = "critical"
    CREATIVE = "creative"


@dataclass
class DebateRound:
    """A round in a debate."""
    round_num: int
    topic: str
    arguments: List[Dict[str, Any]] = field(default_factory=list)
    consensus: Optional[str] = None


@dataclass
class Debater:
    """A debater agent."""
    id: str
    name: str
    perspective: Perspective
    func: Optional[Callable] = None


class DebateEngine:
    """Debate engine for multi-perspective reasoning."""
    
    def __init__(self):
        self.debaters: Dict[str, Debater] = {}
        self.rounds: List[DebateRound] = []
        self.topic: Optional[str] = None
    
    def add_debater(self, name: str, perspective: str, func: Callable = None) -> str:
        """Add a debater."""
        debater_id = f"debater_{uuid.uuid4().hex[:8]}"
        self.debaters[debater_id] = Debater(
            id=debater_id,
            name=name,
            perspective=Perspective(perspective),
            func=func,
        )
        return debater_id
    
    def set_topic(self, topic: str):
        """Set the debate topic."""
        self.topic = topic
    
    async def run_round(self, round_num: int = 1) -> DebateRound:
        """Run a debate round."""
        if not self.topic:
            raise ValueError("Topic not set")
        
        round_obj = DebateRound(round_num=round_num, topic=self.topic)
        
        for debater in self.debaters.values():
            if debater.func:
                try:
                    if asyncio.iscoroutinefunction(debater.func):
                        argument = await debater.func(self.topic, debater.perspective.value)
                    else:
                        argument = debater.func(self.topic, debater.perspective.value)
                    
                    round_obj.arguments.append({
                        "debater": debater.name,
                        "perspective": debater.perspective.value,
                        "argument": argument,
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                except Exception as e:
                    round_obj.arguments.append({
                        "debater": debater.name,
                        "perspective": debater.perspective.value,
                        "argument": f"Error: {e}",
                        "timestamp": datetime.utcnow().isoformat(),
                    })
        
        self.rounds.append(round_obj)
        return round_obj
    
    def build_consensus(self, round_num: int = -1) -> str:
        """Build consensus from a round."""
        if not self.rounds:
            return "No rounds completed"
        
        round_obj = self.rounds[round_num]
        
        # Simple consensus: collect key points
        pro_points = []
        con_points = []
        neutral_points = []
        
        for arg in round_obj.arguments:
            perspective = arg["perspective"]
            text = arg["argument"]
            
            if perspective == Perspective.PRO.value:
                pro_points.append(text)
            elif perspective == Perspective.CON.value:
                con_points.append(text)
            else:
                neutral_points.append(text)
        
        consensus = f"Consensus for '{round_obj.topic}':\n\n"
        if pro_points:
            consensus += f"Supporting arguments ({len(pro_points)}):\n" + "\n".join(f"  + {p}" for p in pro_points) + "\n\n"
        if con_points:
            consensus += f"Opposing arguments ({len(con_points)}):\n" + "\n".join(f"  - {c}" for c in con_points) + "\n\n"
        if neutral_points:
            consensus += f"Neutral observations ({len(neutral_points)}):\n" + "\n".join(f"  = {n}" for n in neutral_points)
        
        round_obj.consensus = consensus
        return consensus
    
    def get_full_transcript(self) -> str:
        """Get full debate transcript."""
        if not self.topic:
            return "No debate started"
        
        transcript = f"=== DEBATE: {self.topic} ===\n\n"
        for i, round_obj in enumerate(self.rounds, 1):
            transcript += f"--- Round {i} ---\n"
            for arg in round_obj.arguments:
                transcript += f"[{arg['perspective'].upper()}] {arg['debater']}: {arg['argument']}\n\n"
            if round_obj.consensus:
                transcript += f"Consensus: {round_obj.consensus}\n\n"
        
        return transcript
    
    def score_arguments(self, round_num: int = -1) -> Dict[str, float]:
        """Score arguments by length and keyword density."""
        if not self.rounds:
            return {}
        
        round_obj = self.rounds[round_num]
        scores = {}
        
        for arg in round_obj.arguments:
            text = arg["argument"]
            # Score by length (proxy for detail) and keyword density
            words = text.split()
            score = len(words) * 0.1
            # Bonus for evidence keywords
            evidence_keywords = ["because", "data", "study", "evidence", "example", "therefore", "thus"]
            score += sum(2 for kw in evidence_keywords if kw in text.lower())
            scores[arg["debater"]] = score
        
        return scores


# ═══════════════════════════════════════════════════════════════════════════════════
# PLUGIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════════

class Plugin(PluginBase):
    """Debate Engine Plugin"""
    
    def __init__(self):
        self.state = PluginState.REGISTERED
        self.manifest = PluginManifest(
            name="debate_engine",
            version="1.0.0",
            description="Multi-perspective debate engine with consensus building and argument scoring",
            license="MIT",
            source="internal",
            capabilities=["debate", "multi_perspective", "consensus_building", "argument_scoring"],
            cost="free",
            permissions=PluginPermissions(
                filesystem_read="workspace",
                filesystem_write="workspace",
                network_domains=[],
                shell_commands=[],
                secrets_access="none",
                max_memory_mb=512,
                max_cpu_percent=20,
            ),
        )
        self.engine: Optional[DebateEngine] = None
    
    async def load(self) -> bool:
        self.engine = DebateEngine()
        self.state = PluginState.LOADED
        return True
    
    async def start(self) -> bool:
        if not self.engine:
            self.engine = DebateEngine()
        self.state = PluginState.RUNNING
        return True
    
    async def stop(self) -> bool:
        self.state = PluginState.UNLOADED
        return True
    
    async def health(self) -> Dict[str, Any]:
        return {
            "plugin": self.manifest.name,
            "version": self.manifest.version,
            "state": self.state.value,
            "healthy": self.state in (PluginState.LOADED, PluginState.RUNNING),
            "ready": self.engine is not None,
            "debaters": len(self.engine.debaters) if self.engine else 0,
        }
    
    # ── PUBLIC API ──────────────────────────────────────────────────────
    
    def add_debater(self, name: str, perspective: str, func: Callable = None) -> str:
        return self.engine.add_debater(name, perspective, func)
    
    def set_topic(self, topic: str):
        self.engine.set_topic(topic)
    
    async def run_round(self, round_num: int = 1) -> Dict[str, Any]:
        round_obj = await self.engine.run_round(round_num)
        return {
            "round": round_obj.round_num,
            "topic": round_obj.topic,
            "arguments": round_obj.arguments,
        }
    
    def build_consensus(self, round_num: int = -1) -> str:
        return self.engine.build_consensus(round_num)
    
    def get_full_transcript(self) -> str:
        return self.engine.get_full_transcript()
    
    def score_arguments(self, round_num: int = -1) -> Dict[str, float]:
        return self.engine.score_arguments(round_num)
    
    async def _run_with_perspectives(self, topic: str) -> Dict[str, Any]:
        """Convenience: run a pro/con debate on a topic with built-in perspectives."""
        def pro_arg(t, p):
            return f"In favor of {t}: it offers clear benefits, scalability, and measurable upside."
        def con_arg(t, p):
            return f"Against {t}: there are real risks, costs, and failure modes to consider."
        
        self.engine.set_topic(topic)
        self.engine.add_debater("Pro", "pro", pro_arg)
        self.engine.add_debater("Con", "con", con_arg)
        round_obj = await self.engine.run_round(1)
        consensus = self.engine.build_consensus()
        return {
            "topic": topic,
            "arguments": round_obj.arguments,
            "consensus": consensus,
        }
    
    def get_capabilities(self) -> List[str]:
        return self.manifest.capabilities
