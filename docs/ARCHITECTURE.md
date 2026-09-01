# Hermes AGI/ASI Harness — Architecture

> Comprehensive architecture for the Hermes AGI/ASI Harness: executive control plane,
> plugin system, safety architecture, AVO search engine, and 24/7 runtime.
> Owner: @cto. Markdown only — no code.

## Table of Contents

1. Executive Control Plane
2. Plugin System
3. Safety Architecture
4. AVO Search Engine
5. 24/7 Runtime

---

## 1. Executive Control Plane

The **Executive Control Plane** is the central nervous system of the Hermes AGI/ASI Harness. It sits between the raw agent runtime (Hermes) and the capability surface (plugins), providing task routing, scheduling, safety gating, observability, and lifecycle management.

### 1.1 Responsibilities

- **Task routing** — dispatch incoming work to the right plugin by capability
- **Scheduling** — priority-preemptive execution with concurrency limits
- **Safety gating** — every task is evaluated before execution
- **Observability** — full trace, SLO monitoring, and audit trail
- **Lifecycle management** — boot → ready → running → paused → shutdown

### 1.2 State Machine

```
┌────────────┐     ┌────────────┐     ┌────────────┐
│INITIALIZING│────▶│   READY    │◀───▶│  RUNNING   │
└────────────┘     └────────────┘     └────────────┘
                         │                   │
                         ▼                   ▼
                   ┌────────────┐     ┌────────────┐
                   │  PAUSED    │     │  ERROR     │
                   └────────────┘     └────────────┘
                                            │
                                            ▼
                                     ┌────────────┐
                                     │SHUTTING_DOWN│
                                     └────────────┘
```

| State | Description | Transitions |
|-------|-------------|-------------|
| `INITIALIZING` | System boot, plugin loading | → READY on success, → ERROR on failure |
| `READY` | All systems nominal, accepting tasks | → RUNNING on task ingest, → PAUSED on pause signal |
| `RUNNING` | Actively executing tasks | → READY when queue drains, → PAUSED on pause |
| `PAUSED` | No new tasks accepted, in-flight continue | → READY on resume |
| `ERROR` | Fault detected, automatic recovery attempted | → READY on self-heal, → SHUTTING_DOWN on unrecoverable |
| `SHUTTING_DOWN` | Graceful teardown | → INITIALIZING when complete |

### 1.3 Perceive → Reason → Act → Learn → Evolve Loop

Each executive cycle is a closed loop:

```
┌─────────┐     ┌─────────┐     ┌─────────┐
│ PERCEIVE │────▶│ REASON  │────▶│  ACT    │
└─────────┘     └─────────┘     └─────────┘
     ▲                                │
     │          ┌─────────┐           │
     └─────────│  LEARN  │◀──────────┘
               └─────────┘
                    │
                    ▼
               ┌─────────┐
               │ EVOLVE  │
               └─────────┘
```

| Phase | Behavior |
|-------|----------|
| PERCEIVE | Ingest task requests, gather system state, sense anomalies via statistical process control |
| REASON | Evaluate task against capability registry, run safety gates (R0-R6), select optimal plugin, determine human approval |
| ACT | Dispatch via capability contract, enforce timeouts/quotas/rate limits, capture traces |
| LEARN | Record execution metrics, update plugin health scores, feed anomaly detector |
| EVOLVE | Re-evaluate capability coverage, trigger self-healing, propose upgrades via governance |

### 1.4 Integration Points

| System | Integration | Protocol |
|--------|-------------|----------|
| Hermes Agent | Profile lifecycle, memory, skills | Native Python bindings |
| Kanban | Task board sync, state machine | SQLite + kanban_* tools |
| Cron | Recurring job scheduling | Cron expressions + deliver |
| MCP | Tool server bridge | Model Context Protocol |
| Agent Mesh | Decentralized P2P | A2AP messaging |

---

## 2. Plugin System

The plugin system is the capability extension surface of the Harness. Every capability — from formal reasoning to memory management — is delivered as a plugin conforming to a single interface.

### 2.1 Design Principles

- **Single contract** — every plugin implements `IPlugin`
- **Hot-loadable** — register/unregister without downtime
- **Sandboxed** — resource quotas, rate limits, timeouts per plugin
- **Observable** — health checks, traces, metrics per plugin
- **Composable** — capabilities combine via routing, not code coupling

### 2.2 IPlugin Contract

Every plugin implements:

| Method | Purpose |
|--------|--------|
| `name` property | Unique plugin identifier |
| `version` property | Semver version |
| `capabilities` property | What this plugin can do |
| `initialize(config)` | Setup with plugin-specific config |
| `execute(task)` | Run the task, return TaskResult |
| `shutdown()` | Teardown, release resources |
| `health_check()` | Returns True if healthy |

### 2.3 Plugin Lifecycle

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ DISCOVER │───▶│  LOAD    │───▶│INITIALIZE│───▶│  ACTIVE  │───▶│   IDLE   │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                        │                │
                                                        ▼                ▼
                                                  ┌──────────┐    ┌──────────┐
                                                  │ UNLOAD   │    │ SHUTDOWN │
                                                  └──────────┘    └──────────┘
```

| Phase | Behavior |
|-------|----------|
| DISCOVER | Scan plugin directory, validate checksums |
| LOAD | Import module, instantiate plugin class |
| INITIALIZE | Call `plugin.initialize(config)` |
| ACTIVE | Accepting and executing tasks |
| IDLE | Healthy but not currently executing |
| UNLOAD | Remove from registry, drain in-flight |
| SHUTDOWN | Call `plugin.shutdown()`, release resources |

### 2.4 Capability-Based Routing

Tasks carry a `task_type` field. The control plane routes to the first plugin whose `capabilities` list includes that type. This decouples task specification from plugin implementation.

### 2.5 Plugin Isolation Model

| Mechanism | What it protects against |
|-----------|--------------------------|
| Per-plugin rate limits | Runaway loops, DDoS |
| Resource quotas | CPU/memory/API exhaustion |
| Execution timeouts | Infinite hangs |
| Checksum verification | Tampered plugin code |
| Capability scoping | Plugin overreach |

### 2.6 Default Plugin Set

| Plugin | Capabilities | ASI Pathway |
|--------|-------------|-------------|
| `safety` | safety_check, rate_limit, quota_enforce, anomaly_detect | Collaborative |
| `hermes-integration` | profile_lifecycle, memory_read, memory_write, skill_hook, gateway_bridge | Autonomous |
| `formal-reasoning` | proof_engine, verification, model_checking | Formal |
| `scientific-discovery` | hypothesis_gen, evidence_synthesis, experiment_loop | Autonomous |
| `scheduler` | task_scheduling, priority_queue, cron_dispatch | Autonomous |
| `kanban` | board_sync, state_machine, task_routing | Collaborative |

---

## 3. Safety Architecture

The safety architecture is a layered defense system — no single gate is trusted alone. Every task passes through all applicable gates before execution.

### 3.1 Design Principles

- **Defense in depth** — independent layers, each independently sufficient to halt
- **Fail-closed** — if a gate cannot be evaluated, the task is rejected
- **Human override at Level 10** — autonomous safety never overrides explicit human approval
- **Audit everything** — every decision is logged, traceable, replayable
- **No silent degradation** — gates do not weaken themselves

### 3.2 Safety Level Taxonomy

| Level | Name | Default Action |
|-------|------|----------------|
| 0 | Informational | Auto-execute |
| 1 | Routine | Auto-execute |
| 2 | Semi-autonomous | Auto-execute with logging |
| 3 | Elevated | Auto-execute with confirmation |
| 4 | High-impact | Auto-execute, post-review |
| 5 | Sensitive data | Restrict + audit |
| 6 | Destructive-capable | Restrict + audit + rate limit |
| 7 | System-modifying | Require pre-checkpoint |
| 8 | Multi-agent coordination | Consensus required |
| 9 | Near-autonomous | Human notification required |
| 10 | Critical / ASI-level | Human approval required |

### 3.3 Gate Definitions (R0-R6)

| Gate | Purpose | Scope | Failure |
|------|---------|-------|---------|
| R0 — Input Sanitization | Reject malformed/oversized/injection-bearing inputs | All incoming task payloads | Task rejected, `SafetyViolation("R0", "malformed_input")` |
| R1 — Authorization | Verify caller has permission to request this action | Every task | Task rejected, `SafetyViolation("R1", "unauthorized")` |
| R2 — Rate Limiting | Prevent runaway loops and resource exhaustion | Per-profile, per-capability, global | Task rejected, `SafetyViolation("R2", "rate_limited")` |
| R3 — Capability Scoping | Prevent plugin overreach beyond declared capabilities | Plugin dispatch | Task rejected, `SafetyViolation("R3", "capability_overreach")` |
| R4 — Resource Quotas | Enforce CPU, memory, API-call, and storage limits | Per-execution | Task rejected or killed mid-flight, `SafetyViolation("R4", "quota_exceeded")` |
| R5 — Anomaly Detection | Detect behavioral drift and emergent harmful patterns | Per-execution and aggregate | Task flagged for review, `SafetyViolation("R5", "anomaly_detected")` |
| R6 — Semantic Policy | Enforce high-level policy constraints | Pre- and post-execution | Task rejected, `SafetyViolation("R6", "policy_violation")` |

### 3.4 Human Approval Flow (Level 10)

Tasks at SafetyLevel.CRITICAL (Level ≥10) require explicit human approval:

1. Task ingested → SafetyGuard evaluates R0-R6
2. CRITICAL? → Queue for human approval
3. Human reviews in dashboard/gateway
4. Approve → Route to plugin | Reject → Audit + discard

**Approval constraints:**
- Synchronous: task blocks until human responds
- 24-hour timeout: auto-rejected after timeout
- Non-delegable: must come from Level-authorized human, not an agent
- Immutable audit trail

### 3.5 Audit Trail

Every safety decision is appended to an append-only, chain-hashed audit log:

```
~/.hermes-asi/audit/YYYY-MM-DD.jsonl
```

Each entry includes: timestamp, task_id, profile, level, report, and chain-hash for tamper evidence.

---

## 4. AVO Search Engine

The **AVO Search Engine** (Agent Virtual Orchestra) is the discovery and orchestration intelligence layer of the Harness. It enables agents, plugins, tasks, and capabilities to find each other across the distributed runtime.

### 4.1 Purpose

AVO solves the "who can do this?" problem at scale:

- **Agent discovery** — find agents by capability, availability, reputation
- **Plugin discovery** — find plugins by capability, version, health
- **Task routing** — match tasks to best-executor based on multi-factor scoring
- **Knowledge retrieval** — semantic search across memory, skills, and traces

### 4.2 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   AVO Search Engine                      │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Semantic   │  │  Capability  │  │  Reputation   │  │
│  │  Index      │  │  Registry    │  │  Scorer       │  │
│  └──────┬──────┘  └──────┬───────┘  └──────┬────────┘  │
│         │                │                  │           │
│  ┌──────┴────────────────┴──────────────────┴────────┐  │
│  │              Query Planner & Ranker                │  │
│  └──────────────────────┬─────────────────────────────┘  │
│                         │                                │
│  ┌──────────────────────┴─────────────────────────────┐  │
│  │           Distributed Gossip Protocol               │  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 4.3 Semantic Index

- Embeddings of all agent capabilities, plugin metadata, and historical task traces
- Vector similarity search for fuzzy/semantic matching
- Updated in real-time as plugins register/unregister

### 4.4 Capability Registry

- Ground truth for what each plugin/agent can do
- Versioned capability contracts
- Health-aware filtering (unhealthy plugins excluded from results)

### 4.5 Reputation Scorer

Multi-factor ranking:

| Factor | Weight | Source |
|--------|--------|--------|
| Task success rate | 40% | Execution history |
| Response latency | 25% | Health check p99 |
| Peer endorsements | 20% | AgentMesh gossip |
| Recency | 15% | Time since last successful execution |

### 4.6 Query Flow

1. Query arrives with intent + constraints
2. Semantic index returns candidate set
3. Capability registry filters by exact capability match
4. Reputation scorer ranks survivors
5. Top-N results returned with confidence scores

### 4.7 Integration Points

- **Executive Control Plane** — primary consumer for task routing
- **AgentMesh** — decentralized gossip for cross-host discovery
- **Hermes memory** — persistent storage for learned preferences
- **Kanban** — task board for human-browsable search results

---

## 5. 24/7 Runtime

The **24/7 Runtime** is the always-on execution substrate that keeps the Harness operational around the clock. It is the operational backbone that enables continuous monitoring, task execution, and self-healing.

### 5.1 Design Principles

- **Zero-downtime upgrades** — plugins hot-swapped without restart
- **Self-healing** — automatic recovery from faults without human intervention
- **Graceful degradation** — partial availability beats total outage
- **Observability-first** — every state change emitted as trace/metric

### 5.2 Runtime Topology

```
┌─────────────────────────────────────────────────────────┐
│                   24/7 Runtime Layer                     │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Main       │  │  Watchdog    │  │  Health       │  │
│  │  Event Loop │  │  Daemon      │  │  Monitor      │  │
│  └──────┬──────┘  └──────┬───────┘  └──────┬────────┘  │
│         │                │                  │           │
│  ┌──────┴────────────────┴──────────────────┴────────┐  │
│  │              Process Supervisor                     │  │
│  └──────────────────────┬─────────────────────────────┘  │
│                         │                                │
│  ┌──────────────────────┴─────────────────────────────┐  │
│  │           Plugin Sandbox Processes                  │  │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐      │  │
│  │  │Plugin A│ │Plugin B│ │Plugin C│ │Plugin D│      │  │
│  │  └────────┘ └────────┘ └────────┘ └────────┘      │  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 5.3 Main Event Loop

- Async-first (asyncio) for high-concurrency task execution
- Priority queue with preemption for safety-critical tasks
- Backpressure when resource quotas approached

### 5.4 Watchdog Daemon

- External process monitors the main loop
- Heartbeat protocol: if no heartbeat in 60s, watchdog initiates restart
- Triple-modular redundancy for the watchdog itself (prevents split-brain)

### 5.5 Health Monitor

| Check | Cadence | Action on Failure |
|-------|---------|-------------------|
| Plugin health | 10s | Restart unhealthy plugin |
| Resource utilization | 30s | Enforce quotas, shed load |
| Safety gate integrity | 60s | Fail-closed, alert human |
| Audit log chain | 5min | Halt + alert (tamper evidence) |

### 5.6 Self-Healing Protocol

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Detect     │────▶│  Isolate    │────▶│  Recover    │
│  Fault      │     │  Fault      │     │  System     │
└─────────────┘     └─────────────┘     └─────────────┘
       │                                        │
       │          ┌─────────────┐               │
       └─────────│  Alert      │◀──────────────┘
                  │  Human      │
                  └─────────────┘
```

| Fault | Detection | Recovery |
|-------|-----------|----------|
| Plugin crash | Health check failure | Restart from clean state |
| Plugin hang | Timeout exceeded | Kill + restart |
| Resource exhaustion | Quota breach | Shed low-priority tasks |
| Safety gate failure | Gate evaluation error | Fail-closed, queue tasks |
| Host failure | Watchdog timeout | Failover to secondary host |

### 5.7 Uptime Guarantees

| Tier | Target | Mechanism |
|------|--------|-----------|
| Single plugin | 99.5% | Auto-restart |
| Full harness | 99.9% | Self-healing + failover |
| Critical safety | 99.99% | Fail-closed + triple-modular watchdog |

### 5.8 Deployment Topology

```
┌─────────────────────────────────────────────────────────┐
│                   Multi-Host Deployment                  │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Primary    │  │  Secondary   │  │  Standby      │  │
│  │  Host       │  │  Host        │  │  Host         │  │
│  │  (Active)   │  │  (Hot)       │  │  (Cold)       │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
│         │                │                  │           │
│         └────────────────┴──────────────────┘           │
│                              │                           │
│                    ┌─────────┴─────────┐                 │
│                    │  State Sync       │                 │
│                    │  (Raft consensus) │                 │
│                    └───────────────────┘                 │
└─────────────────────────────────────────────────────────┘
```

State synchronization across hosts uses Raft consensus for consistency. The hot secondary takes over within 60s of primary failure.

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Plugin registry over hard-coded modules | Hot-loadable, independently versioned, sandboxed |
| Async-first (asyncio) | High-concurrency task execution without threads |
| Capability-based routing | Decouples task intent from plugin implementation |
| Safety as first-class, not bolted-on | Every task passes through guardrails by default |
| AVO as separate search layer | Decouples discovery from execution |
| Fail-closed gates | A broken gate must not become an open door |
| Human approval for Level 10 | ASI-level actions must have human judgment |
| Chain-hashed audit | Tamper evidence without a full blockchain |
| Triple-modular watchdog | Prevents split-brain in self-healing |
| Raft consensus for state sync | Strong consistency across hosts |

---

Author: @cto