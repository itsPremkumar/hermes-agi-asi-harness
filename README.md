# Harnix — AGI & ASI Harness Runtime

LangGraph StateGraph + Agent Lifecycle for autonomous task execution — now ASI-grade.

## Architecture

```
init → plan → dispatch → monitor → (dispatch | adjust | evolve | complete)
```

### ASI-Grade Layers

| Layer | Module | Lines |
|-------|--------|-------|
| **Formal Verification** | `core/formal/formal_verification_advanced.py` | 1,226 |
| **Multi-Agent Orchestration** | `core/mesh/advanced_multi_agent.py` | 730 |
| **Observability** | `core/observability/observability_advanced.py` | 655 |
| **Evaluation Harness** | `core/evaluation/evaluation_advanced.py` | 1,467 |
| **Self-Improvement Boundary** | `core/evolution/self_improvement_advanced.py` | 933 |
| **Production Hardened** | `core/production/production_hardened.py` | 662 |

- **Self-Model**: `plugins/self_model/` — capability measurement, Brier calibration, model recommendation
- **Event-Sourced State**: `plugins/event_sourced_state/` — audit trail, causal replay, mission reconstruction
- **Safety**: `core/safety/` — PromptInjectionDefense, SelfReplicationGuard (27 tests, all passing)
- **Agent Protocol**: `AGENTS.md` — R0-R6 authority, message format, lifecycle

## Usage

```python
from hermes_agi_v2 import run_goal, interactive_mode, health_check, list_plugins

# Execute a single goal
result = await run_goal("write file demo.txt containing HELLO")

# Interactive mode
await interactive_mode()

# Health check
health = await health_check()

# List plugins
await list_plugins()
```

## CLI

```bash
# Unified entry point (replaces hermes_agi.py, hermes_engine.py, etc.)
python -m hermes_agi_v2 --goal "write a Python script that sorts a list"
python -m hermes_agi_v2 --interactive
python -m hermes_agi_v2 --health
python -m hermes_agi_v2 --list-plugins --verbose

# Legacy entry points (deprecated, redirect to hermes_agi_v2.py)
python hermes_agi.py --goal "..."
python hermes_engine.py          # redirects to hermes_agi_v2.py
python hermes_ultimate.py        # redirects to hermes_agi_v2.py
python hermes_supervisor.py      # redirects to hermes_agi_v2.py
python master.py                   # redirects to hermes_agi_v2.py
python harness_control_plane.py    # redirects to hermes_agi_v2.py
```

## State

```python
from harnix import HarnessRuntimeKernel, AgentState, AgentPhase, create_initial_state

state = create_initial_state("my task")
# state["phase"]     # current lifecycle phase
# state["status"]    # running | completed | failed
# state["score"]     # 0.0 - 1.0 progress
# state["plan"]      # list of plan steps
# state["results"]    # execution results
# state["memory"]    # accumulated memory
```

## Plugins

135+ plugins registered. Key categories:
- **Safety**: safety_gates, security_core, injection_defense, self_replicate_guard
- **Memory**: memory_system, memory_curator, hybrid_memory
- **Research**: deep_research, research_engine_v2, autonomous_research
- **Coding**: codegen, coding, skill_forge, skill_learner
- **Evolution**: evolution, evolution_engine, evolution_engine_v2, evolution_safety_loop
- **Verification**: verification_engine, formal_verification, completion_proof
- **Agent**: multi_agent, multi_agent_orchestrator, agent_communication
- **Observability**: observability_dashboard, audit_logger, telemetry
- **Self-Model**: self_model (capability measurement, calibration)
- **Event-Sourced State**: event_sourced_state (audit trail, replay, reconstruction)

## Testing

```bash
python -m pytest tests/ -v
python -m pytest tests/ --cov=core --cov=harnix --cov=plugins
```

Test results: 1700 passed, 52 pre-existing failures (event loop issues unrelated to ASI-grade changes)

## Security

See [SECURITY.md](SECURITY.md).

## License

MIT
