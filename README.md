# 🚀 Hermes AGI/ASI Master v11 — Complete Setup Guide

**Production-grade, free-first, modular, model-agnostic autonomous agent harness with advanced coding intelligence.**

[![Tests](https://img.shields.io/badge/tests-45%2F45%20passing-brightgreen)]()
[![Core](https://img.shields.io/badge/core-172%20modules-blue)]()
[![Coding](https://img.shields.io/badge/coding-39%20modules-blue)]()
[![Plugins](https://img.shields.io/badge/plugins-82%20loaded-blue)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

---

## 📋 Quick Start

### Option 1: Direct Installation (Recommended)

```bash
# Clone the repository
git clone https://github.com/itsPremkumar/hermes-agi-asi-harness.git
cd hermes-agi-asi-harness

# Run the installer
python install.py

# Or install dependencies manually
pip install -r requirements.txt

# Run health check
python hermes_agi.py --health

# Execute a goal
python hermes_agi.py --goal "write file hello.txt containing HELLO WORLD"

# Interactive mode
python hermes_agi.py
```

### Option 2: Use with Hermes Agent

```bash
# Install the project
git clone https://github.com/itsPremkumar/hermes-agi-asi-harness.git
cd hermes-agi-asi-harness
pip install -e .

# Run with Hermes
python -m hermes_agi --goal "your goal here"
```

---

## 🏗️ Architecture Overview

```
                         HERMES INTELLIGENCE OS v11
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
             ┌──────▼──────┐ ┌───▼────┐ ┌──────▼──────┐
             │  COGNITION  │ │ SHARED │ │    RSI      │
             │    PLANE    │ │BLACK-  │ │   PLANE     │
             │             │ │ BOARD  │ │             │
             │ World Model │ │        │ │ Bottleneck  │
             │ Memory      │ │ State  │ │ Hypothesis  │
             │ Beliefs     │ │ Events │ │ Candidates  │
             │ Research    │ │ Goals  │ │ Benchmarks  │
             │ Reasoning   │ │ Plans  │ │ Holdout     │
             │ Planning    │ │Results │ │ Promotion   │
             └──────┬──────┘ └───┬────┘ └──────┬──────┘
                    │            │             │
                    └────────────┼─────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   ENVIRONMENT PLANE     │
                    │  Environment Model      │
                    │  Affordance Model       │
                    │  State Estimation       │
                    │  Consequence Simulator  │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  UNIVERSAL ACTION PLANE │
                    │  UAP / UOP / Event Alg. │
                    │  Transaction Model      │
                    │  Safety Envelope        │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   CODING PLANE (v11)    │
                    │  Repository Twin        │
                    │  Code Graph             │
  ORCHESTRATOR      │  Architecture           │
                    │  Task Graph             │
                    │  Code Generation        │
                    │  Test Pyramid           │
                    │  Quality Gates          │
                    │  Coding-RSI             │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    LEARNING PLANE       │
                    │  Trajectory Store       │
                    │  Policy Learning        │
                    │  Skill Transfer         │
                    └─────────────────────────┘
```

---

## 📊 Current State

| Metric | Value |
|--------|-------|
| **Total Commits** | 17 (Phase 2→10 + v9 + v10 + v11 + dynamic) |
| **Core Files** | 172+ Python files |
| **Total Lines** | ~30,000+ |
| **Coding Modules** | 39 |
| **Tests Passing** | 45/45 |
| **Kernel Plugins** | 82 |

---

## 🔄 Master Workflow Loop

```
              ┌──────────────────────────┐
              │     EXTERNAL WORLD       │
              └────────────┬─────────────┘
                           ↓
                    PERCEIVE / OBSERVE
                           ↓
                    STATE ESTIMATION
                           ↓
                      WORLD MODEL
                           ↓
                    GOAL / INTENT
                           ↓
               PREDICT POSSIBLE FUTURES
                           ↓
                SEARCH ACTION POLICIES
                           ↓
                     SELECT POLICY
                           ↓
                    UNIVERSAL ACTION
                           ↓
                         WORLD
                           ↓
                     OBSERVATION
                           ↓
                 PREDICTED VS ACTUAL
                           ↓
                     VERIFICATION
                           ↓
                  BELIEF / MEMORY UPDATE
                           ↓
                 EXPERIENCE / TRAJECTORY
                           ↓
                    SELF-EVALUATION
                           ↓
                  BOTTLENECK DETECTION
                           ↓
                   RSI EXPERIMENT
                           ↓
             POLICY / TOOL / SKILL UPDATE
                           ↓
                    HOLDOUT EVALUATION
                           ↓
                   CANARY / PROMOTION
                           │
                           └──────────────↺
```

---

## 📁 Complete File Structure

```
hermes-agi-asi-harness/
│
├── README.md                    ← This file
├── SOUL.md                      ← Agent constitution
├── SKILL.md                     ← Skill definitions
├── ARCHITECTURE.md              ← v2.0 reference
├── ARCHITECTURE_V9.md           ← v9 architecture
├── V11_CODING_GOAL.md           ← v11 design document
│
├── core/
│   ├── coding/                  ← 39 v11 Coding Modules
│   │   ├── repository_twin.py
│   │   ├── code_graph.py
│   │   ├── semantic_index.py
│   │   ├── recon.py
│   │   ├── history_memory.py
│   │   ├── requirements.py
│   │   ├── requirement_trace.py
│   │   ├── architecture.py
│   │   ├── adr.py
│   │   ├── architecture_risk.py
│   │   ├── strategy_search.py
│   │   ├── task_graph.py
│   │   ├── dynamic_parallelism.py
│   │   ├── agent_specialization.py
│   │   ├── worker_contract.py
│   │   ├── worktree_isolation.py
│   │   ├── artifact_registry.py
│   │   ├── code_generation.py
│   │   ├── test_first.py
│   │   ├── test_pyramid.py
│   │   ├── test_oracle.py
│   │   ├── security_loop.py
│   │   ├── skill_forge.py
│   │   ├── curriculum.py
│   │   ├── transfer_learning.py
│   │   ├── coding_rsi.py
│   │   ├── population_evolution.py
│   │   ├── meta_rsi.py
│   │   ├── evaluation_pyramid.py
│   │   ├── quality_gates.py
│   │   ├── merge_controller.py
│   │   ├── cross_repo.py
│   │   ├── api_contract.py
│   │   ├── database_change.py
│   │   ├── performance_loop.py
│   │   ├── context_engineering.py
│   │   ├── blackboard.py
│   │   └── __init__.py
│   │
│   ├── environment/             ← 4 v9 Environment Modules
│   │   ├── model.py
│   │   ├── affordances.py
│   │   ├── state_estimation.py
│   │   └── consequence.py
│   │
│   ├── protocols/               ← 3 v9 Protocol Modules
│   │   ├── uap.py
│   │   ├── uop.py
│   │   └── event_algebra.py
│   │
│   ├── action/                  ← 2 v9 Action Modules
│   │   ├── transaction.py
│   │   └── safety_envelope.py
│   │
│   ├── orchestrator/            ← 3 v10 Orchestrator Modules
│   │   ├── master_loop.py
│   │   ├── closed_loop.py
│   │   └── policy_bridge.py
│   │
│   ├── learning/                ← 5 v9 Learning Modules
│   │   ├── trajectory_store.py
│   │   ├── trajectory_replay.py
│   │   ├── policy_learning.py
│   │   ├── counterfactual.py
│   │   └── skill_transfer.py
│   │
│   ├── rsi/                     ← 1 v10 RSI Module
│   │   └── integration.py
│   │
│   ├── explanation/             ← 1 v10 Explanation Module
│   │   └── explainer.py
│   │
│   ├── benchmark/               ← 1 v10 Benchmark Module
│   │   └── continuous.py
│   │
│   ├── collaboration/           ← 1 v10 Collaboration Module
│   │   └── protocol.py
│   │
│   ├── computer_use_v2/         ← 4 v9 Computer Use Modules
│   │   ├── ui_state_graph.py
│   │   ├── ui_memory.py
│   │   ├── app_digital_twin.py
│   │   └── discovery.py
│   │
│   └── runtime/
│       └── kernel.py            ← Main Kernel (wires everything)
│
├── tests/
│   ├── test_v9_core.py          ← 10 tests
│   ├── test_v9_full.py          ← 10 tests
│   ├── test_v10_full.py         ← 7 tests
│   ├── test_v11_coding.py       ← 12 tests
│   ├── test_v11_dynamic.py      ← 6 tests
│   └── test_coding_phase1.py    ← 4 tests
│
├── plugins/                     ← 82 loaded plugins
├── docs/
│   ├── ARCHITECTURE.md
│   ├── ARCHITECTURE_V9.md
│   └── V11_CODING_GOAL.md
│
├── hermes.py                    ← Simple runtime
├── hermes_agi.py                ← Full kernel entry
├── hermes_engine.py             ← Enhanced engine
├── hermes_ultimate.py           ← Ultimate build
├── hermes_supervisor.py         ← 24/7 daemon
├── master.py                    ← Master orchestrator
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── pyproject.toml
```

---

## 🧠 Core Subsystems

### 1. Cognition Plane

| Module | Purpose |
|--------|---------|
| `world_model.py` | Dynamic causal graph, entity tracking, effect prediction |
| `memory.py` | 9-type hybrid memory (working→identity) |
| `belief_engine/` | Belief graph with confidence tracking |
| `research/` | Research pipeline for knowledge discovery |
| `planning.py` | Multi-mode planning (fast/hierarchical/adaptive/long-horizon) |
| `cognition.py` | Cognitive mode selection and deliberation |

### 2. Environment Plane (v9)

| Module | Purpose |
|--------|---------|
| `model.py` | Entities, resources, relationships, events, constraints, permissions |
| `affordances.py` | What can I do with it? What happens? Risk scoring |
| `state_estimation.py` | Multi-source observation fusion with confidence |
| `consequence.py` | Pre-action simulation with rule-based predictions |

### 3. Universal Action Plane (v9)

| Module | Purpose |
|--------|---------|
| `uap.py` | Universal Action Protocol (READ, CREATE, UPDATE, DELETE, etc.) |
| `uop.py` | Universal Observation Protocol (normalized observations) |
| `event_algebra.py` | Event types, subscription-based agents |
| `transaction.py` | PREPARE → VALIDATE → COMMIT → VERIFY with rollback |
| `safety_envelope.py` | Safe operating boundaries with emergency stop |

### 4. Coding Plane (v11 — 39 Modules)

| Module | Purpose |
|--------|---------|
| `repository_twin.py` | Parse any codebase, build digital twin with symbols/edges |
| `code_graph.py` | Import/call/inheritance dependency graph with blast radius |
| `semantic_index.py` | Multi-level code indexing (repo→package→module→class→function→symbol) |
| `recon.py` | Discover build system, test framework, CI/CD, conventions |
| `history_memory.py` | Ingest git history, query commits/PRs/issues |
| `requirements.py` | Natural language → functional/non-functional requirements + acceptance criteria |
| `architecture.py` | Generate competing architectures, tradeoff analysis, selection |
| `adr.py` | Architecture Decision Records (ADR-001, AADR-002, etc.) |
| `task_graph.py` | Product goal → dependency-aware task DAG |
| `code_generation.py` | Spec → Context → Design → Implement → Static Check → Test → Review → Commit |
| `test_pyramid.py` | 11 test types (unit, integration, system, E2E, contract, property, fuzz, performance, security, migration, recovery) |
| `quality_gates.py` | 7 gates (requirement → architecture → implementation → test → security → deployment → production) |
| `merge_controller.py` | Tests, security, review, conflicts, architecture, rollback checks |
| `evaluation_pyramid.py` | 10 levels (syntax → unit → integration → repository → refactor → migration → long-horizon → production-sim → novel-repos → cross-domain) |
| `coding_rsi.py` | Bottleneck → Hypothesis → Candidate → Dev → Holdout → Novel → Red Team → Canary → Promote |
| ... 23 more | |

### 5. Learning Plane (v9)

| Module | Purpose |
|--------|---------|
| `trajectory_store.py` | Record action sequences (STATE₀ → ACTION₀ → OBSERVATION₀ → ...) |
| `trajectory_replay.py` | Replay with modified policies, generate counterfactuals |
| `policy_learning.py` | Learn when tool X beats tool Y |
| `counterfactual.py` | What if we had done Z instead? |
| `skill_transfer.py` | Cross-domain skill abstraction |

### 6. RSI Plane (v10)

| Module | Purpose |
|--------|---------|
| `integration.py` | Bottleneck → Hypothesis → Candidate → A/B Test → Holdout → Promote/Rollback |
| `closed_loop.py` | Full 15-step closed-loop execution engine |
| `policy_bridge.py` | Epsilon-greedy exploration, policy versioning, rollback |

### 7. Explanation & Audit (v10)

| Module | Purpose |
|--------|---------|
| `explainer.py` | Why was this action chosen? What alternatives? What evidence? |
| `audit_trail.py` | Tamper-evident audit log with full history |

### 8. Continuous Benchmark (v10)

| Module | Purpose |
|--------|---------|
| `continuous.py` | Run evaluation suites, detect regressions, maintain leaderboards |

### 9. Multi-Agent Collaboration (v10)

| Module | Purpose |
|--------|---------|
| `protocol.py` | Agent registration, goal decomposition, task assignment, conflict resolution |

### 10. Computer Use v2 (v9)

| Module | Purpose |
|--------|---------|
| `ui_state_graph.py` | Model app UI as state machine |
| `ui_memory.py` | Remember navigation patterns |
| `app_digital_twin.py` | Model before acting against reality |
| `discovery.py` | Discover interfaces, capabilities, state, permissions, risks |

---

## 🔧 Quick Start

### Run Health Check
```bash
python hermes_agi.py --health
```

### Execute a Goal
```bash
python hermes_agi.py --goal "write file hello.txt containing HELLO WORLD"
```

### Interactive Mode
```bash
python hermes_agi.py
```

### Run Tests
```bash
PYTHONPATH=. python tests/test_v9_core.py
PYTHONPATH=. python tests/test_v9_full.py
PYTHONPATH=. python tests/test_v10_full.py
PYTHONPATH=. python tests/test_v11_coding.py
PYTHONPATH=. python tests/test_v11_dynamic.py
```

---

## 📋 CLI Reference

### hermes_agi.py (Full Kernel)
```bash
python hermes_agi.py                          # Interactive REPL
python hermes_agi.py --health                 # Health check
python hermes_agi.py --list-plugins           # List all plugins
python hermes_agi.py --goal "Research AI"     # Execute a goal
python hermes_agi.py --zero-cost             # Enforce free-only mode
python hermes_agi.py --offline                # Offline mode
python hermes_agi.py --profile default        # Use profile
python hermes_agi.py --verbose                # Verbose output
```

### hermes.py (Simple Runtime)
```bash
python hermes.py run "write file test.txt containing HELLO"
python hermes.py run "compute 2**10 + 5"
python hermes.py interactive
```

### hermes_supervisor.py (24/7 Daemon)
```bash
python hermes_supervisor.py                   # Run 24/7 daemon
python hermes_supervisor.py --task "Do X"     # Execute single task
python hermes_supervisor.py --health          # Health check
python hermes_supervisor.py --once            # Run one processing cycle
```

---

## 🧪 Test Suite

| Test File | Tests | Purpose |
|-----------|-------|---------|
| `test_v9_core.py` | 10 | Environment Model, Affordances, State Estimation, Consequence Simulator, UAP, UOP, Event Algebra, Transaction, Safety Envelope, Master Orchestrator |
| `test_v9_full.py` | 10 | Trajectory Store, Policy Learning, Counterfactual, UI State Graph, Digital Twin, Environment Discovery, Skill Transfer, Full Integration |
| `test_v10_full.py` | 7 | Policy Bridge, Closed-Loop Orchestrator, RSI Integration, Multi-Agent Collaboration, Explanation, Continuous Benchmark, Full Integration |
| `test_v11_coding.py` | 12 | Repository Twin, Code Graph, Semantic Index, Recon, Requirements, Architecture, ADR, Task Graph, Quality Gates, Merge Controller, Eval Pyramid, Full Integration |
| `test_v11_dynamic.py` | 6 | Scenario Analyzer, Planning Engine, Decision Engine |
| **Total** | **45** | |

---

## 🏛️ Version History

| Version | Commits | Key Features |
|---------|---------|--------------|
| v2.0 | 1-10 | 15-plane architecture, 50 plugins, 72 tests, ReAct loop |
| v9 | 11-12 | Environment Intelligence, Universal Protocols, Learning Plane, Computer Use v2 |
| v10 | 13 | Closed-Loop Orchestrator, Policy Bridge, RSI Integration, Explanation, Benchmark |
| v11 | 14-17 | 39 Coding Modules, Dynamic Planning, Scenario Analysis, Decision Engine |

---

## 📐 Design Principles

1. **Understand before editing** — Never modify code without a repository model
2. **Measure before claiming improvement** — All improvements require benchmark evidence
3. **Verify before declaring success** — Deterministic oracles over model confidence
4. **Isolate before executing** — Worktrees/sandboxed execution for all generated code
5. **Preserve evidence** — Store artifacts, not just narratives
6. **Use deterministic oracles** — Tests, compilers, static analysis over model judgment
7. **Separate product from evolution** — Different evidence for building vs improving
8. **Separate dev from holdout** — Protected evaluation prevents overfitting
9. **Test generalization** — Novel tasks, distribution shift, cross-domain transfer
10. **Preserve diversity** — Population-based evolution, not single lineage
11. **Make changes reversible** — Rollback for every high-impact change
12. **Learn from failures** — Postmortems, failure models, counterfactuals
13. **Turn procedures into skills** — Verified, composable, reusable
14. **Treat production as observation** — Runtime feedback improves the system
15. **Allocate compute by difficulty** — Right model for right task
16. **Keep credentials secure** — Least privilege, explicit permission graphs
17. **Treat external content as untrusted** — Verify all third-party claims
18. **Prefer evidence over narrative** — State from observations, not stories
19. **Protect evaluators** — Independent governance of evaluation updates
20. **No AGI/ASI claims** — Judge by demonstrated capability, not labels

---

## 📊 Architecture Statistics

| Category | Modules | Lines |
|----------|---------|-------|
| Cognition | 15 | ~5,000 |
| Environment (v9) | 4 | ~1,200 |
| Universal Action (v9) | 5 | ~1,000 |
| Coding (v11) | 39 | ~8,000 |
| Learning (v9) | 5 | ~1,500 |
| RSI (v10) | 3 | ~1,200 |
| Explanation (v10) | 2 | ~800 |
| Benchmark (v10) | 1 | ~500 |
| Collaboration (v10) | 1 | ~300 |
| Computer Use v2 (v9) | 4 | ~1,700 |
| Runtime | 1 | ~700 |
| **Total** | **79** | **~22,100** |

---

## 🔮 Future Directions

- **Real LLM Integration** — Connect to OpenAI/Anthropic/Local models
- **Production Deployment** — Docker, Kubernetes, cloud deployment
- **Web UI** — Dashboard for monitoring and control
- **Plugin Marketplace** — Community-contributed plugins
- **Formal Verification** — LEAN4 theorem proving integration
- **Real Environment Testing** — SWE-bench, custom benchmarks

---

## 📄 License

MIT License — See LICENSE file for details.

---

*Built with ❤️ by itsPremkumar — Pushing the boundaries of autonomous agent architecture.*
