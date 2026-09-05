# AGENTS.md

This file guides all AI agents working in this repository.

## Project: Hermes AGI/ASI Harness v3.0

**Unified agent runtime** — plugin-based, model-agnostic, safety-first.

## Architecture

```
hermes_agi_v2.py    ← Unified entry point (all legacy entry points redirect here)
├── core/            ← Core runtime (kernel, agents, orchestrator)
├── plugins/         ← 135+ plugins (safety, memory, research, evolution)
├── harnix/          ← LangGraph StateGraph runtime kernel
├── src/             ← Source modules (benchmarks, harness, security, mesh)
├── agents/          ← Agent type definitions (coder, executor, planner, etc.)
├── tests/           ← Test suite (88 test files, 1300+ test functions)
└── tools/           ← Tool registry
```

## Key Files

- `hermes_agi_v2.py` — Unified CLI (replaces all legacy entry points)
- `core/runtime/kernel.py` — HermesKernel, the trusted inner ring
- `harnix/kernel.py` — LangGraph StateGraph builder
- `plugins/self_model/` — Capability measurement plugin (#1 priority improvement)
- `plugins/event_sourced_state/` — Event-sourced state plugin (#2 priority improvement)
- `tests/test_safety_validation.py` — Safety validation tests

## Plugin System

Each plugin lives in `plugins/<name>/` with:
- `__init__.py` — Plugin implementation + re-exports
- `plugin.yaml` — Metadata, capabilities, dependencies, config

## Safety

- `core/safety/self_replicate_guard.py` — Prevents unauthorized self-replication
- `core/safety/injection_defense.py` — Prompt injection detection
- `plugins/safety_gates/` — R0-R6 action gate enforcement

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run safety tests
python -m pytest tests/test_safety_validation.py -v

# Run with coverage
python -m pytest tests/ --cov=core --cov=harnix --cov=plugins
```

## Development

1. **Before coding**: Read `README.md` and `AGENTS.md`
2. **Plugin**: Create `plugins/<name>/__init__.py` + `plugin.yaml`
3. **Safety**: Always add tests to `tests/test_safety_validation.py`
4. **Entry point**: Use `hermes_agi_v2.py` — never create new entry points
5. **Agent protocol**: See `AGENTS.md` for message format and lifecycle

## Important

- **No parallel code trees**: Use `core/` not `src/` for new modules
- **Single entry point**: All CLI goes through `hermes_agi_v2.py`
- **Test safety**: Every safety module MUST have validation tests
- **Event sourcing**: State changes go through event store, not direct mutation
- **Self-model**: Every agent reports capability measurements after tasks
