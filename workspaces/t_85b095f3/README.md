# AgentOS — Operating System for AI Agents

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-150%20passed-brightgreen.svg)](https://github.com/itsPremkumar/agentos-runtime)

A runtime platform for orchestrating, scheduling, and governing autonomous AI agents with resource control, sandboxing, and multi-tenancy.

## Features

- **Agent Scheduler** — Priority-based scheduling with fairness, preemption, and resource limits
- **Resource Governor** — CPU, memory, and API rate limiting per tenant
- **Sandboxed Execution** — OS-level isolation with configurable resource limits
- **Inter-Agent Bus** — Pub/sub and RPC communication patterns
- **Persistent State** — SQLite-backed state management with WAL mode and tenant isolation
- **Plugin System** — WASM-based extensions with Python fallback
- **Observability** — OpenTelemetry-compatible traces and Prometheus metrics
- **Multi-Tenancy** — Resource quotas and tenant isolation
- **CLI & Dashboard** — Command-line interface and web dashboard

## Quickstart

### Install

```bash
pip install -e .
```

### Run the CLI

```bash
# Show version
agentos --version

# Show status
agentos status

# Submit an agent
agentos submit my-agent --priority high --cpu 1.0 --memory 512

# Run self-test
agentos self-test

# Show metrics
agentos metrics
```

### Run the Dashboard

```bash
agentos dashboard
# Open http://127.0.0.1:8080
```

### Run Tests

```bash
# Using the built-in test runner (no pytest required)
python test_runner.py

# Or with pytest
pip install -e ".[dev]"
pytest tests/ -v
```

## Architecture

```
agentos/
├── scheduler/      # Priority-based agent scheduling with preemption
├── governor/       # Resource governor (CPU, memory, API rate limits)
├── sandbox/        # Sandboxed execution environment
├── bus/            # Inter-agent communication bus (pub/sub, RPC)
├── state/          # Persistent state management (SQLite + WAL)
├── plugins/        # WASM-based plugin system
├── observability/  # OpenTelemetry traces and metrics
├── tenancy/        # Multi-tenancy with resource quotas
├── cli/            # Command-line interface
└── dashboard/      # Web dashboard
```

## Usage Examples

### Scheduling Agents

```python
from agentos.scheduler import Agent, Priority, Scheduler

scheduler = Scheduler(max_concurrent=4, max_cpu=8.0, max_memory=16384)

agent = Agent(
    id="agent-1",
    name="data-processor",
    priority=Priority.HIGH,
    cpu_quota=2.0,
    memory_quota=1024,
    tenant_id="team-a"
)

result = scheduler.submit(agent)
print(result.action)  # "scheduled" or "queued"
```

### Resource Governor

```python
from agentos.governor import ResourceGovernor, ResourceLimits

governor = ResourceGovernor(ResourceLimits(max_cpu=4.0, max_memory=8192))
governor.register_tenant("team-a")

if governor.allocate_cpu("team-a", 1.0):
    print("CPU allocated")
```

### State Management

```python
from agentos.state import StateManager

state = StateManager()
state.set("config", {"model": "gpt-4"}, tenant_id="team-a")
config = state.get("config", tenant_id="team-a")
```

### Inter-Agent Bus

```python
from agentos.bus import Bus, Message

bus = Bus()

# Subscribe
bus.subscribe("tasks", lambda m: print(f"Received: {m.payload}"))

# Publish
bus.publish(Message(topic="tasks", payload="process-data"))
```

### Observability

```python
from agentos.observability import Observability

obs = Observability()

with obs.trace("process-task", task_id="123"):
    # Your code here
    obs.metrics.counter("tasks_processed")
```

### Multi-Tenancy

```python
from agentos.tenancy import TenantManager
from agentos.governor import ResourceLimits

manager = TenantManager()
manager.create_tenant("team-a", "Team A", limits=ResourceLimits(max_cpu=4.0))

if manager.check_quota("team-a", "cpu", 1.0):
    manager.allocate("team-a", "cpu", 1.0)
```

## License

MIT License — see [LICENSE](LICENSE) for details.
