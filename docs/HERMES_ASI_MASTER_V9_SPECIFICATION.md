# HERMES ASI-MASTER v9: FORMAL SPECIFICATION
## Cognitive Planning & Autonomous Execution Architecture

This document is the authoritative engineering specification for **Hermes ASI-Master v9**. The definitive core of v9 is the **Pre-Execution Intelligence Layer: The Cognitive Compiler**.

Hermes is not designed merely to "think longer" or dump unstructured chain-of-thought into transient prompts. It operates as a deterministic, structured cognitive operating system that reasons about **what** should be done, **why** it should be done, **how** it should be done, **what capabilities** are required, **what evidence** is needed, **how work is parallelized**, and **how completion is provably validated** before committing to real execution.

---

## 1. Top-Level Architectural Formula

$$\text{HERMES v9} = \text{Foundation Models} + \text{Executive Kernel} + \text{Cognitive Planning OS} + \text{Capability OS} + \text{Dynamic Runtimes (LangGraph / Deep Agents)} + \text{Supervisor \& Evolution}$$

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          HERMES COGNITIVE PLANNING OS (v9)                             │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ P0  Mission Understanding   │ Intent extraction, implicit requirements, anti-goals     │
│ P1  Goal Construction       │ Objective, desired world state, immutable invariants     │
│ P2  Environment Recon       │ Repo, filesystem, packages, services, git, MCP, GPU      │
│ P3  Capability Discovery    │ Models, agents, tools, skills, plugins, slash commands   │
│ P4  Uncertainty Analysis    │ Epistemic status: Known, Unknown, Uncertain, Contested   │
│ P5  Research Planning       │ Value of Information (VOI) + Multi-lane research design  │
│ P6  Deep Research Engine    │ Lead + Specialists + Fact Verifier (AgentEye/Web)        │
│ P7  Knowledge Synthesis     │ Verified claim graph + World Model + Mission state update│
│ P8  Strategy Generation     │ Explicit Strategy Candidates (A, B, C) with trade-offs   │
│ P9  Strategy Search & Eval  │ Multi-criteria scoring, branch pruning, simulation       │
│ P10 Goal Decomposition      │ Mission DAG: Objectives ──> Subgoals ──> Atomic Tasks    │
│ P11 Dependency Analysis     │ Declares: depends_on, blocks, enables, conflicts_with    │
│ P12 Parallelization         │ Topological sorting into Execution Waves 1, 2, 3...      │
│ P13 Agent Topology Design   │ 1 agent, planner-executor, lead-specialist, or swarm     │
│ P14 Model Routing           │ Frontier reasoning, coding, vision, or fast model        │
│ P15 Capability Plan         │ Explicit bindings: Tools, on-demand Skills, Plugins, Cmds│
│ P16 Resource Allocation     │ Tokens, time, CPU, GPU, memory, API quota budgeting      │
│ P17 Risk & Safety Planning  │ Reversibility rating, side effects, policy gates         │
│ P18 Verification Planning   │ Verifiers, AST checks, test suites designed BEFORE exec  │
│ P19 Recovery Planning       │ Primary strategy + Fallback A + Fallback B + Escalation  │
│ P20 Execution Compilation   │ Emits executable ExecutionPlanIR & Structured Blackboard │
│ P21 Plan Critic & Approval  │ Adversarial review, invariant validation, PLAN_APPROVED  │
├─────────────────────────────┴──────────────────────────────────────────────────────────┤
│                                   EXECUTION RUNTIME                                    │
│             LangGraph StateGraph  │  Deep Agents Isolated Contexts  │  MCP Tools       │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. The 22 Planning Phases (P0 through P21)

| Phase | Designation | Formal Responsibilities |
| :--- | :--- | :--- |
| **P0** | **Mission Understanding** | Normalizes raw human input into explicit objectives, implicit constraints, and anti-goals ("what must NOT happen"). |
| **P1** | **Goal Construction** | Compiles the formal `GoalContract`, target world state, and non-compactable `GoalInvariant` specifications. |
| **P2** | **Environment Reconnaissance** | Active discovery of hardware profile (CPUs, RAM, GPU), OS, Python runtime, workspace lockfiles, git branch, and running services. |
| **P3** | **Capability Discovery** | Queries the `CapabilityRegistry` to catalog registered models, tools, on-demand skills, plugins, and control commands. |
| **P4** | **Uncertainty Analysis** | Builds an epistemic classification matrix (`KNOWN`, `UNKNOWN`, `UNCERTAIN`, `ASSUMED`, `CONTESTED`). Enforces the invariant: *Never silently convert unknowns into assumptions*. |
| **P5** | **Research Planning** | Computes Value of Information (VOI) and constructs a structured `ResearchPlan` across multiple investigative lanes. |
| **P6** | **Deep Research Execution** | Dispatches research queries across official documentation, source code repositories, and empirical tests. |
| **P7** | **Knowledge Synthesis** | Distills research outputs into verified factual claims, updating the World Model and Planning Blackboard. |
| **P8** | **Strategy Generation** | Formulates discrete, competing `StrategyCandidate` objects (e.g. Minimalist Direct, Staged Robust, Parallel Swarm). |
| **P9** | **Strategy Search & Evaluation** | Multi-attribute evaluation scoring across probability of success, reversibility, risk, cost, and latency. |
| **P10** | **Goal Decomposition** | Decomposes chosen strategy into a formal `GoalGraph` of subgoals and atomic task nodes. |
| **P11** | **Dependency Analysis** | Maps explicit inter-goal relationships: `depends_on`, `blocks`, `enables`, `conflicts_with`. Detects cycles. |
| **P12** | **Parallelization (Waves)** | Partitions tasks into sequential `ExecutionWave` cohorts where all intra-wave tasks execute concurrently. |
| **P13** | **Agent Topology Design** | Selects optimal organizational pattern (Single Agent, Planner-Executor, Lead-Specialists, Swarm). |
| **P14** | **Model Routing** | Assigns specialized foundation models per task based on reasoning difficulty and latency constraints. |
| **P15** | **Capability Planning** | Emits `ExecutionCapabilityPlan` binding tools, on-demand skills, plugins, and control commands per task. |
| **P16** | **Resource Planning** | Budgets tokens, execution time, parallelism limits, and memory partition allocations per subgoal. |
| **P17** | **Risk & Safety Planning** | Quantifies reversibility, side-effects, and attaches policy approval gates for irreversible actions. |
| **P18** | **Verification Planning** | Establishes verification requirements, test oracles, and acceptance criteria *before* work starts. |
| **P19** | **Recovery Planning** | Pre-computes primary fallback, alternate tool, and escalation thresholds *before* execution failure occurs. |
| **P20** | **Execution Compilation** | Synthesizes all data structures into a unified, immutable `ExecutionPlanIR` and `PlanningRecord`. |
| **P21** | **Adversarial Plan Review** | The adversarial `PlanCritic` audits the plan for blindspots, cycles, and invariant compliance. Emits `PLAN_APPROVED`. |

---

## 3. Mission Intermediate Representation (Mission IR)

Every request becomes a durable, persistent `MissionIR` stored out-of-band:
- `mission_id`: Unique persistent identifier.
- `original_request` & `normalized_intent`.
- `objective` & `desired_state`.
- `invariants`: Non-compactable kernel-level rules (e.g. `zero_deletion`, `preserve_tests`).
- `unknowns` & `assumptions`.
- `required_capabilities`: Models, tools, skills, plugins, commands.
- `goal_graph`: Dynamic dependency DAG.

### Goal Lifecycle State Machine
```
CREATED ──> UNDERSTOOD ──> VALIDATED ──> PLANNED ──> ACTIVE ──> VERIFYING ──> COMPLETED
                              │                     │           │
                              ▼                     ▼           ▼
                          REPLANNING <────────── BLOCKED      FAILED / ABANDONED
```

---

## 4. Capability Awareness OS

Hermes maintains a first-class `CapabilityRegistry` with machine-readable manifests:
- **On-Demand Skills (Claude & OpenClaw Inspired)**: Compact metadata kept in registry; complete `SKILL.md` loaded into context only when the capability is selected.
- **Control-Plane Slash Commands**: Models commands as internal control policies (`/plan`, `/research`, `/deep-research`, `/think`, `/fast`, `/autonomous`, `/goal`, `/compact`, `/refine`, `/evaluate`, `/rollback`).
- **Capability Graph**: Hierarchical ontology spanning Research, Coding, Computer Use, and Autonomous Execution.

---

## 5. Dynamic Runtime Substrates (LangGraph & Deep Agents)

Hermes sits above execution frameworks and compiles plans into appropriate substrates:
1. **LangGraph Dynamic StateGraph**:
   - Compiles `ExecutionPlanIR` into an executable state graph (`DynamicStateGraph`).
   - Each goal becomes a state node; dependencies become directed edges; execution waves become checkpoint boundaries.
2. **Deep Agents Isolated Subagent Workspaces**:
   - Maps tasks to isolated scratchpad directories (`.hermes/subagent_sandboxes/`).
   - Injects task-local context packages, completely shielding the lead agent from raw tool output flooding.

---

## 6. Plan Validity Monitoring & Adaptive Replanning

The `PlanValidityMonitor` tracks plan validity score $V \in [0.0, 1.0]$ in real time:
- **$V \ge 0.70$**: `NOMINAL` execution.
- **$0.40 \le V < 0.70$**: `LOCAL_REPLAN` (replaces specific failed subgoal while preserving overall DAG).
- **$V < 0.40$ or Invariant Violation**: `GLOBAL_REPLAN` (re-enters Cognitive Compiler for full mission re-synthesis).
