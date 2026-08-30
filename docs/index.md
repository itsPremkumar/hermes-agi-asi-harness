# Hermes AGI/ASI Harness

> Production-grade, free-first, modular, model-agnostic autonomous agent harness with advanced coding intelligence.

## Quick Start

```bash
# Install
uv pip install -e ".[dev]"

# Run tests
pytest tests/ -x

# Run locally
python hermes.py interactive
```

## Features

- **Plugin Framework** — 82+ plugins across 5 domains
- **Dynamic Config** — Hot-reload configuration in <5s
- **High Availability** — Circuit breaker, failover, graceful degradation
- **Hermes Integration** — Native profiles, kanban, cron, MCP support
- **Continuous Development** — 24/7 improvement loop with A/B testing

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              HERMES INTELLIGENCE OS v11              │
├─────────────────────────────────────────────────────┤
│  COGNITION PLANE  │ SHARED BLACKBOARD │  RSI PLANE  │
│  World Model      │ State             │ Bottleneck  │
│  Memory           │ Events            │ Hypothesis  │
│  Beliefs          │ Goals             │ Candidates  │
│  Research         │ Plans             │ Benchmarks  │
│  Reasoning        │ Results           │ Holdout     │
│  Planning         │                   │ Promotion   │
└─────────────────────────────────────────────────────┘
```

## Links

- [Getting Started](getting-started.md)
- [Architecture](architecture.md)
- [API Reference](api.md)
- [GitHub](https://github.com/itsPremkumar/hermes-agi-asi-harness)
