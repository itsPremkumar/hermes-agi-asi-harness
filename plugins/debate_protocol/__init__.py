"""
Debate Protocol Plugin — Structured Multi-Agent Debate

For difficult decisions: proposal → agent A → B → C → critic → counterargument
→ evidence check → executive decision.
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Position(str, Enum):
    PRO = "pro"
    CON = "con"
    ABSTAIN = "abstain"


@dataclass
class DebateArgument:
    agent_id: str
    position: Position
    argument: str
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.5
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "position": self.position.value,
            "argument": self.argument,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


@dataclass
class DebateOutcome:
    debate_id: str
    topic: str
    arguments: list[DebateArgument] = field(default_factory=list)
    winner: Position | None = None
    consensus_reached: bool = False
    executive_decision: str = ""
    final_confidence: float = 0.0
    duration_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "debate_id": self.debate_id,
            "topic": self.topic,
            "arguments": [a.to_dict() for a in self.arguments],
            "winner": self.winner.value if self.winner else None,
            "consensus_reached": self.consensus_reached,
            "executive_decision": self.executive_decision,
            "final_confidence": self.final_confidence,
            "duration_seconds": self.duration_seconds,
            "timestamp": self.timestamp,
        }


class DebateProtocol:
    """Structured multi-agent debate protocol."""

    def __init__(self):
        self._debates: dict[str, DebateOutcome] = {}
        self._max_rounds = 3

    def start_debate(self, topic: str, initial_proposal: str, proposer: str = "executive") -> str:
        """Start a new debate."""
        debate_id = f"DEBATE-{uuid.uuid4().hex[:8]}"

        # Proposer makes initial argument
        initial_arg = DebateArgument(
            agent_id=proposer,
            position=Position.PRO,
            argument=initial_proposal,
            confidence=0.7,
        )

        outcome = DebateOutcome(
            debate_id=debate_id,
            topic=topic,
            arguments=[initial_arg],
        )
        self._debates[debate_id] = outcome
        return debate_id

    def add_argument(self, debate_id: str, agent_id: str, position: str,
                     argument: str, evidence: list[str] | None = None,
                     confidence: float = 0.5) -> bool:
        """Add an argument to an ongoing debate."""
        outcome = self._debates.get(debate_id)
        if outcome is None:
            return False

        arg = DebateArgument(
            agent_id=agent_id,
            position=Position(position),
            argument=argument,
            evidence=evidence or [],
            confidence=confidence,
        )
        outcome.arguments.append(arg)
        return True

    def hold_vote(self, debate_id: str) -> DebateOutcome:
        """Simulate a voting round with assigned positions."""
        import random

        outcome = self._debates.get(debate_id)
        if outcome is None:
            return None

        # Simulate 3 agents taking positions
        agents = ["agent_a", "agent_b", "agent_c"]
        for agent in agents:
            # Determine position based on existing arguments
            pro_count = sum(1 for a in outcome.arguments if a.position == Position.PRO)
            con_count = sum(1 for a in outcome.arguments if a.position == Position.CON)

            if pro_count > con_count:
                # Take con position (devil's advocate)
                position = Position.CON
                arg_text = f"Against: challenges the current majority view on {outcome.topic}"
            elif con_count > pro_count:
                position = Position.PRO
                arg_text = f"For: supporting the current majority view on {outcome.topic}"
            else:
                position = random.choice([Position.PRO, Position.CON])
                arg_text = f"{position.value}: balanced perspective on {outcome.topic}"

            self.add_argument(
                debate_id, agent, position.value, arg_text,
                confidence=random.uniform(0.4, 0.8)
            )

        return outcome

    def executive_judgment(self, debate_id: str) -> DebateOutcome:
        """Executive makes final decision based on debate."""
        outcome = self._debates.get(debate_id)
        if outcome is None:
            return None

        # Score positions
        pro_score = sum(a.confidence for a in outcome.arguments if a.position == Position.PRO)
        con_score = sum(a.confidence for a in outcome.arguments if a.position == Position.CON)

        if pro_score > con_score:
            outcome.winner = Position.PRO
        elif con_score > pro_score:
            outcome.winner = Position.CON
        else:
            outcome.winner = Position.ABSTAIN

        # Check consensus
        positions = {a.position for a in outcome.arguments}
        outcome.consensus_reached = len(positions) == 1

        outcome.final_confidence = abs(pro_score - con_score) / max(pro_score + con_score, 0.001)
        outcome.executive_decision = f"Decision: {outcome.winner.value} (confidence: {outcome.final_confidence:.2f})"

        start = outcome.arguments[0].timestamp if outcome.arguments else time.time()
        outcome.duration_seconds = time.time() - start
        return outcome

    def run_full_debate(self, topic: str, initial_proposal: str,
                        rounds: int = 3) -> DebateOutcome:
        """Run a complete debate from start to finish."""
        debate_id = self.start_debate(topic, initial_proposal)
        outcome = self._debates[debate_id]

        for i in range(rounds):
            outcome = self.hold_vote(debate_id)
            self.add_argument(debate_id, f"critic_{i}", "abstain",
                             f"Round {i+1} criticism: evaluating arguments")

        outcome = self.executive_judgment(debate_id)
        return outcome

    def get_debate(self, debate_id: str) -> DebateOutcome | None:
        return self._debates.get(debate_id)

    @property
    def debates(self) -> dict[str, DebateOutcome]:
        return self._debates

    def get_stats(self) -> dict[str, Any]:
        total = len(self._debates)
        return {
            "total_debates": total,
            "consensus_rate": sum(1 for d in self._debates.values() if d.consensus_reached) / total if total else 0,
            "avg_confidence": sum(d.final_confidence for d in self._debates.values()) / total if total else 0,
        }


class DebateProtocolPlugin:
    def __init__(self):
        self.engine = DebateProtocol()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {"status": "healthy", "debates": len(self.engine._debates)}


async def create(kernel=None):
    plugin = DebateProtocolPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
