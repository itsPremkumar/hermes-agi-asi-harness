# AgentForge-X

**Kernel + Evolution Engine** — Framework for building, testing, and evolving AI agent fleets.

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run tests
pytest tests/ -v --cov=src/agentforge_x --cov-report=term-missing

# Verify conformance
agentforge-x verify

# Run lint
ruff check src/ tests/
```

## Architecture

```
agentforge_x/
├── contracts.py   # Runtime contract assertions (AgentState, JSONL, protocol)
├── cli.py         # Click CLI (verify, version)
└── __init__.py    # Public exports
```

## Quality Gates

| Gate | Requirement | Status |
|------|-------------|--------|
| Tests | pytest green, >=85% coverage | ✅ 51 tests, 99% coverage |
| Lint | ruff check clean | ✅ 0 errors |
| Type Check | mypy warn-only | ⚠️ Optional |
| Docs | README + module docstrings | ✅ |
| CI | GitHub Actions py3.11/3.12 | ✅ |

## Conformance Harness

The conformance harness validates runtime contracts:

```python
from agentforge_x.contracts import (
    assert_agent_state_keys,
    assert_jsonl_line,
    assert_agent_proto,
    assert_status_transition,
)

# Validate agent state
state = {"id": "a1", "name": "agent", "status": "running", "model": "gpt-4"}
assert_agent_state_keys(state)

# Validate JSONL event
event = '{"ts": "...", "task_id": "a1", "event": "heartbeat"}'
assert_jsonl_line(event)

# Validate agent definition
agent = {"apiVersion": "taskforge.dev/v1", "kind": "Agent", ...}
errors = assert_agent_proto(agent)

# Validate status transition
assert assert_status_transition("idle", "running")
```

## License

MIT
