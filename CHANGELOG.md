# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (structure + quality rounds)
- Root restructure: vendored `workspaces/` removed, shim packages removed,
  dead entry points / integration / eval code archived with mapping READMEs,
  docs consolidated under `docs/`, CI structure/canonical/cycle guardrails
- Benchmark annex consolidated under `benchmarks/` (`arc_engine`,
  `arc_game`, `core_suites`, `solvers/arc_agi_3`); `test_*`-named source
  modules renamed; dead eval singletons archived
- Eagle Eye research integrated behind governance (`eagle_adapter`,
  P6 lane, radar mining, memory ingest, health job, dashboard panel)
- Hermes-first LLM chain with persistent circuit breaker; 22 executable
  safety invariants; Hermes lifecycle controller with leases
- `planning.py` split (`planning_registry.py`), `docs/CANONICAL.md`,
  import-cycle allowlist, per-tool plane metrics, 30+ new subsystem tests
- `interactive` mission loop in CLI; `metrics`, `compact`, `sandbox`,
  `skills`, `llm`, `api` commands; Task Scheduler + backup scripts

### Added (earlier)
- 24/7 daemon loop with disk-backed queue, crash resume, PID lock, scheduler
  (interval + daily), watchdog ticks
- HermesController: profile-isolated lifecycle, role-capped delegation,
  background leases + explicit complete, safe update
- Hermes-first LLM chain (managed router → detected servers → local →
  cloud → deterministic) with TTL probe cache, persistent circuit breaker,
  `llm status/refresh/--ask` CLI
- Skill OS: versioned registry + forge + Hermes-agent sync (58 skills) +
  3 seed skills + `skills` CLI
- Memory: vector + knowledge-graph backends, ranked recall, P22
  consolidation, economic ledger, calibration
- Safety: 22 executable invariants, R0–R3 plugin manifests, kill switch,
  Level-10 approval gates
- Experiments engine + Docker sandbox (explicit local fallback) + arch
  search with Pareto/A-B + BaselineTracker promotion
- Supervisor closed-loop actuation, LLM redirect, signal-gated stagnation
  detector fed by real wave outcomes
- Context compaction runtime (`compact` CLI + `compact_context` tool)
- MCP durable tasks (submit/poll/cancel with leases)
- FastAPI status API with key auth (`api serve`), static dashboard builder
- Ops: CONTINUOUS_OPS.md, Task Scheduler install/uninstall, state
  backup/restore, 30+ new subsystem tests (213 green)

### Fixed
- CLI `daemon run` nested `asyncio.run` crash
- `SLOW_PROGRESS` misclassified as stagnation; wall-clock-only PLATEAU
  verdicts require detector signal
- Background delegates saturating Hermes capacity on long runs
- `Event loop is closed` httpx noise via in-loop client cleanup
- Stale editable install shadowing the checkout (`pip install -e .`)
- Pytest collection error caused by `test_pass = _pass` alias in test_phase3_4.py, test_phase5.py, test_phase6.py, test_phase7.py, test_phase8.py — removed the alias and replaced all `test_pass()` calls with `_pass()` to prevent pytest from collecting them as test functions
- All 1995 tests now pass (previously 39 failed due to pytest NameError/collection issues)

### Added
- Created state/self_model.json with empirical capability metrics (test counts, pass rates, calibration)
- Created state/belief_graph.json with structured belief tracking
- Complete CI/CD pipeline with GitHub Actions
- Docker multi-stage build and docker-compose for local dev
- Pre-commit hooks for code quality
- Mkdocs documentation site
- Monitoring stack (Prometheus + Grafana)
- Security scanning (bandit, pip-audit)
- Type checking with mypy
- Linting and formatting with ruff
- Test coverage reporting
- Release automation (PyPI, GitHub Releases)

## [1.0.0] - 2026-08-30

### Added
- Plugin framework with 82+ plugins
- Dynamic configuration with hot-reload
- High availability (circuit breaker, failover, degradation)
- Hermes Agent integration (profiles, kanban, cron, MCP)
- Continuous development system (24/7 improvement loop)
- A/B testing and canary deployments
- Rollback capabilities
- Progress dashboard
- Training pipeline with fine-tuning
- Daily improvement scheduler
- Threat modeler for security analysis
- Proof checker for formal verification
- Capability registry (31 capabilities, 5 domains)
- V9 engineering operations (CI, deploy, incidents, releases)
- V10 full system integration
- V11 coding intelligence and dynamic workflows

[Unreleased]: https://github.com/itsPremkumar/hermes-agi-asi-harness/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/itsPremkumar/hermes-agi-asi-harness/releases/tag/v1.0.0
