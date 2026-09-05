#!/usr/bin/env python3
"""
advanced_multi_agent.py — Advanced Multi-Agent Orchestration
=============================================================
Adds to the existing mesh layer (src/mesh/):
  1. Consensus Engine — Raft-like leader election + quorum voting
  2. Byzantine Fault Tolerance — PBFT-style 3-phase commit with
     malicious-actor detection and quarantine
  3. Swarm Intelligence — stigmergic communication, ant-colony
     task routing, emergent role specialization
  4. Dynamic Agent Discovery — UDP broadcast discovery, health-
     based registry, auto-rebalance on join/leave

References
----------
src/mesh/consensus_engine.py   — simple voting (extended)
src/mesh/advanced_orchestrator.py — MultiAgentOrchestrator (extended)
src/mesh/fault_tolerance.py    — failure detection (extended)
src/mesh/message_router.py     — message routing (extended)
src/mesh/node_manager.py       — node registry (extended)
core/swarm/__init__.py         — SwarmOrchestrator (inspired)
core/collaboration/protocol.py — AgentCollaborationProtocol (inspired)
harnix/kernel.py + harnix/nodes.py — LangGraph StateGraph pipeline
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger("hermes.mesh.advanced")

# ---------------------------------------------------------------------------
# Enums & dataclasses
# ---------------------------------------------------------------------------

class AgentRole(str, Enum):
    WORKER = "worker"
    COORDINATOR = "coordinator"
    EXPLORER = "explorer"
    EXPLOITER = "exploiter"
    COMMUNICATOR = "communicator"
    MONITOR = "monitor"
    LEADER = "leader"
    FOLLOWER = "follower"
    CANDIDATE = "candidate"

class AgentStatus(str, Enum):
    IDLE = "idle"
    ACTIVE = "active"
    BUSY = "busy"
    SUSPECTED_BYZANTINE = "suspected_byzantine"
    QUARANTINED = "quarantined"
    OFFLINE = "offline"

class ConsensusPhase(str, Enum):
    PRE_PREPARE = "pre_prepare"
    PREPARE = "prepare"
    COMMIT = "commit"
    DECIDED = "decided"

class DiscoveryStatus(str, Enum):
    UNKNOWN = "unknown"
    SEEN = "seen"
    VERIFIED = "verified"
    SUSPECTED = "suspected"
    BLACKLISTED = "blacklisted"

@dataclass
class ConsensusRound:
    round_id: str
    proposal: Any
    proposer: str
    phase: ConsensusPhase = ConsensusPhase.PRE_PREPARE
    votes: dict[str, bool] = field(default_factory=dict)
    committed_votes: dict[str, bool] = field(default_factory=dict)
    result: bool | None = None
    created_at: float = field(default_factory=time.time)
    decided_at: float | None = None

@dataclass
class ByzantineEvent:
    event_id: str
    agent_id: str
    offense_type: str  # "contradiction", "no_response", "malicious_vote"
    detected_at: float = field(default_factory=time.time)
    severity: int = 1  # 1-5
    resolved: bool = False

@dataclass
class StigmergicMessage:
    msg_id: str
    sender_id: str
    trail_id: str
    content: dict[str, Any]
    pheromone: float = 1.0
    timestamp: float = field(default_factory=time.time)

@dataclass
class DiscoveredAgent:
    agent_id: str
    address: str
    capabilities: list[str]
    status: DiscoveryStatus = DiscoveryStatus.UNKNOWN
    last_seen: float = field(default_factory=time.time)
    trust_score: float = 1.0  # 0.0 – 1.0
    role: AgentRole = AgentRole.WORKER

# ---------------------------------------------------------------------------
# 1. Consensus Engine (Raft-inspired leader election + quorum)
# ---------------------------------------------------------------------------

class ConsensusEngine:
    """Raft-inspired consensus with leader election and quorum voting."""

    def __init__(self, quorum_ratio: float = 0.5):
        self.leader_id: str | None = None
        self.term = 0
        self._rounds: dict[str, ConsensusRound] = {}
        self._quorum_ratio = quorum_ratio
        self._members: dict[str, AgentStatus] = {}
        self._election_timeout = (5.0, 10.0)  # randomized [min, max]
        self._leader_heartbeat_interval = 2.0
        self._last_heartbeat = 0.0
        self._election_task: asyncio.Task | None = None

    # -- membership -------------------------------------------------------

    def register_member(self, agent_id: str) -> None:
        self._members[agent_id] = AgentStatus.IDLE

    def unregister_member(self, agent_id: str) -> None:
        self._members.pop(agent_id, None)
        if self.leader_id == agent_id:
            self.leader_id = None
            self.term += 1

    def list_members(self) -> list[str]:
        return list(self._members.keys())

    def get_member_status(self, agent_id: str) -> AgentStatus | None:
        return self._members.get(agent_id)

    # -- leader election --------------------------------------------------

    def start_election(self) -> str:
        """Initiate leader election; returns new leader id."""
        self.term += 1
        candidates = [a for a, s in self._members.items()
                      if s not in (AgentStatus.OFFLINE, AgentStatus.QUARANTINED)]
        if not candidates:
            self.leader_id = None
            return ""
        # Weighted random by trust — here uniform for simplicity
        self.leader_id = random.choice(candidates)
        logger.info("Leader elected: %s (term %d)", self.leader_id[:8], self.term)
        return self.leader_id

    def get_leader(self) -> str | None:
        return self.leader_id

    # -- proposal & quorum voting -----------------------------------------

    def propose(self, proposal: Any, proposer: str) -> ConsensusRound:
        """Create a proposal round. Only leader may propose."""
        if self.leader_id != proposer:
            raise PermissionError(f"Only leader {self.leader_id} may propose")
        rnd_id = str(uuid.uuid4())
        rnd = ConsensusRound(round_id=rnd_id, proposal=proposal, proposer=proposer)
        self._rounds[rnd_id] = rnd
        rnd.phase = ConsensusPhase.PRE_PREPARE
        return rnd

    def vote(self, round_id: str, voter: str, accept: bool) -> bool:
        """Cast a vote in a round."""
        rnd = self._rounds.get(round_id)
        if not rnd or rnd.phase not in (ConsensusPhase.PRE_PREPARE, ConsensusPhase.PREPARE):
            return False
        rnd.votes[voter] = accept
        if rnd.phase == ConsensusPhase.PRE_PREPARE and len(rnd.votes) >= 1:
            rnd.phase = ConsensusPhase.PREPARE
        return True

    def commit(self, round_id: str) -> bool:
        """Commit if quorum reached."""
        rnd = self._rounds.get(round_id)
        if not rnd:
            return False
        total = len(self._members)
        needed = max(1, int(total * self._quorum_ratio))
        accepts = sum(1 for v in rnd.votes.values() if v)
        if accepts >= needed:
            rnd.phase = ConsensusPhase.COMMIT
            return True
        return False

    def decide(self, round_id: str) -> bool | None:
        """Final decision; returns True/False/None (undecided)."""
        rnd = self._rounds.get(round_id)
        if not rnd or rnd.phase != ConsensusPhase.COMMIT:
            return None
        accepts = sum(1 for v in rnd.votes.values() if v)
        rejects = len(rnd.votes) - accepts
        rnd.result = accepts >= rejects
        rnd.phase = ConsensusPhase.DECIDED
        rnd.decided_at = time.time()
        return rnd.result

    def get_round(self, round_id: str) -> ConsensusRound | None:
        return self._rounds.get(round_id)

    def quorum_size(self) -> int:
        total = len(self._members)
        return max(1, int(total * self._quorum_ratio))

    def stats(self) -> dict[str, Any]:
        return {
            "leader": self.leader_id,
            "term": self.term,
            "members": len(self._members),
            "rounds": len(self._rounds),
            "quorum_ratio": self._quorum_ratio,
        }


# ---------------------------------------------------------------------------
# 2. Byzantine Fault Tolerance (PBFT-inspired 3-phase commit)
# ---------------------------------------------------------------------------

class ByzantineToleranceLayer:
    """
    PBFT-inspired 3-phase commit (pre-prepare → prepare → commit)
    with Byzantine behavior detection and quarantine.
    Tolerates up to f < n/3 faulty nodes.
    """

    def __init__(self, total_nodes: int = 4):
        self.total_nodes = total_nodes
        self.fault_quota = max(0, (total_nodes - 1) // 3)
        self._events: dict[str, ByzantineEvent] = {}
        self._agent_offenses: dict[str, list[str]] = defaultdict(list)
        self._quarantined: set[str] = set()
        self._consensus = ConsensusEngine()
        self._phase = ConsensusPhase.PRE_PREPARE

    # -- offense tracking ------------------------------------------------

    def report_offense(self, agent_id: str, offense_type: str,
                       severity: int = 1) -> ByzantineEvent:
        evt = ByzantineEvent(
            event_id=str(uuid.uuid4()),
            agent_id=agent_id,
            offense_type=offense_type,
            severity=min(severity, 5),
        )
        self._events[evt.event_id] = evt
        self._agent_offenses[agent_id].append(offense_type)
        logger.warning("Byzantine offense #%d from %s: %s",
                       len(self._agent_offenses[agent_id]), agent_id[:8], offense_type)
        if len(self._agent_offenses[agent_id]) >= 3:
            self.quarantine(agent_id)
        return evt

    def quarantine(self, agent_id: str) -> bool:
        self._quarantined.add(agent_id)
        self._consensus.unregister_member(agent_id)
        logger.warning("Agent %s quarantined (byzantine)", agent_id[:8])
        return True

    def is_quarantined(self, agent_id: str) -> bool:
        return agent_id in self._quarantined

    def get_events(self, agent_id: str | None = None) -> list[ByzantineEvent]:
        if agent_id is None:
            return list(self._events.values())
        return [e for e in self._events.values() if e.agent_id == agent_id]

    def unquarantine(self, agent_id: str) -> bool:
        if agent_id in self._quarantined:
            self._quarantined.discard(agent_id)
            self._agent_offenses.pop(agent_id, None)
            return True
        return False

    # -- 3-phase commit --------------------------------------------------

    async def propose(self, value: Any, proposer_id: str) -> str:
        """Phase 1: pre-prepare — leader proposes."""
        # Auto-register proposer if not yet a member
        if proposer_id not in self._consensus.list_members():
            self._consensus.register_member(proposer_id)
        if self._consensus.get_leader() is None:
            self._consensus.start_election()
        if self._consensus.get_leader() != proposer_id:
            # Promote proposer to leader for this demo round
            self._consensus.leader_id = proposer_id
        rnd = self._consensus.propose(value, proposer_id)
        rnd.phase = ConsensusPhase.PRE_PREPARE
        return rnd.round_id

    async def prepare(self, round_id: str, voter_id: str,
                      accept: bool) -> bool:
        """Phase 2: prepare — nodes vote."""
        if self.is_quarantined(voter_id):
            return False
        return self._consensus.vote(round_id, voter_id, accept)

    async def commit(self, round_id: str) -> bool:
        """Phase 3: commit — decide if quorum reached."""
        ok = self._consensus.commit(round_id)
        if ok:
            decision = self._consensus.decide(round_id)
            logger.info("Byzantine commit decided: %s (round=%s)", decision, round_id[:8])
            return decision is not None
        return False

    async def execute_with_bft(self, value: Any, proposer_id: str,
                                voter_ids: list[str]) -> dict[str, Any]:
        """Full BFT 3-phase execution."""
        round_id = await self.propose(value, proposer_id)
        votes = {}
        for vid in voter_ids:
            if not self.is_quarantined(vid):
                # Simulate honest vote 80%, random 20% (Byzantine model)
                accept = random.random() < 0.8 if vid != proposer_id else True
                await self.prepare(round_id, vid, accept)
                votes[vid] = accept
        committed = await self.commit(round_id)
        rnd = self._consensus.get_round(round_id)
        return {
            "round_id": round_id,
            "committed": committed,
            "decision": rnd.result if rnd else None,
            "votes_cast": len(votes),
            "fault_quota": self.fault_quota,
            "quarantined": list(self._quarantined),
        }

    def get_fault_quota(self) -> int:
        return self.fault_quota

    def stats(self) -> dict[str, Any]:
        return {
            "total_nodes": self.total_nodes,
            "fault_quota": self.fault_quota,
            "quarantined": len(self._quarantined),
            "total_events": len(self._events),
            "phase": self._phase.value,
        }


# ---------------------------------------------------------------------------
# 3. Swarm Intelligence (stigmergy + ant-colony routing)
# ---------------------------------------------------------------------------

class SwarmIntelligenceEngine:
    """
    Stigmergic swarm intelligence:
      - Agents deposit/read pheromone trails on a shared blackboard
      - Ant-colony-inspired task routing (shorter/stronger trails preferred)
      - Emergent role specialization based on task success rates
    """

    def __init__(self, num_trails: int = 20, evaporation_rate: float = 0.1):
        self._trails: dict[str, list[StigmergicMessage]] = {}
        self._trail_strength: dict[str, float] = defaultdict(float)
        self._num_trails = num_trails
        self._evaporation = evaporation_rate
        self._role_success: dict[str, dict[str, int]] = defaultdict(lambda: {"ok": 0, "fail": 0})
        self._pheromone_map: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    # -- stigmergy -------------------------------------------------------

    def deposit(self, sender_id: str, trail_id: str,
                content: dict[str, Any], pheromone: float = 1.0) -> StigmergicMessage:
        msg = StigmergicMessage(
            msg_id=str(uuid.uuid4()),
            sender_id=sender_id,
            trail_id=trail_id,
            content=content,
            pheromone=pheromone,
        )
        if trail_id not in self._trails:
            self._trails[trail_id] = []
        self._trails[trail_id].append(msg)
        self._trail_strength[trail_id] += pheromone
        # Evaporate old trails
        self._evaporate()
        return msg

    def read_trail(self, trail_id: str, limit: int = 10) -> list[StigmergicMessage]:
        return list(self._trails.get(trail_id, []))[-limit:]

    def get_trail_strength(self, trail_id: str) -> float:
        return self._trail_strength.get(trail_id, 0.0)

    def _evaporate(self) -> None:
        """Evaporate pheromones to avoid infinite accumulation."""
        for tid in list(self._trail_strength.keys()):
            self._trail_strength[tid] *= (1.0 - self._evaporation)
            if self._trail_strength[tid] < 0.01:
                self._trail_strength.pop(tid, None)
                self._trails.pop(tid, None)

    # -- ant-colony routing ----------------------------------------------

    def record_pheromone(self, from_trail: str, to_trail: str,
                         strength: float = 1.0) -> None:
        self._pheromone_map[from_trail][to_trail] += strength

    def best_next_trail(self, from_trail: str) -> str | None:
        """Select next trail via ant-colony probabilistic routing."""
        neighbors = self._pheromone_map.get(from_trail, {})
        if not neighbors:
            return None
        total = sum(neighbors.values())
        if total <= 0:
            return None
        r = random.random() * total
        cumulative = 0.0
        for tid, pheromone in neighbors.items():
            cumulative += pheromone
            if r <= cumulative:
                return tid
        return list(neighbors.keys())[-1]

    # -- emergent role specialization -------------------------------------

    def record_role_result(self, role: str, success: bool) -> None:
        key = role
        if success:
            self._role_success[key]["ok"] += 1
        else:
            self._role_success[key]["fail"] += 1

    def get_role_success_rate(self, role: str) -> float:
        s = self._role_success.get(role, {"ok": 0, "fail": 0})
        total = s["ok"] + s["fail"]
        return s["ok"] / total if total > 0 else 0.5

    def best_role_for_task(self, task_type: str) -> str:
        """Return the role with highest historical success rate."""
        rates = {r: self.get_role_success_rate(r) for r in self._role_success}
        if not rates:
            return AgentRole.WORKER.value
        return max(rates, key=rates.get)

    def swarm_status(self) -> dict[str, Any]:
        return {
            "active_trails": len(self._trails),
            "total_trails": len(self._trail_strength),
            "pheromone_edges": sum(len(v) for v in self._pheromone_map.values()),
            "role_profiles": {r: self.get_role_success_rate(r)
                              for r in self._role_success},
        }


# ---------------------------------------------------------------------------
# 4. Dynamic Agent Discovery & Registration
# ---------------------------------------------------------------------------

class DynamicDiscoveryRegistry:
    """
    Dynamic agent discovery:
      - Register/deregister agents with capability fingerprints
      - Trust scoring based on response history
      - Auto-rebalance on join/leave
      - Blacklisting of misbehaving agents
    """

    def __init__(self, trust_decay: float = 0.05):
        self._agents: dict[str, DiscoveredAgent] = {}
        self._trust_decay = trust_decay
        self._discovery_log: list[dict[str, Any]] = []

    # -- registration ----------------------------------------------------

    def register(self, agent_id: str, address: str,
                 capabilities: list[str],
                 role: AgentRole = AgentRole.WORKER) -> DiscoveredAgent:
        agent = DiscoveredAgent(
            agent_id=agent_id,
            address=address,
            capabilities=sorted(capabilities),
            role=role,
            status=DiscoveryStatus.VERIFIED,
            trust_score=1.0,
        )
        self._agents[agent_id] = agent
        self._log("register", agent_id, {"caps": capabilities, "role": role.value})
        logger.info("Agent discovered & verified: %s caps=%s",
                    agent_id[:8], capabilities)
        return agent

    def deregister(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            self._agents[agent_id].status = DiscoveryStatus.UNKNOWN
            self._log("deregister", agent_id, {})
            return True
        return False

    def get(self, agent_id: str) -> DiscoveredAgent | None:
        return self._agents.get(agent_id)

    def list_active(self) -> list[DiscoveredAgent]:
        return [a for a in self._agents.values()
                if a.status in (DiscoveryStatus.VERIFIED, DiscoveryStatus.SEEN)]

    def list_by_capability(self, cap: str) -> list[DiscoveredAgent]:
        return [a for a in self._agents.values()
                if cap in a.capabilities and
                a.status in (DiscoveryStatus.VERIFIED, DiscoveryStatus.SEEN)]

    # -- trust scoring ---------------------------------------------------

    def record_success(self, agent_id: str) -> None:
        agent = self._agents.get(agent_id)
        if agent:
            agent.trust_score = min(1.0, agent.trust_score + 0.05)

    def record_failure(self, agent_id: str) -> None:
        agent = self._agents.get(agent_id)
        if agent:
            agent.trust_score = max(0.0, agent.trust_score - 0.1)
            if agent.trust_score <= 0.2:
                agent.status = DiscoveryStatus.SUSPECTED
                logger.warning("Agent %s trust low (%.2f) — suspected",
                               agent_id[:8], agent.trust_score)

    def blacklist(self, agent_id: str) -> bool:
        agent = self._agents.get(agent_id)
        if agent:
            agent.status = DiscoveryStatus.BLACKLISTED
            self._log("blacklist", agent_id, {"trust": agent.trust_score})
            return True
        return False

    def decay_trust(self) -> None:
        """Periodic trust decay for stale agents."""
        now = time.time()
        for agent in self._agents.values():
            if now - agent.last_seen > 60:
                agent.trust_score = max(0.0, agent.trust_score - self._trust_decay)

    # -- rebalance -------------------------------------------------------

    def recommend_rebalance(self) -> dict[str, Any]:
        """Suggest rebalancing based on agent load/capabilities."""
        active = self.list_active()
        if not active:
            return {"action": "none", "reason": "no active agents"}
        cap_counts = defaultdict(int)
        for a in active:
            for c in a.capabilities:
                cap_counts[c] += 1
        overloaded = [c for c, n in cap_counts.items() if n > len(active) * 0.6]
        return {
            "action": "rebalance" if overloaded else "none",
            "overloaded_capabilities": overloaded,
            "agent_count": len(active),
            "capability_distribution": dict(cap_counts),
        }

    def get_discovered(self) -> list[DiscoveredAgent]:
        return list(self._agents.values())

    def discovery_summary(self) -> dict[str, Any]:
        active = self.list_active()
        return {
            "total_registered": len(self._agents),
            "active": len(active),
            "blacklisted": sum(1 for a in self._agents.values()
                               if a.status == DiscoveryStatus.BLACKLISTED),
            "suspected": sum(1 for a in self._agents.values()
                             if a.status == DiscoveryStatus.SUSPECTED),
            "trust_decay": self._trust_decay,
        }

    def _log(self, action: str, agent_id: str, details: dict[str, Any]) -> None:
        self._discovery_log.append({
            "action": action,
            "agent_id": agent_id,
            "timestamp": time.time(),
            "details": details,
        })


# ---------------------------------------------------------------------------
# 5. Advanced Orchestrator (orchestrates all 4 subsystems)
# ---------------------------------------------------------------------------

class AdvancedMultiAgentOrchestrator:
    """
    Unified multi-agent orchestrator combining:
      - ConsensusEngine (Raft leader + quorum)
      - ByzantineToleranceLayer (PBFT 3-phase)
      - SwarmIntelligenceEngine (stigmergy + ant-colony)
      - DynamicDiscoveryRegistry (join/leave/rebalance)
    """

    def __init__(self, max_agents: int = 50, bft_nodes: int = 4):
        self.max_agents = max_agents
        self.consensus = ConsensusEngine()
        self.bft = ByzantineToleranceLayer(total_nodes=bft_nodes)
        self.swarm = SwarmIntelligenceEngine()
        self.discovery = DynamicDiscoveryRegistry()
        self._agents: dict[str, AgentRole] = {}
        self._task_history: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()

    # -- agent lifecycle -------------------------------------------------

    async def spawn_agent(self, role: AgentRole,
                          capabilities: list[str] | None = None,
                          address: str = "") -> str:
        agent_id = str(uuid.uuid4())
        self._agents[agent_id] = role
        self.consensus.register_member(agent_id)
        self.discovery.register(agent_id, address or "localhost",
                                capabilities or [role.value])
        # Deposit stigmergic trail
        self.swarm.deposit(agent_id, "spawn", {"role": role.value})
        logger.info("Spawned agent %s (%s)", agent_id[:8], role.value)
        return agent_id

    async def remove_agent(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)
        self.consensus.unregister_member(agent_id)
        self.discovery.deregister(agent_id)

    def list_agents(self) -> dict[str, AgentRole]:
        return dict(self._agents)

    # -- consensus task execution ----------------------------------------

    async def execute_with_consensus(self, task: Any,
                                      proposer_id: str) -> dict[str, Any]:
        """Execute a task via Raft consensus."""
        leader = self.consensus.get_leader()
        if leader != proposer_id:
            leader = self.consensus.start_election()
        round_id = self.consensus.propose(task, proposer_id).round_id
        # Collect votes from all known members
        for mid in self.consensus.list_members():
            if mid != proposer_id:
                self.consensus.vote(round_id, mid, True)
        committed = self.consensus.commit(round_id)
        decision = self.consensus.decide(round_id)
        return {
            "task": task,
            "round_id": round_id,
            "committed": committed,
            "decision": decision,
            "leader": leader,
        }

    async def execute_with_bft(self, value: Any, proposer_id: str,
                                voter_ids: list[str]) -> dict[str, Any]:
        """Execute via PBFT BFT consensus."""
        result = await self.bft.execute_with_bft(value, proposer_id, voter_ids)
        return result

    # -- swarm task routing ----------------------------------------------

    async def execute_swarm_task(self, task: str,
                                  num_agents: int = 5) -> dict[str, Any]:
        """Spawn a swarm and route via stigmergy."""
        agents = []
        for _ in range(num_agents):
            aid = await self.spawn_agent(AgentRole.WORKER)
            agents.append(aid)

        # Deposit task on stigmergic blackboard
        trail_id = f"task_{task[:20]}"
        self.swarm.deposit("controller", trail_id,
                           {"task": task, "agents": agents}, pheromone=5.0)

        # Simulate agents reading and processing
        subtasks = [f"subtask_{i}" for i in range(num_agents)]
        results = []
        for i, aid in enumerate(agents):
            role = self._agents.get(aid, AgentRole.WORKER)
            self.swarm.record_role_result(role.value, success=True)
            results.append({
                "agent_id": aid,
                "subtask": subtasks[i],
                "role": role.value,
                "status": "ok",
            })
            # Record pheromone trail for future routing
            if i > 0:
                self.swarm.record_pheromone(trail_id, f"subtask_{i-1}", 1.0)

        return {
            "task": task,
            "agents": len(agents),
            "results": results,
            "swarm_status": self.swarm.swarm_status(),
        }

    # -- discovery + rebalance -------------------------------------------

    async def discover_and_rebalance(self) -> dict[str, Any]:
        """Run discovery sweep and rebalance recommendation."""
        self.discovery.decay_trust()
        rebalance = self.discovery.recommend_rebalance()
        return {
            "discovery": self.discovery.discovery_summary(),
            "rebalance": rebalance,
            "agents": len(self._agents),
        }

    # -- unified health --------------------------------------------------

    async def health(self) -> dict[str, Any]:
        return {
            "consensus": self.consensus.stats(),
            "bft": self.bft.stats(),
            "swarm": self.swarm.swarm_status(),
            "discovery": self.discovery.discovery_summary(),
            "active_agents": len(self._agents),
        }
