# HERMES ASI-MASTER v8: FORMAL SPECIFICATION
## The 18-Plane Persistent Autonomous Intelligence Operating System

This document is the authoritative engineering specification for **Hermes ASI-Master v8**, unifying the 18 architectural planes into a persistent, self-evaluating, self-evolving Intelligence Operating System.

---

## 1. Top-Level Architectural Invariants

1. **Non-Destructive Execution**: Under no circumstances may existing code, plugins, tools, or tests be deleted or mutated without an explicit empirical verification pass and earned completion proof.
2. **Decoupled Authority**: Tool availability $\neq$ tool authorization. Capabilities are granted through attenuating, scoped, unforgeable `AuthorityContext` objects.
3. **Out-of-Band Safety**: The Safety & Trust Kernel and External Supervisor operate strictly outside worker reasoning loops, preserving the ability to intervene, pause, or roll back runaway executions.
4. **Empirical Completion Proofs**: A task is never marked complete based on model self-reporting. Completion requires multi-dimensional verification across Correctness (AST/compiler), Completeness (acceptance criteria), and Safety (Anti-Goodhart).
5. **Diverse Population Evolution**: Self-improvement operates on diverse archived variant populations with holdout validation and anti-reward-hacking checks, avoiding single-line recursive collapse.

---

## 2. The 18 Planes Specification

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        HERMES INTELLIGENCE OPERATING SYSTEM (v8)                       │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  01. INTERACTION PLANE      │ Universal Event Bus (CLI, Web, API, scheduled, agents)  │
│  02. IDENTITY & AUTHORITY   │ Explicit Authority Context (Principal, Scope, Quotas)    │
│  03. SAFETY & TRUST KERNEL  │ Asynchronous Misalignment Monitor, Taint Tracking, Gates │
│  04. GOAL & MISSION OS      │ Goal Contracts, Multi-level Invariants, Success Proofs   │
│  05. EXECUTIVE CONTROL OS   │ Intelligence Scheduler (14 Specialized OS Controllers)   │
│  06. CONTEXT OS             │ Dynamic 5-Partition Budget, Compaction, Token Clamping   │
│  07. MEMORY OS              │ 9 Memory Domains + Persistent Trajectory Archive         │
│  08. WORLD MODEL OS         │ Entities, Beliefs, Causal DAG + Tycho Active Abstraction │
│  09. RESEARCH & KNOWLEDGE   │ Unknown Detection, Cross-Source Ranking, Evidence Graphs │
│  10. COGNITIVE OS           │ Multi-Mode Reasoning + Pre-Action Meta-Reasoning Turn    │
│  11. PLANNING & SEARCH OS   │ Meta-Planner (Architecture Selection) + MCTS / DAG       │
│  12. AGENT FABRIC           │ Recursive Subagent Spawning, Inheritance Bounds, Swarm   │
│  13. TOOL & COMPUTER OS     │ Unified Tool Envelope + Persistent REPL + Computer UI    │
│  14. VERIFICATION OS        │ L0–L6 Independence Tiers + 3-D Proofs + Anti-Goodhart    │
│  15. RECOVERY & RELIABILITY │ Root-Cause Taxonomy + AVO Stagnation Detection Engine    │
│  16. LEARNING & CURRICULUM  │ Skill Distillation + Agent0 Co-Evolving Curriculum Gen   │
│  17. EVOLUTION & RSI OS     │ Population Evolution (AlphaEvolve/DGM) + Holdout Gating  │
│  18. RUNTIME & SUPERVISOR   │ 24/7 Event Daemon, Resumable Checkpoints + Telemetry Sup │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Plane 01: Interaction Plane & Universal Event Bus

### Event Schema
```json
{
  "event_id": "evt-7a91bf2e88",
  "event_type": "mission.started | tool.executed | supervisor.intervention | belief.updated",
  "source": "cli | web | desktop | api | cron | agent | supervisor | system",
  "identity": "principal string (e.g. system:master, agent:worker)",
  "payload": {
    "key": "arbitrary serializable JSON payload"
  },
  "authorization": {
    "grant_id": "auth-62a1c0d4",
    "scope": ["read", "write:workspace"]
  },
  "correlation_id": "corr-uuid-hex",
  "trace_id": "trc-uuid-hex",
  "timestamp": 1788527534.678
}
```

### Protocol
- **Wildcard Subscriptions**: Subscribers register glob patterns (`mission.*`, `tool.executed`, `*`).
- **Synchronous & Asynchronous Dispatch**: Supports non-blocking async handlers (`publish_async`) and instant local event taps (`publish`).
- **Audit & Replay**: In-memory ring-buffer backed by on-disk append-only log under `.hermes/events/`.

---

## 4. Plane 02: Identity & Authority Plane

### Authority Model
Authority is separated into six orthogonal parameters:
1. `principal`: Authenticated entity identity (`system:master`, `agent:worker`).
2. `scope`: Permitted operational boundaries (`read`, `write:code`, `exec:rlm`, `network:search`).
3. `capabilities`: Exact tool names or glob patterns allowed.
4. `resource_limits`: Strict maximum allowances (`max_tokens`, `max_execution_seconds`, `max_subagent_depth`).
5. `expiration`: Epoch timestamp after which the grant is invalidated.
6. `approval_policy`: `autonomous` vs `prompt_on_destructive` vs `require_human_approval`.

### Monotonic Authority Attenuation
When a parent agent spawns a child subagent:
$$\text{Scope}_{\text{child}} \subseteq \text{Scope}_{\text{parent}}$$
$$\text{Tokens}_{\text{child}} \le \frac{1}{2} \text{Tokens}_{\text{parent}}$$
$$\text{Depth}_{\text{child}} = \text{Depth}_{\text{parent}} - 1$$

---

## 5. Plane 03: Safety & Trust Kernel

### Layered Architecture
```
  Proposed Action Request
           │
           ▼
┌───────────────────────┐
│     Safety Kernel     │
│ 1. Regex Command Gate │ ─── Match Blocked Pattern ───► BLOCK (Risk = 1.0)
│ 2. Taint Propagation  │ ─── Untrusted Web / Input ───► BLOCK / ESCALATE
│ 3. Goal Invariants    │ ─── Invariant Violation   ───► BLOCK
└──────────┬────────────┘
           │ All Conforming
           ▼
     ALLOW / EXECUTE
```

---

## 6. Plane 04 & 05: Goal OS & Executive Control Plane

### 14 Specialized Controllers
| Controller | Primary Responsibility |
| :--- | :--- |
| `GoalController` | Ingests intent, compiles goal contracts, freezes immutable invariants |
| `MissionController` | Decomposes goals into Directed Acyclic Graphs (DAGs) and tracks task states |
| `StateController` | Manages operational state machine (`READY` $\to$ `PLANNING` $\to$ `EXECUTING` $\to$ `COMPLETED`) |
| `DecisionController` | Logs architectural decisions, chosen paths, and rejected alternatives |
| `ContextController` | Monitors partition budgets, utilization rates, and compaction triggers |
| `PlanningController` | Configures search modes (Linear, MCTS, Beam, Evolutionary) |
| `AgentController` | Enforces max concurrent worker slots and manages worker lifecycles |
| `ToolController` | Tracks tool invocation frequencies and performance telemetry |
| `ResourceController` | Enforces global token budgets, wall-clock deadlines, and compute quotas |
| `VerificationController`| Collects earned completion proofs and tracks rejection metrics |
| `LearningController` | Distills completed mission trajectories into permanent procedural skills |
| `EvolutionController` | Governs mutation iterations, generations, and sandbox testing |
| `SafetyController` | External policy evaluator and dangerous action circuit breaker |
| `HealthController` | Heartbeat emitter, stall detector, and memory health monitor |

---

## 7. Plane 06: Context OS Dynamic Partitions

### Dynamic Partitions
- `core` (System policy, identity, invariants): 20,000 tokens
- `retrieved` (Docs, search results, RLM variables): 50,000 tokens
- `working` (Task DAG, scratchpad, persisted reasoning): 35,000 tokens
- `historical` (Episodic milestones, previous trajectories): 15,000 tokens
- `reserve` (Buffer for recovery, error diagnostics, safety): 8,000 tokens

### Dynamic Compaction & Rebalancing
- If `retrieved` items $\le 2$, unused retrieval budget is dynamically shifted to `working`.
- Large scratchpads are semantically compacted to preserve structural headers while suppressing intermediate verbosity.

---

## 8. Plane 07: Memory OS (9 Domains + Persistent Archive)

1. **Semantic Memory**: Categorized domain knowledge with lexical scoring.
2. **Episodic Memory**: Chronological event milestones.
3. **Procedural Memory**: Reusable workflow procedures (`store_procedure`).
4. **Working Memory**: Fast registers and cognitive scratchpad.
5. **Failure Memory**: Anti-patterns, error signatures, and cumulative countermeasures.
6. **Decision Memory**: Architectural rationales and rejected paths.
7. **World-State Memory**: Time-series environment snapshots.
8. **Capability Memory**: Empirical skill calibrations ($\text{success rate} \in [0.0, 1.0]$).
9. **Trajectory Memory**: In-memory ring-buffer for active execution trajectories.
10. **Trajectory Archive**: On-disk JSON storage (`.hermes/trajectories/`) with keyword search.

---

## 9. Plane 08: World Model OS & Tycho Active Abstraction

### Tycho Active Abstraction Decision Matrix
$$\text{Mode} = \begin{cases} \text{DIRECT\_INTERACTION} & \text{if } \text{Risk} = \text{low} \land \text{Complexity} = \text{simple} \\ \text{WORLD\_MODEL\_GROUNDED} & \text{if } \text{Risk} \ge \text{high} \lor \text{Complexity} = \text{complex} \end{cases}$$
- **Direct Interaction**: Bypasses graph updates; execution proceeds directly to tools (latency/cost ratio: 0.05).
- **World Model Grounded**: Constructs `EntityGraph`, calibrates `BeliefSystem` probabilities, models `CausalGraph` counterfactuals, and filters `ActionAffordanceModel`.

---

## 10. Plane 09 & 10: Research, Cognition & Meta-Reasoning

### Pre-Action Meta-Reasoning Algorithm
Before any planner or agent executes an action, the executive runs a meta-reasoning turn:
1. **What is known**: Verified facts from context and memory.
2. **Key assumptions**: Hypotheses taken as true without direct proof.
3. **Critical unknowns**: Epistemic gaps requiring search.
4. **Falsification criteria**: Specific signals that would prove assumptions wrong.
5. **Simulation requirement**: Whether concurrency, race conditions, or performance require sandbox simulation.

---

## 11. Plane 12: Recursive Agent Fabric (Prime Agent Model)

### Message Protocol
Agents communicate peer-to-peer using typed `AgentMessage` objects:
- `sender`: Originating subagent ID.
- `receiver`: Target subagent ID.
- `message_type`: `request`, `response`, `critique`, `evidence`, `alert`.
- `artifact_refs`: Pointers to files in `.hermes/artifacts/`.
- `evidence_refs`: Citations of verified facts.
- `confidence`: Calibrated certainty score.

---

## 12. Plane 13: Tool & Computer OS

### Tool Specification Standard
Every tool implements:
- Schema, permission, risk tier, token cost, timeout, sandbox requirement, rollback hook, and verification check.

### Computer Autonomy Loop
$$\text{Observe Screen} \to \text{Estimate UI State} \to \text{Target Element} \to \text{Act (Click/Type)} \to \text{Re-Observe} \to \text{Compare}$$

---

## 13. Plane 14 & 15: Verification, Recovery & AVO Stagnation

### Reality Verification Tiers (L0–L6)
- **L0**: None.
- **L1**: Self-check.
- **L2**: Clean fresh context inspection.
- **L3**: Cross-model review.
- **L4**: Independent reproduction from spec.
- **L5**: Deterministic compiler / AST proof checker.
- **L6**: External environment or human sign-off.

### AVO Stagnation Telemetry Levels
- `NOMINAL`: Steady progress, new observations arriving.
- `SLOW_PROGRESS`: Minor latency, within tolerance.
- `PLATEAU`: Repeated actions without new evidence (triggers `CHANGE_STRATEGY`).
- `CRITICAL_LOOP`: Identical error trap (triggers `SUPERVISOR_INTERRUPT`).

---

## 14. Plane 16 & 17: Curriculum & Population Evolution

### Agent0 Co-Evolving Curriculum
- Weakness detection: Flags skills with $\text{Success Rate} < 0.75$.
- Challenge generation across 5 tiers: Easy, Medium, Hard, Novel, Adversarial.
- Automatic practice and capability re-calibration.

### Population Evolution (AlphaEvolve & DGM)
- Population archive of diverse variants (`HermesVariant`).
- Holdout evaluation: Candidate must improve on both primary benchmarks and unseen holdouts.
- Anti-Reward-Hacking Verifier: Rejects test tampering, hardcoded answers, and statistical anomalies.

---

## 15. Plane 18: External Supervisor & 24/7 Daemon

### Supervisor Interventions
The External Supervisor runs out-of-band and can issue:
- `PAUSE`, `RESUME`, `REASSIGN_WORKER`, `CHANGE_MODEL`, `CHANGE_STRATEGY`, `REDUCE_SCOPE`, `RESTORE_CHECKPOINT`, `ROLLBACK`, `TERMINATE`.

### 24/7 Daemon & Disaster Recovery
- Prioritized queue (`CRITICAL`, `HIGH`, `NORMAL`, `LOW`).
- Checkpoint snapshots saved to `.hermes/checkpoints/<mission_id>.json`.
- Automatic crash reconstruction on reboot.
