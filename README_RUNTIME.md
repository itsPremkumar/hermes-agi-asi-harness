# Hermes Agent Runtime — Plugin Harness

A working, fully-local agent runtime built on top of the 21 implemented plugins.
No LLM API is required — every capability is a plugin that runs deterministic code.

## What was built

| Layer | File | Responsibility |
|-------|------|---------------|
| Kernel | `core/runtime/agent_kernel.py` | Discovers `plugins/*/__init__.py`, loads each `Plugin`, builds name + capability registry, health checks |
| Context | `core/runtime/context.py` | Unifies `state_manager`, `memory_curator`, `permission_system`, `audit_logger`, `streaming_output` behind one API |
| Planner | `core/runtime/planner.py` | Rule-based: maps a task string → ordered plugin step plan (no LLM) |
| Agent | `core/runtime/agent.py` | Execution loop: permission check → invoke → audit → retry-once → final result |
| CLI | `hermes.py` | `run "<task>"` and `interactive` REPL |

## The 21 working plugins

`state_manager`, `config_manager`, `permission_system`, `shell_tool`,
`filesystem_tool`, `http_tool`, `python_tool`, `git_tool`, `rag_engine`,
`vision_engine`, `document_intel`, `multi_agent_orchestrator`, `debate_engine`,
`swarm_intelligence`, `evolution_engine`, `skill_learner`, `memory_curator`,
`permission_sandbox`, `audit_logger`, `mcp_client`, `streaming_output`.

## Usage

```bash
# Run a single task
python hermes.py run "write file demo.txt containing HELLO"
python hermes.py run "what is 2**10 + 5?"
python hermes.py run "optimize sum of squares in [-3,3]"
python hermes.py run "remember that the project uses MIT license"
python hermes.py run "search memory for MIT license"
python hermes.py run "summarize the quick brown fox jumps over the lazy dog"

# Interactive REPL
python hermes.py interactive
```

Every action is gated by `permission_system` (R0–R6) and recorded in a
tamper-evident hash chain by `audit_logger`. State/memory/audit are isolated to a
temp `HERMES_HOME` per run so the repo stays clean.

## Tests

```bash
python test_working_plugins.py        # 21/21 — each plugin verified end-to-end
python test_runtime.py                 # 5/5  — agent runtime verified end-to-end
python test_cognitive.py               # 18/18 — event bus, ReAct loop, verifier, critic
python test_kernel_integration.py      # 11/11 — full kernel boot + task execution

# Also available (from the Ultimate Build architecture):
python hermes_agi.py --health          # Full kernel health check
python hermes_agi.py --goal "..."      # Submit a task via the HermesKernel pipeline
```

### Kernel Integration (hermes_agi.py)

The `HermesKernel` boots 11 core plugins via `create(kernel)` factories:

| Plugin | Status | Role |
|--------|--------|------|
| `security_core` | healthy | Permissions, sandbox, audit, injection defense |
| `event_bus` | healthy | Typed async events, topic patterns, replay |
| `state_manager` | healthy | SQLite state, sessions, tasks, checkpoints |
| `model_router` | healthy | Free-first model routing (local + fallback) |
| `memory_system` | healthy | 9-type hybrid memory (working→identity) |
| `plugin_manager` | healthy | Plugin discovery (36 discovered), load/enable/disable |
| `execution_engine` | healthy | ReAct + Plan-Execute loop |
| `verification_engine` | healthy | Syntax/semantic/source/tool/test verification |
| `recovery_engine` | healthy | Checkpoint/rollback/retry/resume |
| `evolution_engine` | healthy | Genetic algorithm self-improvement |
| `ecosystem_intel` | healthy | GitHub/ArXiv/HF capability discovery |

## Architecture rules honored

- The kernel is the **only** code that imports plugins; the agent never imports a
  plugin directly — it goes through `context` / `kernel` by name.
- Every external side-effect (file write, shell, http) passes `permission_system`
  first. R4+ actions require elevation/approval.
- Every action is audit-logged with actor=`agent`, result, timestamp, hash chain.
- No plugin code was modified except to fix real bugs (evolution mutation scale,
  memory_curator column indices, audit_logger chain seeding + HERMES_HOME respect).
  `state_manager`/`config_manager` tests were adapted to their real existing APIs.
