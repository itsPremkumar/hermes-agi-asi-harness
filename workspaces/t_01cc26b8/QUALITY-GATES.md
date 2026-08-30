# Quality Gates — Definition of Done per Module

## AgentForge-X v1.0.0

---

## 1. contracts.py — Conformance Harness

### Contract Assertions
- [ ] `assert_agent_state_keys()` — validates AgentState required keys
- [ ] `assert_agent_state_keys(strict=True)` — validates all canonical keys
- [ ] `assert_jsonl_line()` — validates JSONL event format (ts, task_id, event)
- [ ] `assert_agent_proto()` — validates .agent file schema (apiVersion, kind, metadata, spec)
- [ ] `assert_status_transition()` — validates state machine transitions

### DoD
- All 5 functions have type hints
- All 5 functions have docstrings
- All functions tested with positive and negative cases
- Self-check exit code 0

### Test Coverage
- test_contracts.py: 27 tests
- Covers: required keys, missing keys, strict mode, JSONL parsing, invalid JSON, missing keys, invalid event types, non-dict JSON, all event types, agent proto validation, status transitions

---

## 2. cli.py — Command-Line Interface

### Contract Assertions
- [ ] `agentforge-x verify` — runs self-check, exits 0
- [ ] `agentforge-x version` — shows version string

### DoD
- Click-based CLI group with subcommands
- Uses rich for colored output
- Self-check validates contracts import + basic assertion works

### Test Coverage
- test_integration_e2e.py::TestCLI: 2 tests
- Covers: verify command, version command

---

## 3. Fleet Manager (from t_ce0a8dec)

### Contract Assertions
- [ ] YAML fleet definition parsing
- [ ] Agent definition validation (model, steps, tools)
- [ ] Fleet graph validation (no cycles, valid links)
- [ ] Spawn/scale/route operations

### DoD
- YAML fleet file → FleetManager instantiation
- Schema validation rejects invalid definitions
- Graph validation catches cycles and bad links
- Dynamic spawn/scale/route with registry

### Test Coverage
- test_integration_e2e.py::TestFleetManager: 4 tests
- Covers: YAML parsing, agent names, models, steps

---

## 4. Integration E2E

### Mock-LLM → Spawn → Run → Critique → Checkpoint → Resume

### DoD
- MockLLM provides deterministic responses without API calls
- Agent lifecycle: idle → running → completed (or failed → idle retry)
- Critique step produces a finding/score
- Checkpoint creates valid JSONL event
- Resume from checkpoint produces valid JSONL event
- Heartbeat and error events are valid JSONL

### Test Coverage
- test_integration_e2e.py: 18 tests total
- Covers: mock LLM, agent lifecycle, fleet manager, CLI, full e2e lifecycle, contract self-check

---

## 5. CI/CD Pipeline

### Quality Gates
- [ ] GitHub Actions workflow with py3.11/3.12 matrix
- [ ] ruff linting (line-length 100, target py39)
- [ ] pytest with --cov-fail-under=85
- [ ] Coverage report artifact upload

### DoD
- ci.yml triggers on push/PR to main
- ruff clean (no lint errors)
- pytest green with >=85% coverage
- mypy type check (warn-only)

---

## 6. General DoD (All Modules)

### Code Quality
- [ ] ruff check clean
- [ ] Type hints on all public functions
- [ ] Docstrings on all public functions
- [ ] No hardcoded secrets (verified by qa_harness)

### Testing
- [ ] pytest green with >=85% coverage
- [ ] No test files with collection errors
- [ ] Mock external dependencies (no API calls in tests)

### Documentation
- [ ] README.md with install/quickstart
- [ ] Module-level docstrings
- [ ] Test coverage report in CI

### Verification
- [ ] qa_harness PASS on workspace
- [ ] proof_checklist 5/5 EARNED
- [ ] Self-check exits 0
