# HERMES-ASI-Master v7 → v3.0 — Gap Analysis & Improvements (UPDATED)

## Improvements Completed ✅

| # | Gap | Status | Implementation |
|---|-----|--------|----------------|
| 1 | Self-Model (v7 §50) | ✅ **DONE** | `plugins/self_model/` — capability measurement, Brier calibration, model recommendation |
| 2 | Event-Sourced State (v7 §80) | ✅ **DONE** | `plugins/event_sourced_state/` — append-only log, replay, causal chain, mission reconstruction |
| 3 | Safety Validation Tests | ✅ **DONE** | `tests/test_safety_validation.py` — 16 real injection prompts, self-replication tests |
| 4 | Entry Point Consolidation | ✅ **DONE** | `hermes_agi_v2.py` — single unified CLI, all 7 legacy entry points redirect |
| 5 | pyproject.toml Dependencies | ✅ **DONE** | Complete dependency list from real import scan |
| 6 | Agent Protocol | ✅ **DONE** | `AGENTS.md` — message format, lifecycle, safety boundaries, R0-R6 gates |
| 7 | Plugin Registration | ✅ **DONE** | `plugin.yaml` for self_model and event_sourced_state |

## Remaining Gaps (from IMPROVEMENTS.md)

### 🔴 High Priority

#### 8. Scenario Harness (v7 §45)
- **Need**: Structured scenario testing — nominal, long-horizon, failure-recovery, adversarial, distribution-shift
- **Status**: Partial — `plugins/chaos_lab/` exists but no systematic scenario harness
- **Action**: Build `plugins/scenario_harness/` with test categories and automated scenario runner

#### 9. Evaluation Data Splits (v7 §46)
- **Need**: Protected dev/holdout/novel/red-team separation
- **Status**: Benchmarks exist but no data splits
- **Action**: Add dataset splitting module with anti-Goodhart architecture

#### 10. Rollback Infrastructure (v7 §112)
- **Need**: Canary deployment, drift detection, automatic freeze/rollback
- **Status**: No systematic rollback mechanism
- **Action**: Build rollback plugin with checkpoint/restore and drift detection

#### 11. Research Engine v2 (v7 §18-19)
- **Need**: Structured evidence graph with source validation, contradiction search
- **Status**: Basic search exists, no evidence graph
- **Action**: Build evidence graph plugin with citation tracking and synthesis

#### 12. Agent Communication Contract (v7 §29)
- **Need**: Structured envelopes with artifact references, confidence, evidence
- **Status**: `plugins/agent_communication/` exists but minimal
- **Action**: Implement full contract with schema validation

### 🟡 Medium Priority

#### 13. Model Router Enhancement (v7 §31)
- Task classification, model portfolio with measured history
- Success rate / calibration / latency / cost tracking

#### 14. Compute Scaling Controller (v7 §32)
- Explicit reasoning budget per task class
- Agent count, parallelism, tool call limits

#### 15. Sandbox Architecture (v7 §34)
- Filesystem boundaries, network policy, credential isolation
- CPU/RAM limits, timeouts, kill switch

#### 16. Agent Fabric Registry (v7 §26-28)
- Dynamic agent population
- Structured lifecycle with pause/resume/checkpoint/handoff

#### 17. Simulation Layer (v7 §36)
- Digital twin from world model
- Policy experimentation before real action

### 🟢 Lower Priority (Advanced RSI)

#### 18. Model Adaptation Plane (v7 §60)
- Trajectory store → dataset → fine-tune → evaluate

#### 19. Architecture Search (v7 §69)
- Test alternative architectures per task class
- Pareto comparison of fitness vectors

#### 20. Meta-RSI (v7 §70, §107)
- Evolution-policy evaluation
- Protected meta-benchmarks

## Architecture Now

```
hermes_agi_v2.py (unified entry point)
├── core/           Core runtime
├── plugins/        135+ plugins
│   ├── self_model/         ✅ New — capability measurement
│   ├── event_sourced_state/ ✅ New — event sourcing
│   ├── safety_gates/       Safety enforcement
│   └── ... (133 more)
├── harnix/         LangGraph kernel
├── src/            Source modules
├── agents/         Agent type definitions
├── tests/          Test suite
└── tools/          Tool registry
```

## Test Coverage Target

| Current | Target |
|---------|--------|
| ~1384 test functions | ≥ 5000 (1 per core module) |
| 0.1 tests/module | ≥ 1.0 tests/module |
| Safety tests: 0 | Safety tests: 16+ |

## Key Metrics

- **Lines of code**: ~100K
- **Python files**: 751
- **Plugins**: 135+
- **Entry points**: 1 (was 7)
- **Safety tests**: 16 (was 0)
- **Self-model**: ✅ Operational
- **Event sourcing**: ✅ Operational
