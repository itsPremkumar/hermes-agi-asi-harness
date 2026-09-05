# Canonical subsystem map

Three generations of the same systems coexist. **New code imports the
canonical module (middle column).** Legacy generations stay for their tests;
do not extend them.

| Subsystem | Canonical (extend this) | Legacy (read-only) |
|---|---|---|
| OS kernel / mission pipeline | `hermes_os/kernel.py` | `core/kernel.py`, `core/runtime/kernel.py`, `harnix/kernel.py` |
| Supervision | `hermes_os/supervisor.py` (+ actuation) | `core/supervisor.py`, `core/runtime/supervisor.py`, `core/avo/supervisor.py`, `plugins/supervisor/` |
| Planning | `hermes_agi/planning.py` + `planning_registry.py`, `hermes_os/meta_planner.py` | `core/planning.py`, `core/runtime/planner.py`, `core/dynamic/planning_engine.py` |
| Planning data | `hermes_agi/planning_registry.py` | — (split 2026-09; `planning.py` re-exports) |
| Model routing | `hermes_os/model_router.py` + `ModelPortfolio` | `plugins/model_router/`, `core/*router*` |
| Memory | `memory/` (`manager`, `subsystems`, `ranking`, `vector_graph`, `consolidation`, `ledger`) | `plugins/memory*/`, `core/memory.py`, `core/supervisor/memory.py` |
| Verification | `verification/vnext.py` (L0–L6) | `plugins/verification_engine/`, `plugins/completion_proof/` |
| Safety | `hermes_os/safety_kernel.py` + `invariants.py` | `safety/*` (except live `threat_modeler`), `plugins/safety_gates/`, `core/safety/` (archived) |
| Evolution | `hermes_os/evolution_lab.py` + `arch_search.py` | `core/avo/*`, `engines/avo/*`, `plugins/evolution*/` |
| Research | `hermes_os/research.py` + `eagle_adapter.py`, `deep_research/engine.py` | `plugins/deep_research*/`, `core/research_engine.py` |
| Skills | `hermes_os/skills.py` + `skills/` registry | `plugins/skill_forge/`, `plugins/skill_learner/`, `core/coding/skill_forge.py` |
| Scheduler | `hermes_os/scheduler.py` + `cron_expr.py` | `daily_improvement/`, `agent_eye/scheduler.py` |
| Watchdog | `hermes_os/watchdog.py` (resources) + `process_guard.py` (processes) | `plugins/watchdog/`, `plugins/circuit_breaker/` |
| Metrics/cost | `hermes_os/plane_metrics.py`, `plane_cache.py`, `memory/ledger.py`, `tool_scoring.py` | `plugins/cost_enforcer/` (archived), `plugins/economic_ledger/` |
| Recovery | `hermes_os/recovery.py` | `plugins/recovery_engine/`, `plugins/circuit_breaker/recovery.py` |
| Agent fabric | `hermes_os/agent_fabric.py` + `hermes_controller.py` | `core/runtime/agent.py`, `plugins/agent_fabric/`, `plugins/multi_agent*/` |
| World model | `world_model/` | `core/world_model.py`, `plugins/world_model/` |
| Invariants | `hermes_os/invariants.py` | `context_os/invariants.py` (contract layer; safety enforces) |
| Benchmarks | `hermes_agi/benchmarks/runner.py`, `benchmarks/` annex | `core/benchmark/`, `plugins/benchmark*` (archived) |
| Tool env | `hermes_os/tool_env.py` | `plugins/{shell,filesystem,http,python,git}_tool/`, `core/runtime/plugin_base.py` |

Enforcement: `scripts/check_canonical.py` fails CI if `src/hermes_os/*`,
`src/memory/*`, or `src/hermes_agi/__main__.py` import a legacy generation
(`-Planner-` spot-names below are illustrative; the script holds the list).
It also fails on any `src.`-prefixed import in `tests/`: with both repo root
and `src/` on `sys.path`, `src.X` and bare `X` load as twin module objects
and silently break `pytest.raises` / `isinstance` — always use bare roots.
